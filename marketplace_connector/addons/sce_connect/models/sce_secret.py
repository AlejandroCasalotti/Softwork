from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError

from ..services.secret_storage import SecretStorage


class SceSecret(models.Model):
    _name = "sce.secret"
    _description = "SCE Connect Secret"
    _order = "create_date desc"

    name = fields.Char(required=True)
    tenant_id = fields.Many2one("sce.tenant", required=True, ondelete="cascade", index=True)
    secret_type = fields.Selection(
        selection=[
            ("odoo_api_key", "Odoo API Key"),
            ("mercadolibre_client_secret", "MercadoLibre Client Secret"),
            ("mercadolibre_access_token", "MercadoLibre Access Token"),
            ("mercadolibre_refresh_token", "MercadoLibre Refresh Token"),
            ("oauth_pkce_verifier", "OAuth PKCE Verifier"),
        ],
        required=True,
    )
    encrypted_value = fields.Text(
        readonly=True,
        copy=False,
        groups="sce_connect.group_sce_connect_admin",
    )
    masked_value = fields.Char(compute="_compute_masked_value")
    active = fields.Boolean(default=True)
    last_rotated_at = fields.Datetime(readonly=True)

    @api.depends("encrypted_value")
    def _compute_masked_value(self):
        for record in self:
            record.masked_value = "********" if record.encrypted_value else ""

    def set_value(self, value):
        self.ensure_one()
        if not self.env.context.get("sce_backend_secret_access"):
            raise AccessError("Los secretos solo pueden gestionarse desde el backend de SCE Connect.")
        if not value:
            raise UserError("El secreto no puede estar vacío.")
        encrypted = SecretStorage.from_environment().encrypt(value)
        self.sudo().write({"encrypted_value": encrypted, "last_rotated_at": fields.Datetime.now()})
        return True

    def get_value(self):
        self.ensure_one()
        if not self.env.context.get("sce_backend_secret_access"):
            raise AccessError("Los secretos solo pueden leerse desde el backend de SCE Connect.")
        return SecretStorage.from_environment().decrypt(self.encrypted_value)

    def action_set_value(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Set Secret",
            "res_model": "sce.secret.set.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_secret_id": self.id},
        }
