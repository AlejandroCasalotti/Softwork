# -*- coding: utf-8 -*-
import json
import logging
import xmlrpc.client
from datetime import datetime

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SceOdooMigrationRun(models.Model):
    _name = "sce.odoo.migration.run"
    _description = "SCE Odoo Migration Run"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(required=True, default=lambda self: f"Migración {fields.Datetime.now()}")
    account_id = fields.Many2one("sce.account", required=True, ondelete="cascade", index=True)
    connector_id = fields.Many2one(related="account_id.connector_id", store=True, index=True)
    company_id = fields.Many2one(related="account_id.company_id", store=True, index=True)

    state = fields.Selection(
        selection=[
            ("draft", "Borrador"),
            ("queued", "En cola"),
            ("running", "En ejecución"),
            ("paused", "Pausada"),
            ("done", "Finalizada"),
            ("failed", "Fallida"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )

    migration_mode = fields.Selection(
        selection=[("full", "Completa"), ("incremental", "Incremental")],
        default="full",
        required=True,
        tracking=True,
    )
    since_datetime = fields.Datetime(string="Desde fecha (incremental)")
    source_version = fields.Char(readonly=True)
    target_version = fields.Char(readonly=True)

    sync_partners = fields.Boolean(default=True)
    sync_products = fields.Boolean(default=True)
    sync_taxes = fields.Boolean(default=True)
    sync_product_categories = fields.Boolean(default=True)
    sync_product_web_categories = fields.Boolean(default=True)
    sync_product_suppliers = fields.Boolean(default=True)
    sync_sales = fields.Boolean(default=False)
    sync_purchases = fields.Boolean(default=False)
    sync_invoices = fields.Boolean(default=False)
    sync_payments = fields.Boolean(default=False)
    sync_documents = fields.Boolean(default=False)
    sync_stock_warehouses = fields.Boolean(default=False)
    sync_stock_locations = fields.Boolean(default=False)

    checkpoint_json = fields.Text(default="{}")
    result_json = fields.Text()
    last_error = fields.Text()
    started_at = fields.Datetime()
    finished_at = fields.Datetime()
    batch_size = fields.Integer(default=100)
    continue_on_error = fields.Boolean(default=True)
    error_count = fields.Integer(default=0, readonly=True)

    migrated_partners = fields.Integer(default=0, readonly=True)
    migrated_products = fields.Integer(default=0, readonly=True)
    migrated_taxes = fields.Integer(default=0, readonly=True)
    migrated_product_categories = fields.Integer(default=0, readonly=True)
    migrated_product_web_categories = fields.Integer(default=0, readonly=True)
    migrated_product_suppliers = fields.Integer(default=0, readonly=True)
    migrated_sales = fields.Integer(default=0, readonly=True)
    migrated_purchases = fields.Integer(default=0, readonly=True)
    migrated_invoices = fields.Integer(default=0, readonly=True)
    migrated_payments = fields.Integer(default=0, readonly=True)
    migrated_documents = fields.Integer(default=0, readonly=True)
    migrated_warehouses = fields.Integer(default=0, readonly=True)
    migrated_locations = fields.Integer(default=0, readonly=True)

    def _rpc_connect(self, url, db, user, password):
        if not url or not isinstance(url, str):
            raise UserError("Falta URL de Odoo o es inválida.")
        if not db or not isinstance(db, str):
            raise UserError("Falta Base de datos de Odoo o es inválida.")
        if not user or not isinstance(user, str):
            raise UserError("Falta Usuario de Odoo o es inválido.")
        if not password or not isinstance(password, str):
            raise UserError("Falta API Key/Password de Odoo o es inválida.")

        clean_url = url.strip()
        if not clean_url.startswith(("http://", "https://")):
            clean_url = f"https://{clean_url}"

        try:
            common = xmlrpc.client.ServerProxy(f"{clean_url.rstrip('/')}/xmlrpc/2/common")
            uid = common.authenticate(db, user, password, {})
        except Exception as err:
            raise UserError(
                "No se pudo conectar al Odoo remoto.\n"
                f"- URL: {clean_url}\n"
                f"- DB: {db}\n"
                f"- User: {user}\n"
                f"- Detalle técnico: {err}"
            )

        if not uid:
            raise UserError(
                "No se pudo autenticar en Odoo remoto.\n"
                f"- URL: {clean_url}\n"
                f"- DB: {db}\n"
                f"- User: {user}\n"
                "Revisá usuario y API Key/Password, y que el usuario tenga acceso a esa base."
            )

        try:
            models_rpc = xmlrpc.client.ServerProxy(f"{clean_url.rstrip('/')}/xmlrpc/2/object")
        except Exception as err:
            raise UserError(
                "Se autenticó en Odoo remoto pero falló el endpoint de objetos XML-RPC.\n"
                f"- URL: {clean_url}\n"
                f"- Detalle técnico: {err}"
            )

        return uid, models_rpc

    def _rpc_call(self, models_rpc, db, uid, pwd, model, method, *args, **kwargs):
        rpc_kwargs = kwargs or {}
        rpc_args = list(args)

        # Guard rail: avoid malformed XML-RPC payloads that send dict as domain
        # Expected shape for search/search_read/search_count:
        #   args[0] => domain (list/tuple), kwargs => options dict
        if method in ("search", "search_read", "search_count"):
            if rpc_args and isinstance(rpc_args[0], dict):
                rpc_args[0] = []
            elif rpc_args and isinstance(rpc_args[0], (list, tuple)):
                sanitized = []
                for token in rpc_args[0]:
                    if isinstance(token, (list, tuple)) and len(token) == 3:
                        fld, op, val = token
                        if isinstance(val, dict):
                            val = val.get("id") or val.get("name") or val.get("display_name") or False
                        sanitized.append((fld, op, val))
                    else:
                        sanitized.append(token)
                rpc_args[0] = sanitized

        try:
            result = models_rpc.execute_kw(db, uid, pwd, model, method, rpc_args, rpc_kwargs)
            _logger.debug("RPC OK model=%s method=%s", model, method)
            return result
        except Exception as err:
            # No se registran los valores enviados: pueden contener datos del cliente.
            _logger.error("RPC ERROR model=%s method=%s err=%s", model, method, err)
            raise

    def _validate_source_target_connections(self):
        self.ensure_one()
        missing = []
        for label, value in [
            ("Odoo Origen - URL", self.account_id.odoo_source_url),
            ("Odoo Origen - Base de datos", self.account_id.odoo_source_db),
            ("Odoo Origen - Usuario", self.account_id.odoo_source_user),
            ("Odoo Origen - API Key / Password", self.account_id.odoo_source_api_key),
            ("Odoo Destino - URL", self.account_id.odoo_target_url),
            ("Odoo Destino - Base de datos", self.account_id.odoo_target_db),
            ("Odoo Destino - Usuario", self.account_id.odoo_target_user),
            ("Odoo Destino - API Key / Password", self.account_id.odoo_target_api_key),
        ]:
            if not value:
                missing.append(label)
        if missing:
            raise UserError("Faltan datos de conexión Odoo Origen/Destino:\n- " + "\n- ".join(missing))

        src_uid, src_rpc = self._rpc_connect(
            self.account_id.odoo_source_url,
            self.account_id.odoo_source_db,
            self.account_id.odoo_source_user,
            self.account_id.odoo_source_api_key,
        )
        dst_uid, dst_rpc = self._rpc_connect(
            self.account_id.odoo_target_url,
            self.account_id.odoo_target_db,
            self.account_id.odoo_target_user,
            self.account_id.odoo_target_api_key,
        )

        for label, rpc, db, uid, pwd in [
            ("origen", src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key),
            ("destino", dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key),
        ]:
            self._rpc_call(
                rpc,
                db,
                uid,
                pwd,
                "ir.module.module",
                "search_count",
                [],
            )

        return src_uid, src_rpc, dst_uid, dst_rpc

    def _get_versions(self):
        self.ensure_one()
        src_uid, src_rpc, dst_uid, dst_rpc = self._validate_source_target_connections()
        src_ver = self._rpc_call(
            src_rpc,
            self.account_id.odoo_source_db,
            src_uid,
            self.account_id.odoo_source_api_key,
            "ir.config_parameter",
            "get_param",
            "web.base.version",
        ) or "N/D"
        dst_ver = self._rpc_call(
            dst_rpc,
            self.account_id.odoo_target_db,
            dst_uid,
            self.account_id.odoo_target_api_key,
            "ir.config_parameter",
            "get_param",
            "web.base.version",
        ) or "N/D"
        self.write({"source_version": src_ver, "target_version": dst_ver})

    def action_detect_versions(self):
        for rec in self:
            rec._get_versions()
        return True


    def _load_checkpoint(self):
        self.ensure_one()
        try:
            return json.loads(self.checkpoint_json or "{}")
        except Exception:
            return {}

    def _save_checkpoint(self, data):
        self.ensure_one()
        self.checkpoint_json = json.dumps(data or {})

    def _build_since_domain(self, field_name="write_date"):
        self.ensure_one()
        if self.migration_mode != "incremental" or not self.since_datetime:
            return []
        return [(field_name, ">=", fields.Datetime.to_string(self.since_datetime))]

    def _iter_batches(self, ids_list):
        size = max(1, int(self.batch_size or 100))
        for i in range(0, len(ids_list), size):
            yield ids_list[i:i + size]

    def _safe_process_record(self, fn, record_id, cp, cp_key, errors, model_name):
        try:
            fn(record_id)
            cp[cp_key] = record_id
            return True
        except Exception as err:
            err_msg = str(err)
            errors.append({"model": model_name, "id": record_id, "error": err_msg})
            self.error_count = (self.error_count or 0) + 1
            if not self.continue_on_error:
                raise
            return False





















    def _run_migration_now(self):
        for rec in self:
            rec.write({"state": "running", "started_at": fields.Datetime.now(), "last_error": False})
            cp = rec._load_checkpoint()
            try:
                src_uid, src_rpc, dst_uid, dst_rpc = rec._validate_source_target_connections()
                rec._get_versions()

                ctx = rec._build_migration_context(src_uid, src_rpc, dst_uid, dst_rpc)
                errors = []
                for model, counter_field in rec._iter_selected_entities():
                    errors += rec._sync_remote_model(ctx, model, counter_field, cp) or []
                    rec._save_checkpoint(cp)

                rec.error_count = len(errors) if errors else 0
                rec.write(
                    {
                        "state": "done",
                        "finished_at": fields.Datetime.now(),
                        "result_json": json.dumps(
                            {
                                "partners": rec.migrated_partners,
                                "products": rec.migrated_products,
                                "taxes": rec.migrated_taxes,
                                "product_categories": rec.migrated_product_categories,
                                "product_web_categories": rec.migrated_product_web_categories,
                                "product_suppliers": rec.migrated_product_suppliers,
                                "sales": rec.migrated_sales,
                                "purchases": rec.migrated_purchases,
                                "invoices": rec.migrated_invoices,
                                "payments": rec.migrated_payments,
                                "documents": rec.migrated_documents,
                                "warehouses": rec.migrated_warehouses,
                                "locations": rec.migrated_locations,
                                "unresolved_relations": ctx.get("unresolved", {}),
                                "errors": errors,
                                "finished_at": datetime.utcnow().isoformat(),
                            }
                        ),
                    }
                )
            except Exception as err:
                rec.write({"state": "failed", "last_error": str(err), "finished_at": fields.Datetime.now()})
                _logger.exception("La migración Odoo a Odoo falló migration_id=%s", rec.id)

    def action_enqueue_migration(self):
        for rec in self:
            if rec.state == "running":
                continue
            rec._check_required_fields_mapped()
            rec.write({"state": "queued", "last_error": False, "finished_at": False})
        self._trigger_migration_cron()
        return True

    def _trigger_migration_cron(self):
        cron = self.env.ref(
            "softwork_ecommerce_conector_base.ir_cron_sce_process_odoo_migrations",
            raise_if_not_found=False,
        )
        if not cron:
            raise UserError(
                "No se encontró la acción programada de migraciones. Actualizá el módulo "
                "Softwork Ecommerce Connector Base."
            )
        if not cron.active:
            cron.sudo().write({"active": True})
        cron.sudo()._trigger()
        return True

    def action_process_queued_migration(self):
        self.ensure_one()
        if self.state != "queued":
            raise UserError("Solo se puede procesar manualmente una migración que está en cola.")
        return self._trigger_migration_cron()

    @api.model
    def cron_process_migration_queue(self):
        runs = self.search([("state", "=", "queued")], limit=1, order="create_date asc")
        for run in runs:
            run._run_migration_now()

    def action_pause_migration(self):
        self.write({"state": "paused"})
        return True

    def action_resume_migration(self):
        for rec in self:
            if rec.state in ("paused", "failed", "draft"):
                rec.action_enqueue_migration()
        return True

    def action_reset_checkpoint(self):
        self.write({
            "checkpoint_json": "{}",
            "migrated_partners": 0,
            "migrated_products": 0,
            "migrated_taxes": 0,
            "migrated_product_categories": 0,
            "migrated_product_web_categories": 0,
            "migrated_sales": 0,
            "migrated_purchases": 0,
            "migrated_invoices": 0,
            "migrated_warehouses": 0,
            "migrated_locations": 0,
            "error_count": 0,
        })
        return True


class SceOdooMigrationWizard(models.TransientModel):
    _name = "sce.odoo.migration.wizard"
    _description = "SCE Odoo Migration Wizard"

    account_id = fields.Many2one("sce.account", required=True)
    migration_mode = fields.Selection(
        selection=[("full", "Completa"), ("incremental", "Incremental")],
        default="full",
        required=True,
    )
    since_datetime = fields.Datetime(string="Desde fecha")
    sync_partners = fields.Boolean(default=True, string="Clientes/Proveedores")
    sync_products = fields.Boolean(default=True, string="Productos/Categorías base")
    sync_taxes = fields.Boolean(default=True, string="Impuestos")
    sync_product_categories = fields.Boolean(default=True, string="Categorías de producto")
    sync_product_web_categories = fields.Boolean(default=True, string="Categorías web de producto")
    sync_product_suppliers = fields.Boolean(default=True, string="Proveedores de producto")
    sync_sales = fields.Boolean(default=False, string="Ventas")
    sync_purchases = fields.Boolean(default=False, string="Compras")
    sync_invoices = fields.Boolean(default=False, string="Facturas")
    sync_payments = fields.Boolean(default=False, string="Pagos")
    sync_documents = fields.Boolean(default=False, string="Documentos/Adjuntos")
    sync_stock_warehouses = fields.Boolean(default=False, string="Almacenes")
    sync_stock_locations = fields.Boolean(default=False, string="Ubicaciones")

    def action_start(self):
        self.ensure_one()
        missing = []
        for label, value in [
            ("Odoo Origen - URL", self.account_id.odoo_source_url),
            ("Odoo Origen - Base de datos", self.account_id.odoo_source_db),
            ("Odoo Origen - Usuario", self.account_id.odoo_source_user),
            ("Odoo Origen - API Key / Password", self.account_id.odoo_source_api_key),
            ("Odoo Destino - URL", self.account_id.odoo_target_url),
            ("Odoo Destino - Base de datos", self.account_id.odoo_target_db),
            ("Odoo Destino - Usuario", self.account_id.odoo_target_user),
            ("Odoo Destino - API Key / Password", self.account_id.odoo_target_api_key),
        ]:
            if not value:
                missing.append(label)
        if missing:
            raise UserError("Faltan datos en la cuenta para iniciar la migración Odoo→Odoo:\n- " + "\n- ".join(missing))

        run = self.env["sce.odoo.migration.run"].create(
            {
                "name": f"Migración {self.account_id.display_name}",
                "account_id": self.account_id.id,
                "migration_mode": self.migration_mode,
                "since_datetime": self.since_datetime,
                "sync_partners": self.sync_partners,
                "sync_products": self.sync_products,
                "sync_taxes": self.sync_taxes,
                "sync_product_categories": self.sync_product_categories,
                "sync_product_web_categories": self.sync_product_web_categories,
                "sync_product_suppliers": self.sync_product_suppliers,
                "sync_sales": self.sync_sales,
                "sync_purchases": self.sync_purchases,
                "sync_invoices": self.sync_invoices,
                "sync_payments": self.sync_payments,
                "sync_documents": self.sync_documents,
                "sync_stock_warehouses": self.sync_stock_warehouses,
                "sync_stock_locations": self.sync_stock_locations,
            }
        )
        run._validate_source_target_connections()
        run.action_enqueue_migration()
        return {
            "type": "ir.actions.act_window",
            "res_model": "sce.odoo.migration.run",
            "view_mode": "form",
            "res_id": run.id,
            "target": "current",
        }