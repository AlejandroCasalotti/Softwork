from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SceTenant(models.Model):
    _name = "sce.tenant"
    _description = "SCE Connect Tenant"
    _order = "name"

    name = fields.Char(required=True, index=True)
    code = fields.Char(required=True, index=True)
    active = fields.Boolean(default=True)
    user_ids = fields.Many2many("res.users", string="Authorized Users")
    company_id = fields.Many2one("res.company", string="Administrative Company", ondelete="set null")
    external_connection_ids = fields.One2many(
        "sce.external.connection", "tenant_id", string="External Connections"
    )

    code_unique = models.Constraint(
        "UNIQUE(code)",
        "El código del tenant debe ser único.",
    )

    @api.constrains("code")
    def _check_code(self):
        for record in self:
            if not record.code or record.code != record.code.strip():
                raise ValidationError("El código del tenant no puede estar vacío ni tener espacios externos.")
