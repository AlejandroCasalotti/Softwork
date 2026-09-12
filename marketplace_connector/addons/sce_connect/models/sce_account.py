from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SceAccount(models.Model):
    _inherit = "sce.account"

    tenant_id = fields.Many2one(
        "sce.tenant",
        string="Tenant SCE",
        required=False,
        ondelete="restrict",
        index=True,
    )
    external_connection_id = fields.Many2one(
        "sce.external.connection",
        string="Conexión Odoo",
        required=False,
        ondelete="restrict",
        index=True,
    )

    connect_mercadolibre_account_id = fields.Many2one(
        "sce.mercadolibre.account",
        string="Cuenta MercadoLibre Connect",
        ondelete="restrict",
        index=True,
        copy=False,
    )
    connect_ownership_state = fields.Selection(
        [
            ("legacy", "Legacy / sin ownership Connect"),
            ("incomplete", "Ownership Connect incompleto"),
            ("ready", "Ownership Connect completo"),
        ],
        compute="_compute_connect_ownership_state",
        string="Estado ownership Connect",
    )
    stock_policy_ids = fields.One2many(
        "sce.connect.stock.policy", "account_id", string="Política de stock"
    )
    price_policy_ids = fields.One2many(
        "sce.connect.price.policy", "account_id", string="Política de precio"
    )

    def action_open_connect_preview(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Previsualizar configuración",
            "res_model": "sce.connect.preview.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_account_id": self.id},
        }

    @api.depends("tenant_id", "external_connection_id", "connect_mercadolibre_account_id")
    def _compute_connect_ownership_state(self):
        for account in self:
            values = (
                bool(account.tenant_id),
                bool(account.external_connection_id),
                bool(account.connect_mercadolibre_account_id),
            )
            if not any(values):
                account.connect_ownership_state = "legacy"
            elif all(values):
                account.connect_ownership_state = "ready"
            else:
                account.connect_ownership_state = "incomplete"

    @api.constrains(
        "tenant_id",
        "external_connection_id",
        "connect_mercadolibre_account_id",
        "provider_type",
        "connector_id",
        "external_user_id",
    )
    def _check_connect_mercadolibre_account(self):
        for account in self:
            if bool(account.tenant_id) != bool(account.external_connection_id):
                raise ValidationError(
                    "La cuenta SCE Connect debe tener tenant y conexión Odoo juntos."
                )
            if account.tenant_id and account.external_connection_id:
                if account.external_connection_id.tenant_id != account.tenant_id:
                    raise ValidationError(
                        "La conexión Odoo debe pertenecer al mismo tenant que la cuenta SCE."
                    )
            connect_account = account.connect_mercadolibre_account_id
            if not connect_account:
                continue
            if not account.tenant_id or not account.external_connection_id:
                raise ValidationError(
                    "La identidad MercadoLibre Connect requiere tenant y conexión Odoo configurados."
                )
            if account.tenant_id and connect_account.tenant_id != account.tenant_id:
                raise ValidationError(
                    "La identidad MercadoLibre debe pertenecer al mismo tenant que la cuenta SCE."
                )
            connector_type = account.connector_id.provider_type
            if account.provider_type != "mercadolibre" or connector_type != "mercadolibre":
                raise ValidationError(
                    "La cuenta MercadoLibre Connect solo puede vincularse a una cuenta SCE MercadoLibre."
                )
            if (
                account.external_user_id
                and connect_account.seller_user_id
                and str(account.external_user_id) != str(connect_account.seller_user_id)
            ):
                raise ValidationError(
                    "El vendedor MercadoLibre Connect no coincide con el usuario externo de la cuenta SCE."
                )

    def _uses_connect_mercadolibre_credentials(self):
        self.ensure_one()
        return bool(self.connect_mercadolibre_account_id)

    def _get_mercadolibre_access_token(self):
        self.ensure_one()
        if not self._uses_connect_mercadolibre_credentials():
            return self.access_token
        from ..services.mercadolibre_credential_resolver import (
            MercadoLibreConnectCredentialResolver,
        )

        return MercadoLibreConnectCredentialResolver(self.env, self).get_access_token()

    def _get_mercadolibre_external_user_id(self):
        self.ensure_one()
        if self._uses_connect_mercadolibre_credentials():
            return self.connect_mercadolibre_account_id.seller_user_id or False
        return self.external_user_id