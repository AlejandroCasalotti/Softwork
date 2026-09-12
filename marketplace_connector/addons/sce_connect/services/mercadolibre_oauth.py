import json
import logging
import os
from datetime import timedelta
from urllib.parse import urlencode

from odoo import fields
from odoo.exceptions import UserError

from .errors import AuthenticationError, ConfigurationError, NetworkError, PermissionError
from .mercadolibre_transport import MercadoLibreConnectTransport
from .oauth_state import OAuthStateService

_logger = logging.getLogger(__name__)


class MercadoLibreOAuthService:
    CLIENT_ID_ENV = "SCE_ML_CLIENT_ID"
    CLIENT_SECRET_ENV = "SCE_ML_CLIENT_SECRET"
    REDIRECT_URI_ENV = "SCE_ML_REDIRECT_URI"
    AUTHORIZATION_URL = "https://auth.mercadolibre.com.ar/authorization"

    def __init__(self, env, session=None):
        self.env = env
        self.session = session

    def _config(self):
        values = {
            "client_id": os.environ.get(self.CLIENT_ID_ENV, "").strip(),
            "client_secret": os.environ.get(self.CLIENT_SECRET_ENV, ""),
            "redirect_uri": os.environ.get(self.REDIRECT_URI_ENV, "").strip(),
        }
        if not all(values.values()):
            raise ConfigurationError(
                "Falta configurar SCE_ML_CLIENT_ID, SCE_ML_CLIENT_SECRET o SCE_ML_REDIRECT_URI en el servidor."
            )
        if not values["redirect_uri"].startswith("https://"):
            raise ConfigurationError("SCE_ML_REDIRECT_URI debe utilizar HTTPS.")
        return values

    def _transport(self):
        return MercadoLibreConnectTransport(session=self.session)

    def start(self, account):
        config = self._config()
        tenant = account.tenant_id
        transaction_state, challenge, _transaction = OAuthStateService(self.env).create(
            tenant, account, self.env.user
        )
        return f"{self.AUTHORIZATION_URL}?{urlencode({'response_type': 'code', 'client_id': config['client_id'], 'redirect_uri': config['redirect_uri'], 'state': transaction_state, 'code_challenge': challenge, 'code_challenge_method': 'S256'})}"

    def complete(self, state, code, user):
        config = self._config()
        transaction = OAuthStateService(self.env).validate_and_consume(state, user)
        if not code:
            raise UserError("MercadoLibre no devolvió un authorization code.")
        verifier = transaction.code_verifier_secret_id.with_context(
            sce_backend_secret_access=True
        ).get_value()
        data = self._transport().request(
            "POST",
            MercadoLibreConnectTransport.AUTH_BASE_URL,
            payload={
                "grant_type": "authorization_code",
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "code": code,
                "redirect_uri": config["redirect_uri"],
                "code_verifier": verifier,
            },
            form_encoded=True,
        )
        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        if not access_token or not refresh_token:
            raise AuthenticationError("MercadoLibre no devolvió los tokens esperados.")
        seller = self._transport().request(
            "GET",
            f"{MercadoLibreConnectTransport.API_BASE_URL}/users/me",
            access_token=access_token,
        )
        seller_id = seller.get("id")
        if not seller_id:
            raise AuthenticationError("No se pudo identificar el vendedor de MercadoLibre.")
        account = transaction.mercadolibre_account_id.sudo()
        access_secret, refresh_secret = self._store_tokens(account, access_token, refresh_token)
        expires_in = int(data.get("expires_in", 0) or 0)
        account.write(
            {
                "seller_user_id": str(seller_id),
                "seller_nickname": seller.get("nickname") or False,
                "access_token_secret_id": access_secret.id,
                "refresh_token_secret_id": refresh_secret.id,
                "scopes": data.get("scope") or False,
                "expires_at": fields.Datetime.now() + timedelta(seconds=expires_in) if expires_in else False,
                "status": "connected",
                "metadata_json": json.dumps({"token_type": data.get("token_type"), "site_id": seller.get("site_id")}),
                "connected_at": fields.Datetime.now(),
                "last_error": False,
            }
        )
        transaction.code_verifier_secret_id.sudo().write({"active": False, "encrypted_value": False})
        _logger.info("MercadoLibre OAuth completed tenant_id=%s seller_id=%s", account.tenant_id.id, account.seller_user_id)
        return account

    def refresh(self, account):
        if account.status == "disconnected" or not account.refresh_token_secret_id:
            raise AuthenticationError("La cuenta MercadoLibre no tiene refresh token válido.")
        self.env.cr.execute(
            "SELECT id FROM sce_mercadolibre_account WHERE id = %s FOR UPDATE",
            (account.id,),
        )
        account.invalidate_recordset()
        if account.expires_at and account.expires_at > fields.Datetime.now() + timedelta(minutes=2):
            return account
        config = self._config()
        account.sudo().write({"status": "token_refreshing"})
        try:
            refresh_token = account.refresh_token_secret_id.with_context(
                sce_backend_secret_access=True
            ).get_value()
            data = self._transport().request(
                "POST",
                MercadoLibreConnectTransport.AUTH_BASE_URL,
                payload={
                    "grant_type": "refresh_token",
                    "client_id": config["client_id"],
                    "client_secret": config["client_secret"],
                    "refresh_token": refresh_token,
                },
                form_encoded=True,
            )
            access_token = data.get("access_token")
            new_refresh_token = data.get("refresh_token") or refresh_token
            if not access_token:
                raise AuthenticationError("MercadoLibre no devolvió un access token renovado.")
            access_secret, refresh_secret = self._store_tokens(account, access_token, new_refresh_token)
            expires_in = int(data.get("expires_in", 0) or 0)
            account.sudo().write(
                {
                    "access_token_secret_id": access_secret.id,
                    "refresh_token_secret_id": refresh_secret.id,
                    "expires_at": fields.Datetime.now() + timedelta(seconds=expires_in) if expires_in else False,
                    "status": "connected",
                    "last_error": False,
                }
            )
            _logger.info("MercadoLibre token refreshed tenant_id=%s seller_id=%s", account.tenant_id.id, account.seller_user_id)
            return account
        except (AuthenticationError, PermissionError, NetworkError, ConfigurationError) as error:
            account.sudo().write({"status": "auth_required" if isinstance(error, AuthenticationError) else "error", "last_error": str(error)})
            raise

    def test_connection(self, account):
        if account.status == "disconnected":
            return {"status": "disconnected"}
        if account.expires_at and account.expires_at <= fields.Datetime.now() + timedelta(minutes=2):
            self.refresh(account)
        access_token = account.access_token_secret_id.with_context(
            sce_backend_secret_access=True
        ).get_value()
        seller = self._transport().request(
            "GET",
            f"{MercadoLibreConnectTransport.API_BASE_URL}/users/me",
            access_token=access_token,
        )
        if str(seller.get("id")) != account.seller_user_id:
            raise AuthenticationError("La identidad del vendedor no coincide con la cuenta Connect.")
        account.sudo().write({"last_connection_test_at": fields.Datetime.now(), "last_error": False})
        return {"status": "connected", "seller_id": account.seller_user_id}

    def disconnect(self, account):
        for secret in (account.access_token_secret_id, account.refresh_token_secret_id):
            if secret:
                secret.sudo().write({"active": False, "encrypted_value": False})
        account.sudo().write(
            {
                "status": "disconnected",
                "access_token_secret_id": False,
                "refresh_token_secret_id": False,
                "expires_at": False,
                "disconnected_at": fields.Datetime.now(),
            }
        )
        _logger.info("MercadoLibre disconnected tenant_id=%s seller_id=%s", account.tenant_id.id, account.seller_user_id)

    def _store_tokens(self, account, access_token, refresh_token):
        secret_model = self.env["sce.secret"].sudo()
        access_secret = secret_model.create(
            {"name": f"MercadoLibre access token {account.name}", "tenant_id": account.tenant_id.id, "secret_type": "mercadolibre_access_token"}
        )
        refresh_secret = secret_model.create(
            {"name": f"MercadoLibre refresh token {account.name}", "tenant_id": account.tenant_id.id, "secret_type": "mercadolibre_refresh_token"}
        )
        backend_context = {"sce_backend_secret_access": True}
        access_secret.with_context(**backend_context).set_value(access_token)
        refresh_secret.with_context(**backend_context).set_value(refresh_token)
        for old_secret in (account.access_token_secret_id, account.refresh_token_secret_id):
            if old_secret:
                old_secret.sudo().write({"active": False, "encrypted_value": False})
        return access_secret, refresh_secret
