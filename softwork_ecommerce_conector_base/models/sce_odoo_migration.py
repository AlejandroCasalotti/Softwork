# -*- coding: utf-8 -*-
import json
import xmlrpc.client
from datetime import datetime

from odoo import api, fields, models
from odoo.exceptions import UserError


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

    checkpoint_json = fields.Text(default="{}")
    result_json = fields.Text()
    last_error = fields.Text()
    started_at = fields.Datetime()
    finished_at = fields.Datetime()

    migrated_partners = fields.Integer(default=0, readonly=True)
    migrated_products = fields.Integer(default=0, readonly=True)
    migrated_taxes = fields.Integer(default=0, readonly=True)

    def _rpc_connect(self, url, db, user, password):
        common = xmlrpc.client.ServerProxy(f"{url.rstrip('/')}/xmlrpc/2/common")
        uid = common.authenticate(db, user, password, {})
        if not uid:
            raise UserError("No se pudo autenticar en Odoo remoto.")
        models_rpc = xmlrpc.client.ServerProxy(f"{url.rstrip('/')}/xmlrpc/2/object")
        return uid, models_rpc

    def _rpc_call(self, models_rpc, db, uid, pwd, model, method, *args, **kwargs):
        return models_rpc.execute_kw(db, uid, pwd, model, method, args, kwargs or {})

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
            {"limit": 1},
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

    def _sync_res_partner(self, src_rpc, src_uid, dst_rpc, dst_uid, cp):
        self.ensure_one()
        domain = self._build_since_domain()
        partner_ids = self._rpc_call(
            src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
            "res.partner", "search", domain
        )
        last_id = cp.get("res.partner_last_id", 0)
        migrated = 0
        for pid in partner_ids:
            if pid <= last_id:
                continue
            vals = self._rpc_call(
                src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
                "res.partner", "read", [pid], {"fields": ["name", "email", "phone", "vat", "is_company"]}
            )[0]
            existing = self._rpc_call(
                dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                "res.partner", "search", [[("vat", "=", vals.get("vat"))]] if vals.get("vat") else [[("name", "=", vals.get("name"))]],
                {"limit": 1}
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
                    "res.partner", "write", [existing, write_vals]
                )
            else:
                self._rpc_call(
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    "res.partner", "create", [write_vals]
                )
            cp["res.partner_last_id"] = pid
            migrated += 1
        self.migrated_partners += migrated

    def _fields_get(self, rpc, db, uid, pwd, model):
        return self._rpc_call(rpc, db, uid, pwd, model, "fields_get", [], {"attributes": ["type", "readonly", "required"]})

    def _has_field(self, fields_map, field_name):
        return field_name in (fields_map or {})

    def _map_many2one_by_name(self, src_rpc, src_db, src_uid, src_pwd, dst_rpc, dst_db, dst_uid, dst_pwd, src_value, model):
        if not src_value:
            return False
        src_id = src_value[0] if isinstance(src_value, (list, tuple)) else src_value
        src_name = src_value[1] if isinstance(src_value, (list, tuple)) and len(src_value) > 1 else False
        if not src_name:
            src_rec = self._rpc_call(src_rpc, src_db, src_uid, src_pwd, model, "read", [src_id], {"fields": ["name"]})
            src_name = src_rec and src_rec[0].get("name")
        if not src_name:
            return False
        dst_ids = self._rpc_call(dst_rpc, dst_db, dst_uid, dst_pwd, model, "search", [[("name", "=", src_name)]], {"limit": 1})
        return dst_ids[0] if dst_ids else False

    def _sync_product_template(self, src_rpc, src_uid, dst_rpc, dst_uid, cp):
        self.ensure_one()
        domain = self._build_since_domain()
        product_ids = self._rpc_call(
            src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
            "product.template", "search", domain
        )
        last_id = cp.get("product.template_last_id", 0)
        migrated = 0
        for ptid in product_ids:
            if ptid <= last_id:
                continue
            src_fields = self._fields_get(
                src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key, "product.template"
            )
            dst_fields = self._fields_get(
                dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key, "product.template"
            )
            read_fields = ["name", "default_code", "list_price", "standard_price", "type"]
            if self._has_field(src_fields, "categ_id"):
                read_fields.append("categ_id")
            if self._has_field(src_fields, "uom_id"):
                read_fields.append("uom_id")
            if self._has_field(src_fields, "uom_po_id"):
                read_fields.append("uom_po_id")

            vals = self._rpc_call(
                src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
                "product.template", "read", [ptid], {"fields": read_fields}
            )[0]
            search_domain = [[("default_code", "=", vals.get("default_code"))]] if vals.get("default_code") else [[("name", "=", vals.get("name"))]]
            existing = self._rpc_call(
                dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                "product.template", "search", search_domain, {"limit": 1}
            )
            write_vals = {}
            if self._has_field(dst_fields, "name"):
                write_vals["name"] = vals.get("name")
            if self._has_field(dst_fields, "default_code"):
                write_vals["default_code"] = vals.get("default_code")
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
                    "product.template", "write", [existing, write_vals]
                )
            else:
                self._rpc_call(
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    "product.template", "create", [write_vals]
                )
            cp["product.template_last_id"] = ptid
            migrated += 1
        self.migrated_products += migrated

    def _sync_account_tax(self, src_rpc, src_uid, dst_rpc, dst_uid, cp):
        self.ensure_one()
        domain = self._build_since_domain()
        tax_ids = self._rpc_call(
            src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
            "account.tax", "search", domain
        )
        last_id = cp.get("account.tax_last_id", 0)
        migrated = 0
        for tid in tax_ids:
            if tid <= last_id:
                continue
            vals = self._rpc_call(
                src_rpc, self.account_id.odoo_source_db, src_uid, self.account_id.odoo_source_api_key,
                "account.tax", "read", [tid], {"fields": ["name", "amount", "amount_type", "type_tax_use"]}
            )[0]
            existing = self._rpc_call(
                dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                "account.tax", "search", [[("name", "=", vals.get("name")), ("type_tax_use", "=", vals.get("type_tax_use"))]],
                {"limit": 1}
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
                    "account.tax", "write", [existing, write_vals]
                )
            else:
                self._rpc_call(
                    dst_rpc, self.account_id.odoo_target_db, dst_uid, self.account_id.odoo_target_api_key,
                    "account.tax", "create", [write_vals]
                )
            cp["account.tax_last_id"] = tid
            migrated += 1
        self.migrated_taxes += migrated

    def action_run_migration(self):
        for rec in self:
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

                if rec.sync_partners:
                    rec._sync_res_partner(src_rpc, src_uid, dst_rpc, dst_uid, cp)
                    rec._save_checkpoint(cp)

                if rec.sync_products:
                    rec._sync_product_template(src_rpc, src_uid, dst_rpc, dst_uid, cp)
                    rec._save_checkpoint(cp)

                if rec.sync_taxes:
                    rec._sync_account_tax(src_rpc, src_uid, dst_rpc, dst_uid, cp)
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
        self.write({"checkpoint_json": "{}", "migrated_partners": 0, "migrated_products": 0, "migrated_taxes": 0})
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

    def action_start(self):
        self.ensure_one()
        run = self.env["sce.odoo.migration.run"].create(
            {
                "name": f"Migración {self.account_id.display_name}",
                "account_id": self.account_id.id,
                "migration_mode": self.migration_mode,
                "since_datetime": self.since_datetime,
                "sync_partners": self.sync_partners,
                "sync_products": self.sync_products,
                "sync_taxes": self.sync_taxes,
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