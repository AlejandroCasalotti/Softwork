import base64
import hashlib
import json
import os
import secrets
from datetime import timedelta
from urllib.parse import urlencode

import requests

from odoo import fields
from odoo.exceptions import AccessError, UserError


class MercadoLibreOAuthService:
    AUTHORIZATION_URL = "https://auth.mercadolibre.com.ar/authorization"
    TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
    API_URL = "https://api.mercadolibre.com"
    STATE_TTL_MINUTES = 10

    def __init__(self, env):
        self.env = env

    def _config(self):
        params = self.env["ir.config_parameter"].sudo()
        values = {
            "client_id": (
                os.environ.get("SCE_ML_CLIENT_ID", "").strip()
                or params.get_param("sce.mercadolibre.client_id", "").strip()
            ),
            "client_secret": (
                os.environ.get("SCE_ML_CLIENT_SECRET", "")
                or params.get_param("sce.mercadolibre.client_secret", "")
            ),
            "redirect_uri": (
                os.environ.get("SCE_ML_REDIRECT_URI", "").strip()
                or params.get_param("sce.mercadolibre.redirect_uri", "").strip()
            ),
        }
        if not all(values.values()):
            raise UserError(
                "Falta la configuración operativa de la aplicación MercadoLibre. "
                "Configura sce.mercadolibre.client_id, sce.mercadolibre.client_secret "
                "y sce.mercadolibre.redirect_uri en Parámetros del sistema."
            )
        return values

    @staticmethod
    def _pkce_pair():
        verifier = secrets.token_urlsafe(64)[:128]
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).decode().rstrip("=")
        return verifier, challenge

    def _identity(self, account):
        identity = self.env["sce.mercadolibre.account"].sudo().search(
            [("account_id", "=", account.id)], limit=1
        )
        if not identity:
            identity = self.env["sce.mercadolibre.account"].sudo().create(
                {"name": account.name, "account_id": account.id}
            )
        return identity

    def start(self, account, user=None):
        account.ensure_one()
        if account.provider_type != "mercadolibre":
            raise UserError("La cuenta no corresponde a MercadoLibre.")
        config = self._config()
        user = user or self.env.user
        identity = self._identity(account)
        state = secrets.token_urlsafe(32)
        verifier, challenge = self._pkce_pair()
        secret = self.env["sce.credential.secret"].sudo().create(
            {
                "name": f"OAuth PKCE verifier {account.name}",
                "account_id": account.id,
                "secret_type": "oauth_pkce_verifier",
            }
        )
        secret.with_context(sce_core_credential_access=True).set_value(verifier)
        self.env["sce.oauth.transaction"].sudo().create(
            {
                "state_hash": self.env["sce.oauth.transaction"].hash_state(state),
                "user_id": user.id,
                "account_id": account.id,
                "mercadolibre_account_id": identity.id,
                "code_verifier_secret_id": secret.id,
                "expires_at": fields.Datetime.now() + timedelta(minutes=self.STATE_TTL_MINUTES),
            }
        )
        identity.write({"status": "auth_pending", "last_error": False})
        return f"{self.AUTHORIZATION_URL}?{urlencode({'response_type': 'code', 'client_id': config['client_id'], 'redirect_uri': config['redirect_uri'], 'state': state, 'code_challenge': challenge, 'code_challenge_method': 'S256'})}"

    def complete(self, state, code, user):
        if not state or not code:
            raise UserError("MercadoLibre no devolvió un código de autorización válido.")
        transaction = self.env["sce.oauth.transaction"].sudo().search(
            [("state_hash", "=", self.env["sce.oauth.transaction"].hash_state(state))], limit=1
        )
        if not transaction or transaction.user_id != user:
            raise AccessError("El estado OAuth no es válido para el usuario actual.")
        transaction.consume()
        verifier = transaction.code_verifier_secret_id.with_context(
            sce_core_credential_access=True
        ).get_value()
        try:
            data = requests.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "client_id": self._config()["client_id"],
                    "client_secret": self._config()["client_secret"],
                    "code": code.strip(),
                    "redirect_uri": self._config()["redirect_uri"],
                    "code_verifier": verifier,
                },
                timeout=30,
            )
            data.raise_for_status()
            payload = data.json()
        except requests.RequestException as error:
            transaction.mercadolibre_account_id.write({"status": "error", "last_error": str(error)})
            raise UserError("No se pudo completar la autorización con MercadoLibre.") from error
        access_token = payload.get("access_token")
        refresh_token = payload.get("refresh_token")
        if not access_token or not refresh_token:
            raise UserError("MercadoLibre no devolvió los tokens esperados.")
        try:
            response = requests.get(
                f"{self.API_URL}/users/me",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=30,
            )
            response.raise_for_status()
            seller = response.json()
        except requests.RequestException as error:
            raise UserError("No se pudo identificar al vendedor autenticado de MercadoLibre.") from error
        from .mercadolibre_token_service import MercadoLibreTokenService

        identity = transaction.mercadolibre_account_id
        MercadoLibreTokenService(self.env).store_tokens(identity, access_token, refresh_token)
        expires_in = int(payload.get("expires_in", 0) or 0)
        identity.write(
            {
                "seller_user_id": str(seller.get("id") or "") or False,
                "seller_nickname": seller.get("nickname") or False,
                "site_id": seller.get("site_id") or False,
                "country_id": seller.get("country_id") or False,
                "scopes": payload.get("scope") or False,
                "expires_at": fields.Datetime.now() + timedelta(seconds=expires_in) if expires_in else False,
                "status": "connected",
                "metadata_json": json.dumps({"token_type": payload.get("token_type")}),
                "connected_at": fields.Datetime.now(),
                "last_error": False,
            }
        )
        transaction.code_verifier_secret_id.sudo().write({"active": False, "encrypted_value": False})
        transaction.account_id.sudo().write(
            {"state": "connected", "external_user_id": identity.seller_user_id, "last_error": False}
        )
        return identity