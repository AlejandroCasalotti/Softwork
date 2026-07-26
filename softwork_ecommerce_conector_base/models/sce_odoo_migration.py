# -*- coding: utf-8 -*-
import json
import logging
import xmlrpc.client
from datetime import datetime

from odoo import fields, models
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

        _logger.info(
            "RPC_CALL OUT model=%s method=%s args=%s kwargs=%s",
            model,
            method,
            repr(rpc_args),
            repr(rpc_kwargs),
        )

        try:
            result = models_rpc.execute_kw(db, uid, pwd, model, method, rpc_args, rpc_kwargs)
            _logger.info("RPC_CALL OK model=%s method=%s", model, method)
            return result
        except Exception as err:
            _logger.exception(
                "RPC_CALL ERROR model=%s method=%s args=%s kwargs=%s err=%s",
                model,
                method,
                repr(rpc_args),
                repr(rpc_kwargs),
                err,
            )
            raise

    def _get_versions(self):
        self.ensure_one()
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

    def _ensure_remote_ref(self, target_rpc, target_uid, model, domain, create_vals):
        rec_ids = self._rpc_call(
            target_rpc,
            self.account_id.odoo_target_db,
            target_uid,
            self.account_id.odoo_target_api_key,
            model,
            "search",
            domain,
            limit=1,
        )
        if rec_ids:
            return rec_ids[0]
        return self._rpc_call(
            target_rpc,
            self.account_id.odoo_target_db,
            target_uid,
            self.account_id.odoo_target_api_key,
            model,
            "create",
            create_vals,
        )

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
            errors.append({"model": model_name, "id": record_id, "error": str(err)})
            self.error_count = (self.error_count or 0) + 1
            if not self.continue_on_error:
                raise
            return False

    def _sync_res_partner(self, src_rpc, src_uid, dst_rpc, dst_uid, cp):
        self.ensure_one()
        domain = self._build_since_domain()
        partner_ids = self._rpc_call(
            src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
            "res.partner", "search", domain
        )
        last_id = cp.get("res.partner_last_id", 0)
        errors = []
        migrated = 0

        def _process(pid):
            vals = self._rpc_call(
                src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
                "res.partner", "read", [pid], fields=["name", "email", "phone", "vat", "is_company"]
            )[0]
            search_domain = [("vat", "=", vals.get("vat"))] if vals.get("vat") else [("name", "=", vals.get("name"))]
            existing = self._rpc_call(
                dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                "res.partner", "search", search_domain,
                limit=1
            )
            write_vals = {
                "name": vals.get("name"),
                "email": vals.get("email"),
                "phone": vals.get("phone"),
                "vat": vals.get("vat"),
                "is_company": vals.get("is_company", False),
            }
            if existing:
                self._rpc_call(
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    "res.partner", "write", existing[0], write_vals
                )
            else:
                self._rpc_call(
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    "res.partner", "create", write_vals
                )

        for batch in self._iter_batches(partner_ids):
            for pid in batch:
                if pid <= last_id:
                    continue
                ok = self._safe_process_record(_process, pid, cp, "res.partner_last_id", errors, "res.partner")
                if ok:
                    migrated += 1

        self.migrated_partners += migrated
        return errors

    def _fields_get(self, rpc, db, uid, pwd, model):
        return self._rpc_call(
            rpc,
            db,
            uid,
            pwd,
            model,
            "fields_get",
            [],
            attributes=["type", "readonly", "required"],
        )

    def _has_field(self, fields_map, field_name):
        return field_name in (fields_map or {})

    def _safe_value(self, value):
        if isinstance(value, dict):
            return value.get("id") or value.get("name") or value.get("display_name") or False
        if isinstance(value, (list, tuple)) and value:
            return value[0]
        return value

    def _safe_text(self, value):
        if isinstance(value, dict):
            return value.get("name") or value.get("display_name") or str(value.get("id") or "")
        if isinstance(value, (list, tuple)):
            return str(value[1]) if len(value) > 1 else str(value[0] if value else "")
        return value

    def _prepare_write_vals(self, src_vals, dst_fields):
        write_vals = {}
        for fname, fdef in (dst_fields or {}).items():
            if fname in ("id", "create_uid", "create_date", "write_uid", "write_date", "__last_update", "display_name"):
                continue
            if fdef.get("readonly"):
                continue
            if fname not in src_vals:
                continue

            ftype = fdef.get("type")
            val = src_vals.get(fname)

            if ftype == "many2one":
                write_vals[fname] = self._safe_value(val)
            elif ftype in ("many2many", "one2many"):
                if isinstance(val, list):
                    ids = [v for v in val if isinstance(v, int)]
                    write_vals[fname] = [(6, 0, ids)]
            else:
                write_vals[fname] = val
        return write_vals

    def _safe_product_search_domain(self, vals):
        default_code = self._safe_text(vals.get("default_code"))
        name = self._safe_text(vals.get("name"))
        if default_code:
            return [("default_code", "=", default_code)]
        if name:
            return [("name", "=", name)]
        return []

    def _map_many2one_by_name(self, src_rpc, src_db, src_uid, src_pwd, dst_rpc, dst_db, dst_uid, dst_pwd, src_value, model):
        if not src_value:
            return False
        src_id = src_value[0] if isinstance(src_value, (list, tuple)) else src_value
        src_name = src_value[1] if isinstance(src_value, (list, tuple)) and len(src_value) > 1 else False
        if not src_name:
            src_rec = self._rpc_call(
                src_rpc, src_db, src_uid, src_pwd, model, "read", [src_id], fields=["name"]
            )
            src_name = src_rec and src_rec[0].get("name")
        if not src_name:
            return False
        dst_ids = self._rpc_call(
            dst_rpc, dst_db, dst_uid, dst_pwd, model, "search", [("name", "=", src_name)], limit=1
        )
        return dst_ids[0] if dst_ids else False

    def _sync_product_template(self, src_rpc, src_uid, dst_rpc, dst_uid, cp):
        self.ensure_one()
        domain = self._build_since_domain()
        product_ids = self._rpc_call(
            src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
            "product.template", "search", domain
        )
        last_id = cp.get("product.template_last_id", 0)
        errors = []
        migrated = 0

        def _process(ptid):
            src_fields = self._fields_get(
                src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key, "product.template"
            )
            dst_fields = self._fields_get(
                dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key, "product.template"
            )
            # Leer todos los campos disponibles en origen para copiar lo máximo compatible.
            read_fields = list((src_fields or {}).keys())
            vals = self._rpc_call(
                src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
                "product.template", "read", [ptid], fields=read_fields
            )[0]

            search_domain = self._safe_product_search_domain(vals)
            existing = self._rpc_call(
                dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                "product.template", "search", search_domain, limit=1
            ) if search_domain else []

            # Copia genérica defensiva + override de campos clave.
            write_vals = self._prepare_write_vals(vals, dst_fields)
            if self._has_field(dst_fields, "name"):
                write_vals["name"] = self._safe_text(vals.get("name"))
            if self._has_field(dst_fields, "default_code"):
                write_vals["default_code"] = self._safe_text(vals.get("default_code"))
            if self._has_field(dst_fields, "list_price"):
                write_vals["list_price"] = vals.get("list_price") or 0.0
            if self._has_field(dst_fields, "standard_price"):
                write_vals["standard_price"] = vals.get("standard_price") or 0.0
            if self._has_field(dst_fields, "type"):
                write_vals["type"] = vals.get("type") or "consu"

            if self._has_field(dst_fields, "categ_id") and vals.get("categ_id"):
                dst_categ_id = self._map_many2one_by_name(
                    src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    vals.get("categ_id"), "product.category"
                )
                if dst_categ_id:
                    write_vals["categ_id"] = dst_categ_id

            if self._has_field(dst_fields, "uom_id") and vals.get("uom_id"):
                dst_uom_id = self._map_many2one_by_name(
                    src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    vals.get("uom_id"), "uom.uom"
                )
                if dst_uom_id:
                    write_vals["uom_id"] = dst_uom_id

            if self._has_field(dst_fields, "uom_po_id") and vals.get("uom_po_id"):
                dst_uom_po_id = self._map_many2one_by_name(
                    src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    vals.get("uom_po_id"), "uom.uom"
                )
                if dst_uom_po_id:
                    write_vals["uom_po_id"] = dst_uom_po_id
            if existing:
                self._rpc_call(
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    "product.template", "write", existing[0], write_vals
                )
            else:
                self._rpc_call(
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    "product.template", "create", write_vals
                )

        for batch in self._iter_batches(product_ids):
            for ptid in batch:
                if ptid <= last_id:
                    continue
                ok = self._safe_process_record(_process, ptid, cp, "product.template_last_id", errors, "product.template")
                if ok:
                    migrated += 1

        self.migrated_products += migrated
        return errors

    def _sync_product_category(self, src_rpc, src_uid, dst_rpc, dst_uid, cp):
        self.ensure_one()
        domain = self._build_since_domain()
        cat_ids = self._rpc_call(
            src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
            "product.category", "search", domain
        )
        last_id = cp.get("product.category_last_id", 0)
        errors = []
        migrated = 0

        def _process(cid):
            vals = self._rpc_call(
                src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
                "product.category", "read", [cid], fields=["name", "parent_id"]
            )[0]
            existing = self._rpc_call(
                dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                "product.category", "search", [("name", "=", vals.get("name"))], limit=1
            )
            write_vals = {"name": vals.get("name")}
            if vals.get("parent_id"):
                parent_id = self._map_many2one_by_name(
                    src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    vals.get("parent_id"), "product.category"
                )
                if parent_id:
                    write_vals["parent_id"] = parent_id
            if existing:
                self._rpc_call(
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    "product.category", "write", existing[0], write_vals
                )
            else:
                self._rpc_call(
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    "product.category", "create", write_vals
                )

        for batch in self._iter_batches(cat_ids):
            for cid in batch:
                if cid <= last_id:
                    continue
                ok = self._safe_process_record(_process, cid, cp, "product.category_last_id", errors, "product.category")
                if ok:
                    migrated += 1

        self.migrated_product_categories += migrated
        return errors

    def _sync_product_public_category(self, src_rpc, src_uid, dst_rpc, dst_uid, cp):
        self.ensure_one()
        domain = self._build_since_domain()
        cat_ids = self._rpc_call(
            src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
            "product.public.category", "search", domain
        )
        last_id = cp.get("product.public.category_last_id", 0)
        errors = []
        migrated = 0

        def _process(cid):
            vals = self._rpc_call(
                src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
                "product.public.category", "read", [cid], fields=["name", "parent_id"]
            )[0]
            existing = self._rpc_call(
                dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                "product.public.category", "search", [("name", "=", vals.get("name"))], limit=1
            )
            write_vals = {"name": vals.get("name")}
            if vals.get("parent_id"):
                parent_id = self._map_many2one_by_name(
                    src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    vals.get("parent_id"), "product.public.category"
                )
                if parent_id:
                    write_vals["parent_id"] = parent_id
            if existing:
                self._rpc_call(
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    "product.public.category", "write", existing[0], write_vals
                )
            else:
                self._rpc_call(
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    "product.public.category", "create", write_vals
                )

        for batch in self._iter_batches(cat_ids):
            for cid in batch:
                if cid <= last_id:
                    continue
                ok = self._safe_process_record(
                    _process, cid, cp, "product.public.category_last_id", errors, "product.public.category"
                )
                if ok:
                    migrated += 1

        self.migrated_product_web_categories += migrated
        return errors

    def _sync_product_supplierinfo(self, src_rpc, src_uid, dst_rpc, dst_uid, cp):
        self.ensure_one()
        domain = self._build_since_domain()
        supp_ids = self._rpc_call(
            src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
            "product.supplierinfo", "search", domain
        )
        last_id = cp.get("product.supplierinfo_last_id", 0)
        errors = []
        migrated = 0

        def _process(sid):
            vals = self._rpc_call(
                src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
                "product.supplierinfo", "read", [sid],
                fields=["name", "product_tmpl_id", "product_id", "min_qty", "price", "delay", "product_code", "product_name"]
            )[0]

            partner_id = False
            if vals.get("name"):
                partner_id = self._map_many2one_by_name(
                    src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    vals.get("name"), "res.partner"
                )

            product_tmpl_id = False
            if vals.get("product_tmpl_id"):
                product_tmpl_id = self._map_many2one_by_name(
                    src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    vals.get("product_tmpl_id"), "product.template"
                )

            if not partner_id or not product_tmpl_id:
                raise UserError(
                    "No se pudo mapear supplierinfo: partner_id o product_tmpl_id inexistente en destino"
                )

            existing = self._rpc_call(
                dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                "product.supplierinfo", "search",
                [("name", "=", partner_id), ("product_tmpl_id", "=", product_tmpl_id)],
                limit=1
            )
            write_vals = {
                "name": partner_id,
                "product_tmpl_id": product_tmpl_id,
                "min_qty": vals.get("min_qty") or 0.0,
                "price": vals.get("price") or 0.0,
                "delay": vals.get("delay") or 0,
                "product_code": vals.get("product_code"),
                "product_name": vals.get("product_name"),
            }
            if existing:
                self._rpc_call(
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    "product.supplierinfo", "write", existing[0], write_vals
                )
            else:
                self._rpc_call(
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    "product.supplierinfo", "create", write_vals
                )

        for batch in self._iter_batches(supp_ids):
            for sid in batch:
                if sid <= last_id:
                    continue
                ok = self._safe_process_record(
                    _process, sid, cp, "product.supplierinfo_last_id", errors, "product.supplierinfo"
                )
                if ok:
                    migrated += 1

        self.migrated_product_suppliers += migrated
        return errors

    def _sync_account_payment(self, src_rpc, src_uid, dst_rpc, dst_uid, cp):
        self.ensure_one()
        domain = self._build_since_domain()
        pay_ids = self._rpc_call(
            src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
            "account.payment", "search", domain
        )
        last_id = cp.get("account.payment_last_id", 0)
        errors = []
        migrated = 0

        def _process(pid):
            vals = self._rpc_call(
                src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
                "account.payment", "read", [pid],
                fields=["payment_type", "partner_type", "amount", "date", "ref", "partner_id", "journal_id", "currency_id"]
            )[0]

            partner_id = False
            if vals.get("partner_id"):
                partner_id = self._map_many2one_by_name(
                    src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    vals.get("partner_id"), "res.partner"
                )

            journal_id = False
            if vals.get("journal_id"):
                journal_id = self._map_many2one_by_name(
                    src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    vals.get("journal_id"), "account.journal"
                )

            existing = self._rpc_call(
                dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                "account.payment", "search", [("ref", "=", vals.get("ref"))], limit=1
            ) if vals.get("ref") else []

            write_vals = {
                "payment_type": vals.get("payment_type") or "inbound",
                "partner_type": vals.get("partner_type") or "customer",
                "amount": vals.get("amount") or 0.0,
                "date": vals.get("date"),
                "ref": vals.get("ref"),
            }
            if partner_id:
                write_vals["partner_id"] = partner_id
            if journal_id:
                write_vals["journal_id"] = journal_id

            if existing:
                self._rpc_call(
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    "account.payment", "write", existing[0], write_vals
                )
            else:
                self._rpc_call(
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    "account.payment", "create", write_vals
                )

        for batch in self._iter_batches(pay_ids):
            for pid in batch:
                if pid <= last_id:
                    continue
                ok = self._safe_process_record(_process, pid, cp, "account.payment_last_id", errors, "account.payment")
                if ok:
                    migrated += 1

        self.migrated_payments += migrated
        return errors

    def _sync_ir_attachment(self, src_rpc, src_uid, dst_rpc, dst_uid, cp):
        self.ensure_one()
        domain = self._build_since_domain()
        att_ids = self._rpc_call(
            src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
            "ir.attachment", "search", domain
        )
        last_id = cp.get("ir.attachment_last_id", 0)
        errors = []
        migrated = 0
        allowed_models = {"res.partner", "product.template", "account.move", "account.payment"}

        def _process(aid):
            vals = self._rpc_call(
                src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
                "ir.attachment", "read", [aid],
                fields=["name", "res_model", "res_id", "mimetype", "type", "datas", "url"]
            )[0]
            if vals.get("res_model") not in allowed_models:
                return

            existing = self._rpc_call(
                dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                "ir.attachment", "search",
                [("name", "=", vals.get("name")), ("res_model", "=", vals.get("res_model")), ("res_id", "=", vals.get("res_id"))],
                limit=1
            )
            write_vals = {
                "name": vals.get("name"),
                "res_model": vals.get("res_model"),
                "res_id": vals.get("res_id"),
                "mimetype": vals.get("mimetype"),
                "type": vals.get("type") or "binary",
                "datas": vals.get("datas"),
                "url": vals.get("url"),
            }
            if existing:
                self._rpc_call(
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    "ir.attachment", "write", existing[0], write_vals
                )
            else:
                self._rpc_call(
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    "ir.attachment", "create", write_vals
                )

        for batch in self._iter_batches(att_ids):
            for aid in batch:
                if aid <= last_id:
                    continue
                ok = self._safe_process_record(_process, aid, cp, "ir.attachment_last_id", errors, "ir.attachment")
                if ok:
                    migrated += 1

        self.migrated_documents += migrated
        return errors

    def _sync_account_tax(self, src_rpc, src_uid, dst_rpc, dst_uid, cp):
        self.ensure_one()
        domain = self._build_since_domain()
        tax_ids = self._rpc_call(
            src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
            "account.tax", "search", domain
        )
        last_id = cp.get("account.tax_last_id", 0)
        errors = []
        migrated = 0

        def _process(tid):
            vals = self._rpc_call(
                src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
                "account.tax", "read", [tid], fields=["name", "amount", "amount_type", "type_tax_use"]
            )[0]
            existing = self._rpc_call(
                dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                "account.tax", "search", [("name", "=", vals.get("name")), ("type_tax_use", "=", vals.get("type_tax_use"))],
                limit=1
            )
            write_vals = {
                "name": vals.get("name"),
                "amount": vals.get("amount") or 0.0,
                "amount_type": vals.get("amount_type") or "percent",
                "type_tax_use": vals.get("type_tax_use") or "sale",
            }
            if existing:
                self._rpc_call(
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    "account.tax", "write", existing[0], write_vals
                )
            else:
                self._rpc_call(
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    "account.tax", "create", write_vals
                )

        for batch in self._iter_batches(tax_ids):
            for tid in batch:
                if tid <= last_id:
                    continue
                ok = self._safe_process_record(_process, tid, cp, "account.tax_last_id", errors, "account.tax")
                if ok:
                    migrated += 1

        self.migrated_taxes += migrated
        return errors

    def _sync_sale_order(self, src_rpc, src_uid, dst_rpc, dst_uid, cp):
        self.ensure_one()
        domain = self._build_since_domain()
        order_ids = self._rpc_call(
            src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
            "sale.order", "search", domain
        )
        last_id = cp.get("sale.order_last_id", 0)
        errors = []
        migrated = 0

        def _process(oid):
            vals = self._rpc_call(
                src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
                "sale.order", "read", [oid], fields=["name", "client_order_ref", "state", "partner_id"]
            )[0]
            partner_id = False
            if vals.get("partner_id"):
                partner_id = self._map_many2one_by_name(
                    src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    vals.get("partner_id"), "res.partner"
                )
            existing = self._rpc_call(
                dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                "sale.order", "search", [("name", "=", vals.get("name"))], limit=1
            )
            write_vals = {"name": vals.get("name"), "client_order_ref": vals.get("client_order_ref")}
            if partner_id:
                write_vals["partner_id"] = partner_id
            if existing:
                self._rpc_call(
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    "sale.order", "write", existing[0], write_vals
                )
            else:
                self._rpc_call(
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    "sale.order", "create", write_vals
                )

        for batch in self._iter_batches(order_ids):
            for oid in batch:
                if oid <= last_id:
                    continue
                ok = self._safe_process_record(_process, oid, cp, "sale.order_last_id", errors, "sale.order")
                if ok:
                    migrated += 1

        self.migrated_sales += migrated
        return errors

    def _sync_purchase_order(self, src_rpc, src_uid, dst_rpc, dst_uid, cp):
        self.ensure_one()
        domain = self._build_since_domain()
        order_ids = self._rpc_call(
            src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
            "purchase.order", "search", domain
        )
        last_id = cp.get("purchase.order_last_id", 0)
        errors = []
        migrated = 0

        def _process(oid):
            vals = self._rpc_call(
                src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
                "purchase.order", "read", [oid], fields=["name", "partner_ref", "state", "partner_id"]
            )[0]
            partner_id = False
            if vals.get("partner_id"):
                partner_id = self._map_many2one_by_name(
                    src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    vals.get("partner_id"), "res.partner"
                )
            existing = self._rpc_call(
                dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                "purchase.order", "search", [("name", "=", vals.get("name"))], limit=1
            )
            write_vals = {"name": vals.get("name"), "partner_ref": vals.get("partner_ref")}
            if partner_id:
                write_vals["partner_id"] = partner_id
            if existing:
                self._rpc_call(
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    "purchase.order", "write", existing[0], write_vals
                )
            else:
                self._rpc_call(
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    "purchase.order", "create", write_vals
                )

        for batch in self._iter_batches(order_ids):
            for oid in batch:
                if oid <= last_id:
                    continue
                ok = self._safe_process_record(_process, oid, cp, "purchase.order_last_id", errors, "purchase.order")
                if ok:
                    migrated += 1

        self.migrated_purchases += migrated
        return errors

    def _sync_account_move(self, src_rpc, src_uid, dst_rpc, dst_uid, cp):
        self.ensure_one()
        domain = self._build_since_domain()
        move_ids = self._rpc_call(
            src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
            "account.move", "search", domain
        )
        last_id = cp.get("account.move_last_id", 0)
        errors = []
        migrated = 0

        def _process(mid):
            vals = self._rpc_call(
                src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
                "account.move", "read", [mid], fields=["name", "move_type", "invoice_date", "partner_id", "ref"]
            )[0]
            partner_id = False
            if vals.get("partner_id"):
                partner_id = self._map_many2one_by_name(
                    src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    vals.get("partner_id"), "res.partner"
                )
            existing = self._rpc_call(
                dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                "account.move", "search", [("name", "=", vals.get("name")), ("move_type", "=", vals.get("move_type"))], limit=1
            )
            write_vals = {
                "name": vals.get("name"),
                "move_type": vals.get("move_type") or "out_invoice",
                "invoice_date": vals.get("invoice_date"),
                "ref": vals.get("ref"),
            }
            if partner_id:
                write_vals["partner_id"] = partner_id
            if existing:
                self._rpc_call(
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    "account.move", "write", existing[0], write_vals
                )
            else:
                self._rpc_call(
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    "account.move", "create", write_vals
                )

        for batch in self._iter_batches(move_ids):
            for mid in batch:
                if mid <= last_id:
                    continue
                ok = self._safe_process_record(_process, mid, cp, "account.move_last_id", errors, "account.move")
                if ok:
                    migrated += 1

        self.migrated_invoices += migrated
        return errors

    def _sync_stock_warehouse(self, src_rpc, src_uid, dst_rpc, dst_uid, cp):
        self.ensure_one()
        domain = self._build_since_domain()
        wh_ids = self._rpc_call(
            src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
            "stock.warehouse", "search", domain
        )
        last_id = cp.get("stock.warehouse_last_id", 0)
        errors = []
        migrated = 0

        def _process(wid):
            vals = self._rpc_call(
                src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
                "stock.warehouse", "read", [wid], fields=["name", "code", "company_id"]
            )[0]
            existing_domain = [("code", "=", vals.get("code"))] if vals.get("code") else [("name", "=", vals.get("name"))]
            existing = self._rpc_call(
                dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                "stock.warehouse", "search", existing_domain, limit=1
            )
            write_vals = {"name": vals.get("name"), "code": vals.get("code")}
            if existing:
                self._rpc_call(
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    "stock.warehouse", "write", existing[0], write_vals
                )
            else:
                self._rpc_call(
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    "stock.warehouse", "create", write_vals
                )

        for batch in self._iter_batches(wh_ids):
            for wid in batch:
                if wid <= last_id:
                    continue
                ok = self._safe_process_record(_process, wid, cp, "stock.warehouse_last_id", errors, "stock.warehouse")
                if ok:
                    migrated += 1

        self.migrated_warehouses += migrated
        return errors

    def _sync_stock_location(self, src_rpc, src_uid, dst_rpc, dst_uid, cp):
        self.ensure_one()
        domain = self._build_since_domain()
        loc_ids = self._rpc_call(
            src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
            "stock.location", "search", domain
        )
        last_id = cp.get("stock.location_last_id", 0)
        errors = []
        migrated = 0

        def _process(lid):
            vals = self._rpc_call(
                src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
                "stock.location", "read", [lid], fields=["name", "complete_name", "usage", "location_id"]
            )[0]
            existing_domain = [("complete_name", "=", vals.get("complete_name"))] if vals.get("complete_name") else [("name", "=", vals.get("name"))]
            existing = self._rpc_call(
                dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                "stock.location", "search", existing_domain, limit=1
            )
            write_vals = {"name": vals.get("name"), "usage": vals.get("usage") or "internal"}
            if vals.get("location_id"):
                parent_id = self._map_many2one_by_name(
                    src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    vals.get("location_id"), "stock.location"
                )
                if parent_id:
                    write_vals["location_id"] = parent_id
            if existing:
                self._rpc_call(
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    "stock.location", "write", existing[0], write_vals
                )
            else:
                self._rpc_call(
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    "stock.location", "create", write_vals
                )

        for batch in self._iter_batches(loc_ids):
            for lid in batch:
                if lid <= last_id:
                    continue
                ok = self._safe_process_record(_process, lid, cp, "stock.location_last_id", errors, "stock.location")
                if ok:
                    migrated += 1

        self.migrated_locations += migrated
        return errors

    def action_run_migration(self):
        for rec in self:
            missing = []
            for label, value in [
                ("Odoo Origen - URL", rec.account_id.odoo_source_url),
                ("Odoo Origen - Base de datos", rec.account_id.odoo_source_db),
                ("Odoo Origen - Usuario", rec.account_id.odoo_source_user),
                ("Odoo Origen - API Key / Password", rec.account_id.odoo_source_api_key),
                ("Odoo Destino - URL", rec.account_id.odoo_target_url),
                ("Odoo Destino - Base de datos", rec.account_id.odoo_target_db),
                ("Odoo Destino - Usuario", rec.account_id.odoo_target_user),
                ("Odoo Destino - API Key / Password", rec.account_id.odoo_target_api_key),
            ]:
                if not value:
                    missing.append(label)
            if missing:
                raise UserError("Faltan datos de conexión Odoo Origen/Destino:\n- " + "\n- ".join(missing))

            rec.write({"state": "running", "started_at": fields.Datetime.now(), "last_error": False})
            cp = rec._load_checkpoint()
            try:
                src_uid, src_rpc = rec._rpc_connect(
                    rec.account_id.odoo_source_url,
                    rec.account_id.odoo_source_db,
                    rec.account_id.odoo_source_user,
                    rec.account_id.odoo_source_api_key,
                )
                dst_uid, dst_rpc = rec._rpc_connect(
                    rec.account_id.odoo_target_url,
                    rec.account_id.odoo_target_db,
                    rec.account_id.odoo_target_user,
                    rec.account_id.odoo_target_api_key,
                )
                rec._get_versions()

                errors = []
                if rec.sync_partners:
                    errors += rec._sync_res_partner(src_rpc, src_uid, dst_rpc, dst_uid, cp) or []
                    rec._save_checkpoint(cp)

                if rec.sync_products:
                    errors += rec._sync_product_template(src_rpc, src_uid, dst_rpc, dst_uid, cp) or []
                    rec._save_checkpoint(cp)

                if rec.sync_product_categories:
                    errors += rec._sync_product_category(src_rpc, src_uid, dst_rpc, dst_uid, cp) or []
                    rec._save_checkpoint(cp)

                if rec.sync_product_web_categories:
                    errors += rec._sync_product_public_category(src_rpc, src_uid, dst_rpc, dst_uid, cp) or []
                    rec._save_checkpoint(cp)

                if rec.sync_product_suppliers:
                    errors += rec._sync_product_supplierinfo(src_rpc, src_uid, dst_rpc, dst_uid, cp) or []
                    rec._save_checkpoint(cp)

                if rec.sync_taxes:
                    errors += rec._sync_account_tax(src_rpc, src_uid, dst_rpc, dst_uid, cp) or []
                    rec._save_checkpoint(cp)

                if rec.sync_sales:
                    errors += rec._sync_sale_order(src_rpc, src_uid, dst_rpc, dst_uid, cp) or []
                    rec._save_checkpoint(cp)

                if rec.sync_purchases:
                    errors += rec._sync_purchase_order(src_rpc, src_uid, dst_rpc, dst_uid, cp) or []
                    rec._save_checkpoint(cp)

                if rec.sync_invoices:
                    errors += rec._sync_account_move(src_rpc, src_uid, dst_rpc, dst_uid, cp) or []
                    rec._save_checkpoint(cp)

                if rec.sync_payments:
                    errors += rec._sync_account_payment(src_rpc, src_uid, dst_rpc, dst_uid, cp) or []
                    rec._save_checkpoint(cp)

                if rec.sync_documents:
                    errors += rec._sync_ir_attachment(src_rpc, src_uid, dst_rpc, dst_uid, cp) or []
                    rec._save_checkpoint(cp)

                if rec.sync_stock_warehouses:
                    errors += rec._sync_stock_warehouse(src_rpc, src_uid, dst_rpc, dst_uid, cp) or []
                    rec._save_checkpoint(cp)

                if rec.sync_stock_locations:
                    errors += rec._sync_stock_location(src_rpc, src_uid, dst_rpc, dst_uid, cp) or []
                    rec._save_checkpoint(cp)

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
                                "sales": rec.migrated_sales,
                                "purchases": rec.migrated_purchases,
                                "invoices": rec.migrated_invoices,
                                "warehouses": rec.migrated_warehouses,
                                "locations": rec.migrated_locations,
                                "errors": errors,
                                "finished_at": datetime.utcnow().isoformat(),
                            }
                        ),
                    }
                )
            except Exception as err:
                rec.write({"state": "failed", "last_error": str(err), "finished_at": fields.Datetime.now()})
                raise

    def action_pause_migration(self):
        self.write({"state": "paused"})
        return True

    def action_resume_migration(self):
        for rec in self:
            if rec.state in ("paused", "failed", "draft"):
                rec.action_run_migration()
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
    sync_sales = fields.Boolean(default=False, string="Ventas")
    sync_purchases = fields.Boolean(default=False, string="Compras")
    sync_invoices = fields.Boolean(default=False, string="Facturas")
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
                "sync_sales": self.sync_sales,
                "sync_purchases": self.sync_purchases,
                "sync_invoices": self.sync_invoices,
                "sync_stock_warehouses": self.sync_stock_warehouses,
                "sync_stock_locations": self.sync_stock_locations,
            }
        )
        run.action_run_migration()
        return {
            "type": "ir.actions.act_window",
            "res_model": "sce.odoo.migration.run",
            "view_mode": "form",
            "res_id": run.id,
            "target": "current",
        }