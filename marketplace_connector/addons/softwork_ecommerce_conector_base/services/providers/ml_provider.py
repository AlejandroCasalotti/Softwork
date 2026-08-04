# -*- coding: utf-8 -*-
import base64
import json
import logging
import time
from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError

try:
    import requests
except Exception:  # pragma: no cover
    requests = None

from ..provider_interface import IProvider

_logger = logging.getLogger(__name__)


class MercadoLibreProvider(IProvider):
    BASE_AUTH_URL = "https://api.mercadolibre.com/oauth/token"
    BASE_API_URL = "https://api.mercadolibre.com"
    """
    Provider MercadoLibre con operaciones reales para catálogo, órdenes y mensajería.
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

    def _to_int(self, value, default=0):
        try:
            return int(value)
        except Exception:
            return default

    def _to_float(self, value, default=0.0):
        try:
            return float(value)
        except Exception:
            return default

    def _request(self, method, endpoint, payload=None, params=None, with_auth=True, form_encoded=False):
        self._ensure_requests()
        headers = {"Content-Type": "application/json"}
        if form_encoded:
            headers["Content-Type"] = "application/x-www-form-urlencoded"

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
            request_kwargs = {
                "method": method,
                "url": url,
                "params": params,
                "headers": headers,
                "timeout": timeout_seconds,
            }
            if form_encoded:
                request_kwargs["data"] = payload
            else:
                request_kwargs["json"] = payload
            response = requests.request(**request_kwargs)
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

    def _extract_item_id(self, payload):
        payload = payload or {}
        item_id = payload.get("id") or payload.get("item_id") or payload.get("ml_item_id")
        if not item_id:
            raise UserError("Falta item_id/id para operar publicación de MercadoLibre.")
        return str(item_id).strip()

    def _normalize_attributes(self, payload):
        attrs = payload.get("attributes") or []
        if isinstance(attrs, str):
            try:
                attrs = json.loads(attrs)
            except Exception:
                attrs = []
        if not isinstance(attrs, list):
            attrs = []
        normalized = []
        for at in attrs:
            if not isinstance(at, dict):
                continue
            if at.get("id") and (at.get("value_name") is not None or at.get("value_id") is not None):
                normalized.append(at)
        return normalized

    def _normalize_pictures(self, payload):
        pictures = payload.get("pictures") or []
        if not isinstance(pictures, list):
            pictures = []
        normalized = []
        for p in pictures:
            if isinstance(p, dict) and p.get("source"):
                normalized.append({"source": p["source"]})
            elif isinstance(p, str) and p.strip():
                normalized.append({"source": p.strip()})
        image_b64 = payload.get("image_1920")
        if image_b64 and isinstance(image_b64, (str, bytes)):
            if isinstance(image_b64, bytes):
                image_b64 = image_b64.decode()
            normalized.append({"source": f"data:image/jpeg;base64,{image_b64}"})
        return normalized

    def _build_item_payload(self, payload):
        payload = payload or {}
        title = (payload.get("title") or "").strip()
        category_id = (payload.get("category_id") or "").strip()
        if not title:
            raise UserError("MercadoLibre: falta 'title' para publicar.")
        if not category_id:
            raise UserError("MercadoLibre: falta 'category_id' para publicar.")

        price = self._to_float(payload.get("price"), 0.0)
        qty = self._to_int(payload.get("available_quantity"), 0)

        if price <= 0:
            raise UserError("MercadoLibre: el precio debe ser mayor a cero.")
        if qty < 0:
            qty = 0

        item = {
            "title": title,
            "category_id": category_id,
            "price": price,
            "currency_id": payload.get("currency_id") or "ARS",
            "available_quantity": qty,
            "buying_mode": payload.get("buying_mode") or "buy_it_now",
            "condition": payload.get("condition") or "new",
            "listing_type_id": payload.get("listing_type_id") or payload.get("listing_type") or "gold_special",
        }

        attributes = self._normalize_attributes(payload)
        if attributes:
            item["attributes"] = attributes

        pictures = self._normalize_pictures(payload)
        if pictures:
            item["pictures"] = pictures

        description = payload.get("description")
        if isinstance(description, dict):
            item["description"] = description
        elif payload.get("description_plain_text"):
            item["description"] = {"plain_text": payload.get("description_plain_text")}

        sale_terms = payload.get("sale_terms")
        if isinstance(sale_terms, list):
            item["sale_terms"] = sale_terms

        if payload.get("warranty"):
            item.setdefault("sale_terms", [])
            item["sale_terms"].append({"id": "WARRANTY_TYPE", "value_name": payload["warranty"]})

        return item

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
        _logger.info(
            "ML OAuth exchange request: grant_type=%s client_id=%s redirect_uri=%s has_code_verifier=%s code_len=%s",
            payload.get("grant_type"),
            (payload.get("client_id") or "")[:6] + "***" if payload.get("client_id") else "",
            payload.get("redirect_uri"),
            bool(payload.get("code_verifier")),
            len(payload.get("code") or ""),
        )
        data = self._request(
            "POST",
            self.BASE_AUTH_URL,
            payload=payload,
            with_auth=False,
            form_encoded=True,
        )
        elapsed_ms = (data.get("_meta") or {}).get("elapsed_ms") if isinstance(data, dict) else None
        expires_in = int(data.get("expires_in", 0) or 0)
        token_expires_at = fields.Datetime.now() + timedelta(seconds=expires_in) if expires_in else False

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
        data = self._request(
            "POST",
            self.BASE_AUTH_URL,
            payload=payload,
            with_auth=False,
            form_encoded=True,
        )
        elapsed_ms = (data.get("_meta") or {}).get("elapsed_ms") if isinstance(data, dict) else None
        expires_in = int(data.get("expires_in", 0) or 0)
        token_expires_at = fields.Datetime.now() + timedelta(seconds=expires_in) if expires_in else False

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
        item_payload = self._build_item_payload(payload or {})
        data = self._request("POST", "/items", payload=item_payload)
        return self._ok(action="publish_product", item_id=data.get("id"), raw=data)

    def update_product(self, payload):
        payload = payload or {}
        item_id = self._extract_item_id(payload)

        if payload.get("status") and not payload.get("title"):
            item_payload = {"status": payload.get("status")}
        else:
            item_payload = self._build_item_payload(payload)
            if payload.get("status"):
                item_payload["status"] = payload.get("status")

        data = self._request("PUT", f"/items/{item_id}", payload=item_payload)
        return self._ok(action="update_product", item_id=item_id, raw=data)

    def get_item(self, external_id):
        if not external_id:
            raise UserError("Falta external_id/item_id para consultar publicación.")
        data = self._request("GET", f"/items/{external_id}")
        return self._ok(action="get_item", external_id=external_id, item=data, raw=data)

    def search_categories(self, query, limit=20):
        query = (query or "").strip()
        if not query:
            raise UserError("Ingresa un texto para buscar categorías en MercadoLibre.")
        limit = min(max(self._to_int(limit, 20), 1), 50)
        data = self._request(
            "GET",
            "/sites/MLA/domain_discovery/search",
            params={"q": query, "limit": limit},
        )
        items = data if isinstance(data, list) else []
        normalized = []
        for item in items:
            if not isinstance(item, dict):
                continue
            category_id = item.get("category_id")
            if not category_id:
                continue
            normalized.append(
                {
                    "category_id": category_id,
                    "category_name": item.get("category_name") or "",
                    "domain_id": item.get("domain_id") or "",
                    "domain_name": item.get("domain_name") or "",
                }
            )
        return self._ok(action="search_categories", query=query, items=normalized, raw=data)

    def delete_product(self, payload):
        payload = payload or {}
        item_id = self._extract_item_id(payload)
        data = self._request("PUT", f"/items/{item_id}", payload={"status": "closed"})
        return self._ok(action="delete_product", item_id=item_id, raw=data)

    def update_stock(self, payload):
        payload = payload or {}
        item_id = self._extract_item_id(payload)
        qty = self._to_int(payload.get("available_quantity"), 0)
        if qty < 0:
            qty = 0
        data = self._request("PUT", f"/items/{item_id}", payload={"available_quantity": qty})
        return self._ok(action="update_stock", item_id=item_id, available_quantity=qty, raw=data)

    def update_price(self, payload):
        payload = payload or {}
        item_id = self._extract_item_id(payload)
        price = self._to_float(payload.get("price"), 0.0)
        if price <= 0:
            raise UserError("MercadoLibre: el precio debe ser mayor a cero.")
        data = self._request("PUT", f"/items/{item_id}", payload={"price": price})
        return self._ok(action="update_price", item_id=item_id, price=price, raw=data)

    def get_orders(self, params=None):
        params = params or {}
        seller_id = params.get("seller") or self.account.external_user_id
        if not seller_id:
            me = self._request("GET", "/users/me")
            seller_id = me.get("id")
        query = {
            "seller": seller_id,
            "offset": self._to_int(params.get("offset"), 0),
            "limit": min(max(self._to_int(params.get("limit"), 50), 1), 200),
        }
        if params.get("order_status"):
            query["order.status"] = params["order_status"]
        data = self._request("GET", "/orders/search", params=query)
        results = data.get("results") if isinstance(data, dict) else []
        if not isinstance(results, list):
            results = []
        return self._ok(action="get_orders", items=results, paging=data.get("paging"), raw=data)

    def get_order(self, external_id):
        if not external_id:
            raise UserError("Falta external_id para consultar la orden.")
        data = self._request("GET", f"/orders/{external_id}")
        return self._ok(action="get_order", external_id=external_id, order=data)

    def cancel_order(self, external_id):
        if not external_id:
            raise UserError("Falta external_id para cancelar la orden.")
        data = self._request("PUT", f"/orders/{external_id}", payload={"status": "cancelled"})
        return self._ok(action="cancel_order", external_id=external_id, raw=data)

    def get_messages(self, params=None):
        params = params or {}
        query = {}
        if params.get("resource"):
            query["resource"] = params["resource"]
        if params.get("tag"):
            query["tag"] = params["tag"]
        data = self._request("GET", "/messages", params=query)
        items = data.get("results") if isinstance(data, dict) else []
        if not isinstance(items, list):
            items = []
        return self._ok(action="get_messages", items=items, raw=data)

    def answer_message(self, payload):
        payload = payload or {}
        message_id = payload.get("message_id")
        text = payload.get("text") or payload.get("message")
        if not message_id:
            raise UserError("Falta message_id para responder mensaje.")
        if not text:
            raise UserError("Falta texto para responder mensaje.")
        data = self._request("POST", f"/messages/{message_id}/answers", payload={"text": text})
        return self._ok(action="answer_message", message_id=message_id, raw=data)

    def download_invoice(self, external_id):
        if not external_id:
            raise UserError("Falta external_id para descargar factura.")
        data = self._request("GET", f"/orders/{external_id}/billing_info")
        content = json.dumps(data, ensure_ascii=False).encode("utf-8")
        content_b64 = base64.b64encode(content).decode()
        return self._ok(action="download_invoice", external_id=external_id, content_b64=content_b64, raw=data)

    def upload_invoice(self, payload):
        payload = payload or {}
        order_id = payload.get("order_id") or payload.get("external_id")
        if not order_id:
            raise UserError("Falta order_id/external_id para subir comprobante.")
        body = {}
        for key in ("invoice_number", "invoice_series", "invoice_date", "invoice_url"):
            if payload.get(key):
                body[key] = payload[key]
        if not body:
            body = {"note": "invoice_uploaded_from_odoo"}
        data = self._request("POST", f"/orders/{order_id}/billing_info", payload=body)
        return self._ok(action="upload_invoice", order_id=order_id, raw=data)

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
            if payload.get("id") or payload.get("item_id") or payload.get("ml_item_id"):
                return self.update_product(payload)
            return self.publish_product(payload)
        if operation == "sync_stock":
            return self.update_stock(payload)
        if operation == "sync_prices":
            return self.update_price(payload)
        if operation == "import_orders":
            return self.get_orders(params)
        if operation == "import_order":
            return self.get_order(params.get("external_id"))
        if operation == "health_check":
            return self.health()
        if operation == "sync_messages":
            return self.get_messages(params)
        if operation == "close_product":
            return self.delete_product(payload)
        if operation == "import_item":
            external_id = (
                params.get("external_id")
                or payload.get("id")
                or payload.get("item_id")
                or payload.get("ml_item_id")
            )
            return self.get_item(external_id)
        return self._ok(action="sync", params=params)

    def webhook(self, payload):
        return self._ok(action="webhook", payload=payload or {})