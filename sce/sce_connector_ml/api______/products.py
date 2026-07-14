# -*- coding: utf-8 -*-
#
# Softwork Commerce Engine (SCE)
# MercadoLibre Products API
#

from __future__ import annotations


class ProductsAPI:
    """
    MercadoLibre Products API.

    Handles all product related operations.
    """

    def __init__(self, context):

        self.context = context

        self.http = context.http

        self.account = context.account

        self.logger = context.logger

    # ---------------------------------------------------------

    def publish(self, payload):

        """
        Publish a new item.
        """

        endpoint = "/items"

        return self.http.post(
            endpoint,
            json=payload,
        )

    # ---------------------------------------------------------

    def update(self, item_id, payload):

        endpoint = f"/items/{item_id}"

        return self.http.put(
            endpoint,
            json=payload,
        )

    # ---------------------------------------------------------

    def delete(self, item_id):

        endpoint = f"/items/{item_id}"

        return self.http.delete(
            endpoint,
        )

    # ---------------------------------------------------------

    def get(self, item_id):

        endpoint = f"/items/{item_id}"

        return self.http.get(
            endpoint,
        )

    # ---------------------------------------------------------

    def search(self):

        endpoint = "/users/me/items/search"

        return self.http.get(endpoint)