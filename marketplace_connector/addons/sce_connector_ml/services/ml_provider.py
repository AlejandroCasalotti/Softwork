"""MercadoLibre implementation owned by the connector addon.

The base implementation is inherited temporarily while the remaining ML API
helpers are extracted from the core provider module.
"""
# -*- coding: utf-8 -*-
import base64
import json

from odoo.addons.softwork_ecommerce_conector_base.services.providers.ml_provider import (
    MercadoLibreProvider as CoreMercadoLibreProvider,
)
from odoo.exceptions import UserError

from .http_transport import MercadoLibreHttpTransport
from .oauth import MercadoLibreOAuth


class MercadoLibreProvider(MercadoLibreHttpTransport, MercadoLibreOAuth, CoreMercadoLibreProvider):
    """Connector-owned entry point for MercadoLibre provider behavior."""

    def _build_item_payload(self, payload):
        payload = dict(payload or {})
        provider_data = payload.get("provider_data")
        if isinstance(provider_data, dict):
            payload.setdefault("family_name", provider_data.get("family_name") or "")
            payload.setdefault("description_html", provider_data.get("description_html") or "")
            payload.setdefault("warranty", provider_data.get("warranty") or "")
        payload.setdefault("available_quantity", payload.get("stock", 0))
        payload.setdefault("listing_type_id", payload.get("listing_type") or "gold_special")
        return super()._build_item_payload(payload)

    def health(self):
        user = self._request("GET", "/users/me")
        return self._ok(
            action="health",
            status="up",
            account_id=self.account.id,
            user_id=user.get("id") if isinstance(user, dict) else False,
        )

    def get_authenticated_user_id(self):
        if self.account.external_user_id:
            return str(self.account.external_user_id)
        result = self.health()
        user_id = result.get("user_id") if isinstance(result, dict) else False
        if not user_id:
            raise UserError("No se pudo identificar al vendedor autenticado de MercadoLibre.")
        return str(user_id)

    def list_item_ids(self, user_id, offset=0, limit=100, scroll_id=None):
        params = {"limit": limit}
        if scroll_id:
            params.update({"search_type": "scan", "scroll_id": scroll_id})
        else:
            params["offset"] = offset
        return self._request("GET", f"/users/{user_id}/items/search", params=params)

    def webhook(self, payload):
        return self._ok(action="webhook", payload=payload or {})

    def _build_item_update_payload(self, payload):
        payload = dict(payload or {})
        provider_data = payload.get("provider_data")
        if isinstance(provider_data, dict):
            payload.setdefault("description_html", provider_data.get("description_html") or "")
            payload.setdefault("warranty", provider_data.get("warranty") or "")
        payload.setdefault("available_quantity", payload.get("stock", 0))
        return super()._build_item_update_payload(payload)

    def search_categories(self, query, limit=20):
        query = (query or "").strip()
        if len(query) < 2:
            raise UserError("La búsqueda de categorías ML requiere al menos 2 caracteres.")
        limit = min(max(self._to_int(limit, 8), 1), 8)
        data = self._request(
            "GET",
            "/sites/MLA/domain_discovery/search",
            params={"q": query, "limit": limit},
        )
        items = data if isinstance(data, list) else []
        normalized = [
            {
                "category_id": item.get("category_id"),
                "category_name": item.get("category_name") or "",
                "domain_id": item.get("domain_id") or "",
                "domain_name": item.get("domain_name") or "",
            }
            for item in items
            if isinstance(item, dict) and item.get("category_id")
        ]
        return self._ok(action="search_categories", query=query, items=normalized, raw=data)

    def get_category_attributes(self, category_id):
        category_id = (category_id or "").strip()
        if not category_id:
            raise UserError("Falta category_id para consultar atributos de categoría.")
        data = self._request("GET", f"/categories/{category_id}/attributes")
        items = data if isinstance(data, list) else []
        normalized = []
        for item in items:
            if not isinstance(item, dict) or not (item.get("id") or "").strip():
                continue
            tags = item.get("tags") if isinstance(item.get("tags"), dict) else {}
            values = item.get("values") if isinstance(item.get("values"), list) else []
            normalized.append(
                {
                    "id": item["id"].strip(),
                    "name": item.get("name") or item["id"],
                    "value_type": item.get("value_type") or "string",
                    "required": bool(tags.get("required")),
                    "allow_variations": bool(tags.get("allow_variations")),
                    "values": [
                        {"id": value.get("id"), "name": value.get("name")}
                        for value in values
                        if isinstance(value, dict) and (value.get("id") is not None or value.get("name") is not None)
                    ],
                }
            )
        return self._ok(action="get_category_attributes", category_id=category_id, items=normalized, raw=data)

    def get_category_required_fields(self, category_id):
        response = self.get_category_attributes(category_id)
        attributes = response.get("items") if isinstance(response, dict) else []
        required = [attribute for attribute in attributes if attribute.get("required")]
        return self._ok(
            action="get_category_required_fields",
            category_id=category_id,
            items=required,
            total_required=len(required),
            raw=response.get("raw") if isinstance(response, dict) else {},
        )

    def get_listing_prices(self, category_id, price, listing_type_id):
        category_id = (category_id or "").strip()
        listing_type_id = (listing_type_id or "").strip()
        price = self._to_float(price, 0.0)
        if not category_id or not listing_type_id or price <= 0:
            raise UserError("Faltan categoría, tipo de publicación o precio para consultar costos ML.")

        params = {
            "category_id": category_id,
            "price": price,
            "listing_type_id": listing_type_id,
        }
        data = self._request("GET", "/sites/MLA/listing_prices", params=params)
        items = data if isinstance(data, list) else []
        if isinstance(data, dict):
            items = next(
                (
                    value
                    for key in ("items", "results", "prices", "listing_prices")
                    if isinstance((value := data.get(key)), list)
                ),
                [],
            )
        items = [item for item in items if isinstance(item, dict)]
        matching = [item for item in items if item.get("listing_type_id") == listing_type_id]
        return self._ok(
            action="get_listing_prices",
            items=matching or items,
            raw=data,
        )

    def publish_product(self, payload):
        item_payload = self._build_item_payload(payload or {})
        try:
            data = self._request("POST", "/items", payload=item_payload)
        except UserError as error:
            message = str(error)
            if "body.invalid_fields" not in message or "[title]" not in message:
                raise
            item_payload.pop("title", None)
            data = self._request("POST", "/items", payload=item_payload)
            return self._ok(
                action="publish_product",
                item_id=data.get("id"),
                catalog_managed=True,
                raw=data,
            )
        return self._ok(action="publish_product", item_id=data.get("id"), raw=data)

    def update_product(self, payload):
        payload = payload or {}
        item_id = self._extract_item_id(payload)
        if payload.get("status") and not payload.get("title"):
            item_payload = {"status": payload["status"]}
        else:
            item_payload = self._build_item_update_payload(payload)
            if payload.get("status"):
                item_payload["status"] = payload["status"]
        data = self._request("PUT", f"/items/{item_id}", payload=item_payload)
        return self._ok(action="update_product", item_id=item_id, raw=data)

    def delete_product(self, payload):
        item_id = self._extract_item_id(payload or {})
        data = self._request("PUT", f"/items/{item_id}", payload={"status": "closed"})
        return self._ok(action="delete_product", item_id=item_id, raw=data)

    def update_stock(self, payload):
        payload = payload or {}
        item_id = self._extract_item_id(payload)
        quantity = max(0, self._to_int(payload.get("available_quantity"), 0))
        variation_id = payload.get("variation_id") or payload.get("external_variant_id")
        endpoint = f"/items/{item_id}/variations/{variation_id}" if variation_id else f"/items/{item_id}"
        data = self._request(
            "PUT",
            endpoint,
            payload={"available_quantity": quantity},
        )
        return self._ok(
            action="update_stock",
            item_id=item_id,
            variation_id=str(variation_id) if variation_id else False,
            available_quantity=quantity,
            raw=data,
        )

    def update_price(self, payload):
        payload = payload or {}
        item_id = self._extract_item_id(payload)
        price = self._to_float(payload.get("price"), 0.0)
        if price <= 0:
            raise UserError("MercadoLibre: el precio debe ser mayor a cero.")
        data = self._request("PUT", f"/items/{item_id}", payload={"price": price})
        return self._ok(action="update_price", item_id=item_id, price=price, raw=data)

    def get_item(self, external_id, params=None):
        external_id = str(external_id or "").strip()
        if not external_id:
            raise UserError("Falta external_id/item_id para consultar publicación.")
        data = self._request("GET", f"/items/{external_id}", params=params)
        return self._ok(action="get_item", external_id=external_id, item=data, raw=data)

    def get_order(self, external_id):
        external_id = str(external_id or "").strip()
        if not external_id:
            raise UserError("Falta el ID externo de la orden MercadoLibre.")
        data = self._request("GET", f"/orders/{external_id}")
        return self._ok(action="get_order", external_id=external_id, order=data)

    def get_orders(self, params=None):
        params = params or {}
        seller_id = params.get("seller") or self.account.external_user_id
        if not seller_id:
            seller_id = self._request("GET", "/users/me").get("id")
        query = {
            "seller": seller_id,
            "offset": self._to_int(params.get("offset"), 0),
            "limit": min(max(self._to_int(params.get("limit"), 50), 1), 200),
        }
        if params.get("order_status"):
            query["order.status"] = params["order_status"]
        data = self._request("GET", "/orders/search", params=query)
        items = data.get("results") if isinstance(data, dict) else []
        return self._ok(
            action="get_orders",
            items=items if isinstance(items, list) else [],
            paging=data.get("paging") if isinstance(data, dict) else {},
            raw=data,
        )

    def cancel_order(self, external_id):
        external_id = str(external_id or "").strip()
        if not external_id:
            raise UserError("Falta el ID externo de la orden MercadoLibre.")
        data = self._request(
            "PUT",
            f"/orders/{external_id}",
            payload={"status": "cancelled"},
        )
        return self._ok(action="cancel_order", external_id=external_id, raw=data)

    def get_messages(self, params=None):
        params = params or {}
        query = {key: params[key] for key in ("resource", "tag") if params.get(key)}
        data = self._request("GET", "/messages", params=query)
        items = data.get("results") if isinstance(data, dict) else []
        return self._ok(
            action="get_messages",
            items=items if isinstance(items, list) else [],
            raw=data,
        )

    def answer_message(self, payload):
        payload = payload or {}
        message_id = payload.get("message_id")
        text = payload.get("text") or payload.get("message")
        if not message_id:
            raise UserError("Falta message_id para responder mensaje.")
        if not text:
            raise UserError("Falta texto para responder mensaje.")
        data = self._request(
            "POST",
            f"/messages/{message_id}/answers",
            payload={"text": text},
        )
        return self._ok(action="answer_message", message_id=message_id, raw=data)

    def download_invoice(self, external_id):
        external_id = str(external_id or "").strip()
        if not external_id:
            raise UserError("Falta external_id para descargar factura.")
        data = self._request("GET", f"/orders/{external_id}/billing_info")
        content_b64 = base64.b64encode(json.dumps(data, ensure_ascii=False).encode("utf-8")).decode()
        return self._ok(
            action="download_invoice",
            external_id=external_id,
            content_b64=content_b64,
            raw=data,
        )

    def upload_invoice(self, payload):
        payload = payload or {}
        order_id = payload.get("order_id") or payload.get("external_id")
        if not order_id:
            raise UserError("Falta order_id/external_id para subir comprobante.")
        body = {key: payload[key] for key in ("invoice_number", "invoice_series", "invoice_date", "invoice_url") if payload.get(key)}
        data = self._request(
            "POST",
            f"/orders/{order_id}/billing_info",
            payload=body or {"note": "invoice_uploaded_from_odoo"},
        )
        return self._ok(action="upload_invoice", order_id=order_id, raw=data)

    def sync(self, params=None):
        params = params or {}
        operation = params.get("operation", "sync_products")
        payload = params.get("payload", {})
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except (TypeError, ValueError):
                payload = {"raw": payload}

        operations = {
            "sync_products": lambda: self.update_product(payload) if payload.get("id") or payload.get("item_id") or payload.get("ml_item_id") else self.publish_product(payload),
            "sync_stock": lambda: self.update_stock(payload),
            "sync_prices": lambda: self.update_price(payload),
            "import_orders": lambda: self.get_orders(params),
            "import_order": lambda: self.get_order(params.get("external_id")),
            "health_check": self.health,
            "sync_messages": lambda: self.get_messages(params),
            "close_product": lambda: self.delete_product(payload),
            "import_item": lambda: self.get_item(
                params.get("external_id")
                or payload.get("id")
                or payload.get("item_id")
                or payload.get("ml_item_id")
            ),
        }
        operation_handler = operations.get(operation)
        if operation_handler:
            return operation_handler()
        return self._ok(action="sync", params=params)
