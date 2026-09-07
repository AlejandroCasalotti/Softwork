from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..services.connection_service import ConnectionService
from ..services.odoo_external_product_service import OdooExternalProductService


class SceExternalConnection(models.Model):
    _name = "sce.external.connection"
    _description = "SCE Connect External Odoo Connection"
    _order = "name"

    name = fields.Char(required=True)
    tenant_id = fields.Many2one("sce.tenant", required=True, ondelete="cascade", index=True)
    url = fields.Char(required=True)
    database = fields.Char(required=True)
    user = fields.Char(required=True)
    odoo_version = fields.Selection(
        selection=[("19", "Odoo 19")], required=True, default="19"
    )
    api_type = fields.Selection(selection=[("json2", "JSON-2")], required=True, default="json2")
    secret_id = fields.Many2one("sce.secret", required=True, ondelete="restrict", index=True)
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("connected", "Connected"),
            ("authentication_error", "Authentication Error"),
            ("permission_error", "Permission Error"),
            ("database_error", "Database Error"),
            ("network_error", "Network Error"),
            ("api_error", "API Error"),
            ("invalid_configuration", "Invalid Configuration"),
        ],
        default="draft",
        required=True,
    )
    last_test_at = fields.Datetime(readonly=True)
    last_test_status = fields.Char(readonly=True)
    last_error = fields.Text(readonly=True)
    timeout_seconds = fields.Integer(default=30, required=True)
    allow_insecure_http = fields.Boolean(default=False)
    allow_private_network = fields.Boolean(default=False)
    external_company_id = fields.Integer(
        string="ID empresa remota",
        help="ID de res.company en el Odoo remoto asociado a esta conexión.",
    )
    last_metadata_at = fields.Datetime(readonly=True)
    last_product_sync = fields.Datetime(readonly=True, help="Checkpoint incremental de sincronización de productos.")

    @api.constrains("tenant_id", "secret_id")
    def _check_secret_tenant(self):
        for record in self:
            if record.secret_id and record.tenant_id != record.secret_id.tenant_id:
                raise ValidationError("La conexión y su secreto deben pertenecer al mismo tenant.")

    @api.constrains("timeout_seconds")
    def _check_timeout(self):
        for record in self:
            if record.timeout_seconds <= 0:
                raise ValidationError("El timeout debe ser mayor que cero.")

    @api.constrains("external_company_id")
    def _check_external_company_id(self):
        for record in self:
            if record.external_company_id < 0:
                raise ValidationError("El ID de empresa remota debe ser un entero positivo.")

    def write(self, vals):
        if "external_company_id" in vals:
            new_company_id = vals["external_company_id"] or False
            for connection in self:
                if connection.external_company_id == new_company_id:
                    continue
                active_mappings = self.env["sce.external.product.mapping"].search_count(
                    [
                        ("external_connection_id", "=", connection.id),
                        ("active", "=", True),
                    ]
                )
                if active_mappings:
                    raise UserError(
                        "No se puede cambiar la empresa remota mientras existan mappings de productos activos."
                    )
        return super().write(vals)

    def action_test_connection(self):
        for record in self:
            result = ConnectionService(record, env=self.env).test_connection()
            record.sudo().write({"state": result["status"]})
        return True

    def action_test_controlled_write(self):
        self.ensure_one()
        result = ConnectionService(self, env=self.env).test_controlled_write()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "SCE Connect",
                "message": f"Prueba completada. Registros creados: {result['record_ids']}",
                "type": "success",
                "sticky": False,
            },
        }

    def action_read_metadata(self):
        self.ensure_one()
        result = ConnectionService(self, env=self.env).metadata("res.partner")
        self.sudo().write({"last_metadata_at": fields.Datetime.now()})
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Metadata recibida",
                "message": f"Campos descubiertos: {len(result)}",
                "type": "success",
                "sticky": False,
            },
        }

    def action_sync_products(self):
        self.ensure_one()
        if self.state != "connected":
            raise UserError("La conexión debe estar validada antes de sincronizar productos.")
        summary = OdooExternalProductService(self, env=self.env).sync_products()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Sincronización de productos completada",
                "message": (
                    "Templates: %(templates)s | Variantes: %(variants)s | "
                    "Mappings creados: %(created)s | actualizados: %(updated)s | "
                    "archivados: %(archived)s"
                ) % {
                    "templates": summary["templates_processed"],
                    "variants": summary["variants_processed"],
                    "created": summary["records_created"],
                    "updated": summary["records_updated"],
                    "archived": summary["mappings_archived"],
                },
                "type": "success",
                "sticky": False,
            },
        }
