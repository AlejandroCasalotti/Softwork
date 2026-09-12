from datetime import timedelta

import requests

from odoo import fields
from odoo.exceptions import UserError


class MercadoLibreTokenService:
    REFRESH_MARGIN_MINUTES = 2

    def __init__(self, env):
        self.env = env

    def _identity(self, account):
        identity = self.env["sce.mercadolibre.account"].sudo().search(
            [("account_id", "=", account.id)], limit=1
        )
        if not identity:
            raise UserError("La cuenta SCE no tiene una identidad MercadoLibre conectada.")
        return identity

    def _credential(self, secret):
        return secret.with_context(sce_core_credential_access=True).get_value()

    def _clear_identity_tokens(self, identity, status, message):
        (identity.access_token_secret_id | identity.refresh_token_secret_id).sudo().write(
            {"active": False, "encrypted_value": False}
        )
        identity.sudo().write(
            {
                "access_token_secret_id": False,
                "refresh_token_secret_id": False,
                "expires_at": False,
                "status": status,
                "last_error": message,
            }
        )
        identity.account_id._sync_mercadolibre_runtime_state(
            identity=identity, last_error=message
        )

    def store_tokens(self, identity, access_token, refresh_token):
        secret_model = self.env["sce.credential.secret"].sudo()
        access_secret = secret_model.create(
            {"name": f"MercadoLibre access token {identity.name}", "account_id": identity.account_id.id, "secret_type": "mercadolibre_access_token"}
        )
        refresh_secret = secret_model.create(
            {"name": f"MercadoLibre refresh token {identity.name}", "account_id": identity.account_id.id, "secret_type": "mercadolibre_refresh_token"}
        )
        context = {"sce_core_credential_access": True}
        access_secret.with_context(**context).set_value(access_token)
        refresh_secret.with_context(**context).set_value(refresh_token)
        old_secrets = identity.access_token_secret_id | identity.refresh_token_secret_id
        identity.sudo().write({"access_token_secret_id": access_secret.id, "refresh_token_secret_id": refresh_secret.id})
        old_secrets.sudo().write({"active": False, "encrypted_value": False})

    def get_access_token(self, account):
        identity = self._identity(account)
        if identity.expires_at and identity.expires_at <= fields.Datetime.now() + timedelta(minutes=self.REFRESH_MARGIN_MINUTES):
            identity = self.refresh(identity)
        if not identity.access_token_secret_id:
            raise UserError("La cuenta MercadoLibre no tiene un access token disponible.")
        return self._credential(identity.access_token_secret_id)

    def refresh(self, identity):
        self.env.cr.execute("SELECT id FROM sce_mercadolibre_account WHERE id = %s FOR UPDATE", (identity.id,))
        identity.invalidate_recordset()
        if identity.expires_at and identity.expires_at > fields.Datetime.now() + timedelta(minutes=self.REFRESH_MARGIN_MINUTES):
            return identity
        if not identity.refresh_token_secret_id:
            raise UserError("La cuenta MercadoLibre no tiene refresh token válido.")
        from .mercadolibre_oauth_service import MercadoLibreOAuthService

        config = MercadoLibreOAuthService(self.env)._config()
        try:
            response = requests.post(
                MercadoLibreOAuthService.TOKEN_URL,
                data={"grant_type": "refresh_token", "client_id": config["client_id"], "client_secret": config["client_secret"], "refresh_token": self._credential(identity.refresh_token_secret_id)},
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as error:
            message = str(error)
            status = "auth_required" if "invalid_grant" in message else "error"
            user_message = (
                "Mercado Libre necesita que vuelvas a autorizar la conexión."
                if status == "auth_required"
                else "Mercado Libre rechazó temporalmente la sincronización. Podés intentarlo nuevamente."
            )
            if status == "auth_required":
                self._clear_identity_tokens(identity, status, user_message)
            else:
                identity.sudo().write({"status": status, "last_error": user_message})
                identity.account_id._sync_mercadolibre_runtime_state(
                    identity=identity, last_error=user_message
                )
            raise UserError(user_message) from error
        access_token = payload.get("access_token")
        if not access_token:
            raise UserError("MercadoLibre no devolvió un access token renovado.")
        self.store_tokens(identity, access_token, payload.get("refresh_token") or self._credential(identity.refresh_token_secret_id))
        expires_in = int(payload.get("expires_in", 0) or 0)
        identity.sudo().write({"expires_at": fields.Datetime.now() + timedelta(seconds=expires_in) if expires_in else False, "status": "connected", "last_error": False})
        identity.account_id._sync_mercadolibre_runtime_state(identity=identity)
        return identity

    def disconnect(self, account):
        identity = self._identity(account)
        (identity.access_token_secret_id | identity.refresh_token_secret_id).sudo().write(
            {"active": False, "encrypted_value": False}
        )
        identity.sudo().write({"access_token_secret_id": False, "refresh_token_secret_id": False, "expires_at": False, "status": "disconnected", "disconnected_at": fields.Datetime.now()})
        account._sync_mercadolibre_runtime_state(identity=identity)

    def mark_auth_required(self, account, message=None):
        identity = self._identity(account)
        self._clear_identity_tokens(
            identity,
            "auth_required",
            message or "Mercado Libre necesita que vuelvas a autorizar la conexión.",
        )