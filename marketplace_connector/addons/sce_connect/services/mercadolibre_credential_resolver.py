from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError

from .mercadolibre_oauth import MercadoLibreOAuthService


class MercadoLibreConnectCredentialResolver:
    """Resolve credentials owned by a linked SCE Connect MercadoLibre account."""

    REFRESH_MARGIN_MINUTES = 2

    def __init__(self, env, execution_account):
        self.env = env
        self.execution_account = execution_account

    def _connect_account(self):
        self.execution_account.ensure_one()
        account = self.execution_account.connect_mercadolibre_account_id
        if not account:
            raise UserError("La cuenta SCE no tiene una cuenta MercadoLibre Connect vinculada.")
        return account

    def get_access_token(self):
        account = self._connect_account()
        refresh_deadline = fields.Datetime.now() + timedelta(minutes=self.REFRESH_MARGIN_MINUTES)
        if account.expires_at and account.expires_at <= refresh_deadline:
            account = MercadoLibreOAuthService(self.env).refresh(account)
        secret = account.access_token_secret_id
        if not secret:
            raise UserError("La cuenta MercadoLibre Connect no tiene un access token disponible.")
        return secret.with_context(sce_backend_secret_access=True).get_value()

    def get_seller_user_id(self):
        seller_user_id = self._connect_account().seller_user_id
        return str(seller_user_id) if seller_user_id else False