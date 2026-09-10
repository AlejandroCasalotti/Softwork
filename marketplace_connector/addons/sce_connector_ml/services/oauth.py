# -*- coding: utf-8 -*-
import logging
from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class MercadoLibreOAuth:
    """OAuth operations owned by the MercadoLibre connector."""

    def _persist_refreshed_tokens(self, refresh_result):
        return bool(isinstance(refresh_result, dict) and refresh_result.get("ok"))

    def authenticate(self):
        if not self.account.auth_code:
            raise UserError("Falta Authorization Code en la cuenta.")
        if not self.account.client_id or not self.account.client_secret or not self.account.redirect_uri:
            raise UserError("Faltan datos OAuth: client_id/client_secret/redirect_uri.")
        if not self.account.oauth_code_verifier:
            raise UserError("Falta code_verifier (PKCE). Presiona 'Conectar MercadoLibre' nuevamente.")

        payload = {
            "grant_type": "authorization_code",
            "client_id": (self.account.client_id or "").strip(),
            "client_secret": self.account.client_secret,
            "code": (self.account.auth_code or "").strip(),
            "redirect_uri": (self.account.redirect_uri or "").strip(),
            "code_verifier": (self.account.oauth_code_verifier or "").strip(),
        }
        data = self._request("POST", self.BASE_AUTH_URL, payload=payload, with_auth=False, form_encoded=True)
        expires_in = int(data.get("expires_in", 0) or 0)
        expires_at = fields.Datetime.now() + timedelta(seconds=expires_in) if expires_in else False
        external_user_id = False
        if data.get("access_token"):
            try:
                me = self._request(
                    "GET",
                    "/users/me",
                    with_auth=False,
                    params={"access_token": data["access_token"]},
                )
                external_user_id = str(me.get("id") or "")
            except Exception:
                _logger.exception("No se pudo resolver el usuario ML después del OAuth exchange.")
        return self._ok(
            action="authenticate",
            account_id=self.account.id,
            access_token=data.get("access_token"),
            refresh_token=data.get("refresh_token"),
            token_type=data.get("token_type"),
            token_expires_at=expires_at,
            external_user_id=external_user_id,
            raw=data,
        )

    def refresh_token(self):
        from .mercadolibre_token_service import MercadoLibreTokenService

        identity = MercadoLibreTokenService(self.env)._identity(self.account)
        MercadoLibreTokenService(self.env).refresh(identity)
        return self._ok(action="refresh_token", account_id=self.account.id)
