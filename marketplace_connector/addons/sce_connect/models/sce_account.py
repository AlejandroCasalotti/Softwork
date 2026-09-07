from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SceAccount(models.Model):
    _inherit = "sce.account"

    connect_mercadolibre_account_id = fields.Many2one(
        "sce.mercadolibre.account",
        string="Cuenta MercadoLibre Connect",
        ondelete="restrict",
        index=True,
        copy=False,
    )

    @api.constrains(
        "connect_mercadolibre_account_id",
        "provider_type",
        "connector_id",
        "external_user_id",
    )
    def _check_connect_mercadolibre_account(self):
        for account in self:
            connect_account = account.connect_mercadolibre_account_id
            if not connect_account:
                continue
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