# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Mercado Libre API Client
"""

from __future__ import annotations

from typing import Any

from odoo.addons.sce_base.services.http.auth import AuthStrategy
from odoo.addons.sce_base.services.http.client import HttpClient
from odoo.addons.sce_base.services.http.response import HttpResponse


class MLEndpoints:
    """
    Mercado Libre API endpoints.
    """

    OAUTH_TOKEN = "/oauth/token"

    USERS = "/users"

    ITEMS = "/items"

    ORDERS = "/orders"

    SHIPMENTS = "/shipments"

    CATEGORIES = "/categories"

    SITES = "/sites"

    CURRENCIES = "/currencies"

    QUESTIONS = "/questions"

    VISITS = "/visits"

    ORDERS_SEARCH = "/orders/search"


class MLApiClient:
    """
    Mercado Libre API Client.
    """

    DEFAULT_TIMEOUT = 30

    def __init__(
        self,
        *,
        base_url: str,
        auth: AuthStrategy | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:

        self._client = HttpClient(
            base_url=base_url,
            auth=auth,
            timeout=timeout,
        )

    # ==========================================================
    # Generic HTTP
    # ==========================================================

    def get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:

        response = self._client.get(
            path,
            params=params,
            headers=headers,
        )

        return self._body(response)

    def post(
        self,
        path: str,
        *,
        json: Any = None,
        data: Any = None,
        headers: dict[str, str] | None = None,
    ) -> Any:

        response = self._client.post(
            path,
            json=json,
            data=data,
            headers=headers,
        )

        return self._body(response)

    def put(
        self,
        path: str,
        *,
        json: Any = None,
        data: Any = None,
        headers: dict[str, str] | None = None,
    ) -> Any:

        response = self._client.put(
            path,
            json=json,
            data=data,
            headers=headers,
        )

        return self._body(response)

    def patch(
        self,
        path: str,
        *,
        json: Any = None,
        data: Any = None,
        headers: dict[str, str] | None = None,
    ) -> Any:

        response = self._client.patch(
            path,
            json=json,
            data=data,
            headers=headers,
        )

        return self._body(response)

    def delete(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> Any:

        response = self._client.delete(
            path,
            headers=headers,
        )

        return self._body(response)

    # ==========================================================
    # OAuth
    # ==========================================================

    def exchange_token(
        self,
        *,
        client_id: str,
        client_secret: str,
        code: str,
        redirect_uri: str,
    ) -> dict[str, Any]:

        payload = {
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        }

        return self.post(
            MLEndpoints.OAUTH_TOKEN,
            json=payload,
        )

    def refresh_token(
        self,
        *,
        client_id: str,
        client_secret: str,
        refresh_token: str,
    ) -> dict[str, Any]:

        payload = {
            "grant_type": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
        }

        return self.post(
            MLEndpoints.OAUTH_TOKEN,
            json=payload,
        )

    # ==========================================================
    # Users
    # ==========================================================

    def get_user(
        self,
        user_id: str,
    ) -> dict[str, Any]:

        return self.get(
            f"{MLEndpoints.USERS}/{user_id}"
        )

    def get_me(self) -> dict[str, Any]:

        return self.get(
            f"{MLEndpoints.USERS}/me"
        )

    # ==========================================================
    # Sites
    # ==========================================================

    def get_sites(self) -> list[dict[str, Any]]:

        return self.get(
            MLEndpoints.SITES
        )

    def get_site(
        self,
        site_id: str,
    ) -> dict[str, Any]:

        return self.get(
            f"{MLEndpoints.SITES}/{site_id}"
        )

    # ==========================================================
    # Categories
    # ==========================================================

    def get_categories(
        self,
        site_id: str,
    ) -> list[dict[str, Any]]:

        return self.get(
            f"{MLEndpoints.SITES}/{site_id}/categories"
        )

    def get_category(
        self,
        category_id: str,
    ) -> dict[str, Any]:

        return self.get(
            f"{MLEndpoints.CATEGORIES}/{category_id}"
        )

    # ==========================================================
    # Internal
    # ==========================================================

    @staticmethod
    def _body(
        response: HttpResponse,
    ) -> Any:
        """
        Returns only the response body.
        """

        return response.body

            # ==========================================================
    # Items
    # ==========================================================

    def get_item(
        self,
        item_id: str,
    ) -> dict[str, Any]:

        return self.get(
            f"{MLEndpoints.ITEMS}/{item_id}"
        )

    def create_item(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:

        return self.post(
            MLEndpoints.ITEMS,
            json=payload,
        )

    def update_item(
        self,
        item_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:

        return self.put(
            f"{MLEndpoints.ITEMS}/{item_id}",
            json=payload,
        )

    def close_item(
        self,
        item_id: str,
    ) -> dict[str, Any]:

        return self.put(
            f"{MLEndpoints.ITEMS}/{item_id}",
            json={
                "status": "closed",
            },
        )

    def pause_item(
        self,
        item_id: str,
    ) -> dict[str, Any]:

        return self.put(
            f"{MLEndpoints.ITEMS}/{item_id}",
            json={
                "status": "paused",
            },
        )

    def activate_item(
        self,
        item_id: str,
    ) -> dict[str, Any]:

        return self.put(
            f"{MLEndpoints.ITEMS}/{item_id}",
            json={
                "status": "active",
            },
        )

    # ==========================================================
    # Price
    # ==========================================================

    def update_price(
        self,
        item_id: str,
        price: float,
    ) -> dict[str, Any]:

        return self.put(
            f"{MLEndpoints.ITEMS}/{item_id}",
            json={
                "price": price,
            },
        )

    # ==========================================================
    # Stock
    # ==========================================================

    def update_stock(
        self,
        item_id: str,
        quantity: int,
    ) -> dict[str, Any]:

        return self.put(
            f"{MLEndpoints.ITEMS}/{item_id}",
            json={
                "available_quantity": quantity,
            },
        )

    # ==========================================================
    # Description
    # ==========================================================

    def get_description(
        self,
        item_id: str,
    ) -> dict[str, Any]:

        return self.get(
            f"{MLEndpoints.ITEMS}/{item_id}/description"
        )

    def update_description(
        self,
        item_id: str,
        text: str,
    ) -> dict[str, Any]:

        return self.put(
            f"{MLEndpoints.ITEMS}/{item_id}/description",
            json={
                "plain_text": text,
            },
        )

    # ==========================================================
    # Pictures
    # ==========================================================

    def upload_picture(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:

        return self.post(
            "/pictures",
            json=payload,
        )

    # ==========================================================
    # Visits
    # ==========================================================

    def get_visits(
        self,
        item_id: str,
    ) -> dict[str, Any]:

        return self.get(
            f"{MLEndpoints.ITEMS}/{item_id}/visits"
        )

    # ==========================================================
    # Questions
    # ==========================================================

    def get_questions(
        self,
        item_id: str,
    ) -> list[dict[str, Any]]:

        return self.get(
            MLEndpoints.QUESTIONS,
            params={
                "item": item_id,
            },
        )

    def answer_question(
        self,
        question_id: str,
        text: str,
    ) -> dict[str, Any]:

        return self.post(
            f"{MLEndpoints.QUESTIONS}/{question_id}/answers",
            json={
                "text": text,
            },
        )

    # ==========================================================
    # Search
    # ==========================================================

    def search_items(
        self,
        seller_id: str,
        *,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:

        params = {
            "seller_id": seller_id,
            "offset": offset,
            "limit": limit,
        }

        if status:
            params["status"] = status

        return self.get(
            MLEndpoints.ITEMS,
            params=params,
        )

    # ==========================================================
    # Currencies
    # ==========================================================

    def get_currencies(
        self,
    ) -> list[dict[str, Any]]:

        return self.get(
            MLEndpoints.CURRENCIES,
        )

    def get_currency(
        self,
        currency_id: str,
    ) -> dict[str, Any]:

        return self.get(
            f"{MLEndpoints.CURRENCIES}/{currency_id}"
        )

            # ==========================================================
    # Orders
    # ==========================================================

    def get_order(
        self,
        order_id: str | int,
    ) -> dict[str, Any]:

        return self.get(
            f"{MLEndpoints.ORDERS}/{order_id}"
        )

    def search_orders(
        self,
        *,
        seller_id: str | int | None = None,
        order_status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:

        params = {
            "offset": offset,
            "limit": limit,
        }

        if seller_id is not None:
            params["seller"] = seller_id

        if order_status:
            params["order.status"] = order_status

        return self.get(
            MLEndpoints.ORDERS_SEARCH,
            params=params,
        )

    def search_recent_orders(
        self,
        seller_id: str | int,
    ) -> dict[str, Any]:

        return self.search_orders(
            seller_id=seller_id,
            offset=0,
            limit=50,
        )

    # ==========================================================
    # Shipments
    # ==========================================================

    def get_shipment(
        self,
        shipment_id: str | int,
    ) -> dict[str, Any]:

        return self.get(
            f"{MLEndpoints.SHIPMENTS}/{shipment_id}"
        )

    def get_shipment_items(
        self,
        shipment_id: str | int,
    ) -> dict[str, Any]:

        return self.get(
            f"{MLEndpoints.SHIPMENTS}/{shipment_id}/items"
        )

    def get_shipment_history(
        self,
        shipment_id: str | int,
    ) -> dict[str, Any]:

        return self.get(
            f"{MLEndpoints.SHIPMENTS}/{shipment_id}/history"
        )

    # ==========================================================
    # Generic Resources
    # ==========================================================

    def exists(
        self,
        path: str,
    ) -> bool:

        try:
            self.get(path)
            return True

        except Exception:
            return False

    # ==========================================================
    # Raw HTTP
    # ==========================================================

    def get_raw(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> HttpResponse:

        return self._client.get(
            path,
            params=params,
            headers=headers,
        )

    def post_raw(
        self,
        path: str,
        *,
        json: Any = None,
        data: Any = None,
        headers: dict[str, str] | None = None,
    ) -> HttpResponse:

        return self._client.post(
            path,
            json=json,
            data=data,
            headers=headers,
        )

    def put_raw(
        self,
        path: str,
        *,
        json: Any = None,
        data: Any = None,
        headers: dict[str, str] | None = None,
    ) -> HttpResponse:

        return self._client.put(
            path,
            json=json,
            data=data,
            headers=headers,
        )

    def patch_raw(
        self,
        path: str,
        *,
        json: Any = None,
        data: Any = None,
        headers: dict[str, str] | None = None,
    ) -> HttpResponse:

        return self._client.patch(
            path,
            json=json,
            data=data,
            headers=headers,
        )

    def delete_raw(
        self,
        path: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> HttpResponse:

        return self._client.delete(
            path,
            headers=headers,
        )

    # ==========================================================
    # Properties
    # ==========================================================

    @property
    def http_client(self) -> HttpClient:
        """
        Returns the underlying HTTP client.
        """

        return self._client