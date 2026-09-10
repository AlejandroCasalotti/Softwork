import json

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SceMercadoLibreAccount(models.Model):
    _name = "sce.mercadolibre.account"
    _description = "SCE MercadoLibre Account"
    _order = "name"

    name = fields.Char(required=True)
    account_id = fields.Many2one("sce.account", required=True, ondelete="cascade", index=True)
    seller_user_id = fields.Char(readonly=True, index=True)
    seller_nickname = fields.Char(readonly=True)
    site_id = fields.Char(readonly=True)
    country_id = fields.Char(readonly=True)
    access_token_secret_id = fields.Many2one("sce.credential.secret", readonly=True, ondelete="set null")
    refresh_token_secret_id = fields.Many2one("sce.credential.secret", readonly=True, ondelete="set null")
    scopes = fields.Char(readonly=True)
    expires_at = fields.Datetime(readonly=True)
    status = fields.Selection(
        [
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

    _account_unique = models.Constraint(
        "UNIQUE(account_id)", "La cuenta SCE ya tiene una identidad MercadoLibre."
    )

    @api.constrains("metadata_json")
    def _check_metadata_json(self):
        for record in self:
            if record.metadata_json:
                try:
                    json.loads(record.metadata_json)
                except (TypeError, ValueError) as error:
                    raise ValidationError("La metadata de MercadoLibre debe ser JSON válido.") from error