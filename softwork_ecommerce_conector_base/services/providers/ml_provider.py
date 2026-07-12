# -*- coding: utf-8 -*-
import json
import time

from odoo import fields
from odoo.exceptions import UserError

try:
    import requests
except Exception:  # pragma: no cover
    requests = None

from ..provider_interface import IProvider


class MercadoLibreProvider(IProvider):
    BASE_AUTH_URL = "https://api.mercadolibre.com/oauth/token"
    BASE_API_URL = "https://api.mercadolibre.com"
    """
    Implementación base de provider MercadoLibre.
    Deja estructura productiva para extender integración real por API.
    """

    def __init__(self, env, account):
        self.env = env
        self.account = account

    def _ok(self, **kwargs):
        payload = {"ok": True, "provider": "mercadolibre"}
        payload.update(kwargs)
        return payload

    def _ensure_requests(self):
        if not requests:
            raise UserError("La librería Python 'requests' no está disponible en el entorno Odoo.")

    def _request(self, method, endpoint, payload=None, params=None, with_auth=True):
        self._ensure_requests()
        headers = {"Content-Type": "application/json"}
        if with_auth:
            token = self.account.access_token
            if not token:
                raise UserError("No hay access token configurado en la cuenta.")
            headers["Authorization"] = f"Bearer {token}"

        url = endpoint if endpoint.startswith("http") else f"{self.BASE_API_URL}{endpoint}"
        timeout_seconds = int(self.account.provider_timeout_seconds or 30)
        if timeout_seconds <= 0:
            timeout_seconds = 30
        started_at = time.monotonic()
        try:
            response = requests.request(
                method=method,
                url=url,
                json=payload,
                params=params,
                headers=headers,
                timeout=timeout_seconds,
            )
        except requests.Timeout:
            raise UserError(
                f"Tiempo de espera agotado ({timeout_seconds}s) al conectar con MercadoLibre. "
                "Intenta nuevamente."
            )
        except requests.RequestException as err:
            raise UserError(f"Error de red con MercadoLibre: {err}")

        elapsed_ms = int((time.monotonic() - started_at) * 1000)
        if response.status_code >= 400:
            raise UserError(f"Error MercadoLibre {response.status_code}: {response.text}")
        if not response.text:
            return {"_meta": {"elapsed_ms": elapsed_ms}}
        data = response.json()
        if isinstance(data, dict):
            data.setdefault("_meta", {})
            data["_meta"]["elapsed_ms"] = elapsed_ms
        return data

    def authenticate(self):
        if not self.account.auth_code:
            raise UserError("Falta Authorization Code en la cuenta.")
        if not self.account.client_id or not self.account.client_secret or not self.account.redirect_uri:
            raise UserError("Faltan datos OAuth: client_id/client_secret/redirect_uri.")

        if not self.account.oauth_code_verifier:
            raise UserError("Falta code_verifier (PKCE). Presiona 'Conectar MercadoLibre' nuevamente.")
        payload = {
            "grant_type": "authorization_code",
            "client_id": self.account.client_id,
            "client_secret": self.account.client_secret,
            "code": self.account.auth_code,
            "redirect_uri": self.account.redirect_uri,
            "code_verifier": self.account.oauth_code_verifier,
        }
        data = self._request("POST", self.BASE_AUTH_URL, payload=payload, with_auth=False)
        elapsed_ms = (data.get("_meta") or {}).get("elapsed_ms") if isinstance(data, dict) else None
        expires_in = int(data.get("expires_in", 0) or 0)
        token_expires_at = fields.Datetime.now() + fields.DateUtils.to_timedelta(seconds=expires_in) if expires_in else False

        external_user_id = False
        access = data.get("access_token")
        if access:
            try:
                me = self._request(
                    "GET",
                    "/users/me",
                    with_auth=False,
                    params={"access_token": access},
                )
                external_user_id = str(me.get("id") or "")
            except Exception:
                external_user_id = False

        return self._ok(
            action="authenticate",
            account_id=self.account.id,
            access_token=data.get("access_token"),
            refresh_token=data.get("refresh_token"),
            token_type=data.get("token_type"),
            token_expires_at=token_expires_at,
            external_user_id=external_user_id,
            raw=data,
            elapsed_ms=elapsed_ms,
        )

    def refresh_token(self):
        if not self.account.refresh_token:
            raise UserError("Falta refresh token en la cuenta.")
        if not self.account.client_id or not self.account.client_secret:
            raise UserError("Faltan datos OAuth: client_id/client_secret.")

        payload = {
            "grant_type": "refresh_token",
            "client_id": self.account.client_id,
            "client_secret": self.account.client_secret,
            "refresh_token": self.account.refresh_token,
        }
        data = self._request("POST", self.BASE_AUTH_URL, payload=payload, with_auth=False)
        elapsed_ms = (data.get("_meta") or {}).get("elapsed_ms") if isinstance(data, dict) else None
        expires_in = int(data.get("expires_in", 0) or 0)
        token_expires_at = fields.Datetime.now() + fields.DateUtils.to_timedelta(seconds=expires_in) if expires_in else False

        return self._ok(
            action="refresh_token",
            account_id=self.account.id,
            access_token=data.get("access_token"),
            refresh_token=data.get("refresh_token"),
            token_type=data.get("token_type"),
            token_expires_at=token_expires_at,
            raw=data,
            elapsed_ms=elapsed_ms,
        )

    def health(self):
        me = self._request("GET", "/users/me")
        return self._ok(action="health", status="up", account_id=self.account.id, user_id=me.get("id"))

    def publish_product(self, payload):
        return self._ok(action="publish_product", payload=payload or {})

    def update_product(self, payload):
        return self._ok(action="update_product", payload=payload or {})

    def delete_product(self, payload):
        return self._ok(action="delete_product", payload=payload or {})

    def update_stock(self, payload):
        return self._ok(action="update_stock", payload=payload or {})

    def update_price(self, payload):
        return self._ok(action="update_price", payload=payload or {})

    def get_orders(self, params=None):
        return self._ok(action="get_orders", items=[], params=params or {})

    def get_order(self, external_id):
        return self._ok(action="get_order", external_id=external_id, order={})

    def cancel_order(self, external_id):
        return self._ok(action="cancel_order", external_id=external_id)

    def get_messages(self, params=None):
        return self._ok(action="get_messages", items=[], params=params or {})

    def answer_message(self, payload):
        return self._ok(action="answer_message", payload=payload or {})

    def download_invoice(self, external_id):
        return self._ok(action="download_invoice", external_id=external_id, content_b64=False)

    def upload_invoice(self, payload):
        return self._ok(action="upload_invoice", payload=payload or {})

    def sync(self, params=None):
        params = params or {}
        operation = params.get("operation", "sync_products")
        payload = params.get("payload", {})
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except Exception:
                payload = {"raw": payload}

        if operation == "sync_products":
            return self.publish_product(payload)
        if operation == "sync_stock":
            return self.update_stock(payload)
        if operation == "sync_prices":
            return self.update_price(payload)
        if operation == "import_orders":
            return self.get_orders(params)
        if operation == "health_check":
            return self.health()
        if operation == "sync_messages":
            return self.get_messages(params)
        return self._ok(action="sync", params=params)

    def webhook(self, payload):
        return self._ok(action="webhook", payload=payload or {})