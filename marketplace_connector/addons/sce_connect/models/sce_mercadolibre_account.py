import json

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ..services.errors import AuthenticationError
from ..services.mercadolibre_oauth import MercadoLibreOAuthService


class SceMercadoLibreAccount(models.Model):
    _name = "sce.mercadolibre.account"
    _description = "SCE Connect MercadoLibre Account"
    _order = "name"

    name = fields.Char(required=True)
    tenant_id = fields.Many2one("sce.tenant", required=True, ondelete="cascade", index=True)
    seller_user_id = fields.Char(string="Seller User ID", readonly=True, index=True)
    seller_nickname = fields.Char(string="Seller Nickname", readonly=True)
    access_token_secret_id = fields.Many2one("sce.secret", readonly=True, ondelete="set null")
    refresh_token_secret_id = fields.Many2one("sce.secret", readonly=True, ondelete="set null")
    scopes = fields.Char(readonly=True)
    expires_at = fields.Datetime(readonly=True)
    status = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("auth_pending", "Authorization Pending"),
            ("connected", "Connected"),
            ("token_refreshing", "Refreshing Token"),
            ("auth_required", "Authorization Required"),
            ("disconnected", "Disconnected"),
            ("error", "Error"),
        ],
        default="draft",
        required=True,
    )
    metadata_json = fields.Text(readonly=True)
    last_connection_test_at = fields.Datetime(readonly=True)
    last_error = fields.Text(readonly=True)
    connected_at = fields.Datetime(readonly=True)
    disconnected_at = fields.Datetime(readonly=True)

    _seller_unique = models.Constraint(
        "UNIQUE(tenant_id, seller_user_id)",
        "El vendedor de MercadoLibre ya está conectado a este tenant.",
    )

    @api.constrains("metadata_json")
    def _check_metadata_json(self):
        for record in self:
            if record.metadata_json:
                try:
                    json.loads(record.metadata_json)
                except (TypeError, ValueError) as error:
                    raise ValidationError("La metadata de MercadoLibre debe ser JSON válido.") from error

    def action_connect_mercadolibre(self):
        self.ensure_one()
        return {"type": "ir.actions.act_url", "url": MercadoLibreOAuthService(self.env).start(self), "target": "self"}

    def action_reconnect_mercadolibre(self):
        return self.action_connect_mercadolibre()

    def action_disconnect_mercadolibre(self):
        for account in self:
            MercadoLibreOAuthService(self.env).disconnect(account)
        return True

    def action_test_mercadolibre_connection(self):
        for account in self:
            try:
                result = MercadoLibreOAuthService(self.env).test_connection(account)
            except Exception as error:
                account.sudo().write({
                    "status": "auth_required" if isinstance(error, AuthenticationError) else "error",
                    "last_error": str(error),
                })
                raise
            account.sudo().write({"status": result["status"]})
        return True

    def action_refresh_mercadolibre_token(self):
        for account in self:
            MercadoLibreOAuthService(self.env).refresh(account)
        return True
