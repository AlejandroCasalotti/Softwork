from odoo import fields, models
from odoo.exceptions import AccessError

from ..services.core_secret_service import CoreSecretService


class SceCredentialSecret(models.Model):
    _name = "sce.credential.secret"
    _description = "SCE Core Provider Credential"
    _order = "create_date desc"

    name = fields.Char(required=True)
    account_id = fields.Many2one("sce.account", ondelete="cascade", index=True)
    secret_type = fields.Selection(
        [
            ("mercadolibre_access_token", "MercadoLibre Access Token"),
            ("mercadolibre_refresh_token", "MercadoLibre Refresh Token"),
            ("oauth_pkce_verifier", "OAuth PKCE Verifier"),
        ],
        required=True,
    )
    encrypted_value = fields.Text(readonly=True, copy=False, groups="base.group_system")
    key_version = fields.Char(readonly=True)
    active = fields.Boolean(default=True)
    last_rotated_at = fields.Datetime(readonly=True)

    def set_value(self, value):
        self.ensure_one()
        if not self.env.context.get("sce_core_credential_access"):
            raise AccessError("Las credenciales solo pueden gestionarse desde servicios internos de SCE.")
        self.sudo().write(
            {
                "encrypted_value": CoreSecretService.from_runtime().encrypt(value),
                "last_rotated_at": fields.Datetime.now(),
            }
        )

    def get_value(self):
        self.ensure_one()
        if not self.env.context.get("sce_core_credential_access"):
            raise AccessError("Las credenciales solo pueden leerse desde servicios internos de SCE.")
        return CoreSecretService.from_runtime().decrypt(self.encrypted_value)