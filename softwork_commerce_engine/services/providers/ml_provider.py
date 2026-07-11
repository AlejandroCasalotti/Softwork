# -*- coding: utf-8 -*-
import json

from ..provider_interface import IProvider


class MercadoLibreProvider(IProvider):
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

    def authenticate(self):
        return self._ok(action="authenticate", account_id=self.account.id)

    def refresh_token(self):
        return self._ok(action="refresh_token", account_id=self.account.id)

    def health(self):
        return self._ok(action="health", status="up", account_id=self.account.id)

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