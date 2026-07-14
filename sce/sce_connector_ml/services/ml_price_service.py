# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Mercado Libre Price Service
"""

from __future__ import annotations

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class MLPriceService(models.AbstractModel):

    _name = "ml.price.service"
    _description = "Mercado Libre Price Service"

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _client(self):
        return self.env["ml.api.client"]

    # -------------------------------------------------------------------------
    # Get Price
    # -------------------------------------------------------------------------

    def get(
        self,
        account,
        item_id,
    ):

        item = self._client().get(
            account,
            f"/items/{item_id}",
        )

        return {

            "price": item.get("price"),

            "currency_id": item.get("currency_id"),

            "available_quantity": item.get(
                "available_quantity"
            ),

            "status": item.get("status"),

        }

    # -------------------------------------------------------------------------
    # Update Price
    # -------------------------------------------------------------------------

    def update(
        self,
        account,
        item_id,
        price,
    ):

        payload = {

            "price": float(price),

        }

        result = self._client().put(

            account,

            f"/items/{item_id}",

            json=payload,

        )

        _logger.info(

            "Mercado Libre price updated (%s -> %s)",

            item_id,

            price,

        )

        return result

    # -------------------------------------------------------------------------
    # Bulk Update
    # -------------------------------------------------------------------------

    def bulk_update(
        self,
        account,
        items,
    ):

        results = []

        for item in items:

            try:

                results.append(

                    self.update(

                        account,

                        item["item_id"],

                        item["price"],

                    )

                )

            except Exception as error:

                _logger.exception(error)

        return results

    # -------------------------------------------------------------------------
    # Suggested Price
    # -------------------------------------------------------------------------

    def suggested_price(
        self,
        account,
        item_id,
    ):

        item = self.get(
            account,
            item_id,
        )

        return item.get("price")

    # -------------------------------------------------------------------------
    # Calculate Net Price
    # -------------------------------------------------------------------------

    def calculate_net_price(
        self,
        account,
        item_id,
    ):

        item = self.get(
            account,
            item_id,
        )

        fees = self.env[
            "ml.fee.service"
        ].calculate_fee(

            account,

            item["price"],

            item_id=item_id,

        )

        return {

            "gross_price": item["price"],

            "fee": fees.get("fee", 0),

            "shipping": fees.get(
                "shipping_cost",
                0,
            ),

            "net_price":

                item["price"]

                - fees.get("fee", 0)

                - fees.get("shipping_cost", 0),

        }

    # -------------------------------------------------------------------------
    # Currency
    # -------------------------------------------------------------------------

    def currency(
        self,
        account,
        item_id,
    ):

        item = self.get(
            account,
            item_id,
        )

        return self.env[
            "ml.currency.service"
        ].get_currency(

            account,

            item["currency_id"],

        )

    # -------------------------------------------------------------------------
    # Simulate Price
    # -------------------------------------------------------------------------

    def simulate(
        self,
        account,
        item_id,
        new_price,
    ):

        fees = self.env[
            "ml.fee.service"
        ].calculate_fee(

            account,

            new_price,

            item_id=item_id,

        )

        return {

            "price": new_price,

            "fee": fees.get("fee"),

            "shipping": fees.get(
                "shipping_cost",
                0,
            ),

            "estimated_net":

                new_price

                - fees.get("fee", 0)

                - fees.get(
                    "shipping_cost",
                    0,
                ),

        }

    # -------------------------------------------------------------------------
    # Synchronize
    # -------------------------------------------------------------------------

    def synchronize(
        self,
        account,
        product,
    ):

        if not product.ml_item_id:

            return False

        return self.update(

            account,

            product.ml_item_id,

            product.list_price,

        )

    # -------------------------------------------------------------------------
    # Dashboard
    # -------------------------------------------------------------------------

    def dashboard(
        self,
        account,
        item_id,
    ):

        info = self.get(
            account,
            item_id,
        )

        net = self.calculate_net_price(
            account,
            item_id,
        )

        return {

            "price": info["price"],

            "currency": info["currency_id"],

            "net": net["net_price"],

            "fee": net["fee"],

            "shipping": net["shipping"],

        }

    # -------------------------------------------------------------------------
    # Health
    # -------------------------------------------------------------------------

    def health(
        self,
        account,
    ):

        try:

            self.env[
                "ml.user.service"
            ].me(account)

            return {

                "service": "price",

                "status": "ok",

            }

        except Exception as error:

            return {

                "service": "price",

                "status": "error",

                "message": str(error),

            }