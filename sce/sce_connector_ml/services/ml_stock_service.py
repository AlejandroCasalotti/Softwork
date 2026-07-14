# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Mercado Libre Stock Service
"""

from __future__ import annotations

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class MLStockService(models.AbstractModel):
    """
    Mercado Libre Stock Service.
    """

    _name = "ml.stock.service"
    _description = "Mercado Libre Stock Service"

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _client(self):
        return self.env["ml.api.client"]

    # -------------------------------------------------------------------------
    # Get Stock
    # -------------------------------------------------------------------------

    def get(
        self,
        account,
        item_id,
    ):
        """
        Returns current stock information.
        """

        item = self._client().get(
            account,
            f"/items/{item_id}",
        )

        return {

            "available_quantity": item.get(
                "available_quantity",
                0,
            ),

            "sold_quantity": item.get(
                "sold_quantity",
                0,
            ),

            "status": item.get(
                "status",
            ),

        }

    # -------------------------------------------------------------------------
    # Update Stock
    # -------------------------------------------------------------------------

    def update(
        self,
        account,
        item_id,
        quantity,
    ):
        """
        Updates available quantity.
        """

        payload = {

            "available_quantity": quantity,

        }

        result = self._client().put(

            account,

            f"/items/{item_id}",

            json=payload,

        )

        _logger.info(

            "Stock updated (%s -> %s)",

            item_id,

            quantity,

        )

        return result

    # -------------------------------------------------------------------------
    # Increase
    # -------------------------------------------------------------------------

    def increase(
        self,
        account,
        item_id,
        quantity,
    ):
        """
        Increases available stock.
        """

        stock = self.get(
            account,
            item_id,
        )

        return self.update(

            account,

            item_id,

            stock["available_quantity"] + quantity,

        )

    # -------------------------------------------------------------------------
    # Decrease
    # -------------------------------------------------------------------------

    def decrease(
        self,
        account,
        item_id,
        quantity,
    ):
        """
        Decreases available stock.
        """

        stock = self.get(
            account,
            item_id,
        )

        new_qty = max(
            0,
            stock["available_quantity"] - quantity,
        )

        return self.update(

            account,

            item_id,

            new_qty,

        )

    # -------------------------------------------------------------------------
    # Synchronize Product
    # -------------------------------------------------------------------------

    def synchronize_product(
        self,
        account,
        product,
    ):
        """
        Synchronizes one Odoo product.
        """

        if not product.ml_item_id:

            return False

        quantity = int(
            product.qty_available
        )

        return self.update(

            account,

            product.ml_item_id,

            quantity,

        )

    # -------------------------------------------------------------------------
    # Synchronize Multiple Products
    # -------------------------------------------------------------------------

    def synchronize(
        self,
        account,
        products,
    ):
        """
        Synchronizes multiple products.
        """

        results = []

        for product in products:

            try:

                results.append(

                    self.synchronize_product(
                        account,
                        product,
                    )

                )

            except Exception as error:

                _logger.exception(error)

        return results

    # -------------------------------------------------------------------------
    # Validate Stock
    # -------------------------------------------------------------------------

    def validate(
        self,
        quantity,
    ):
        """
        Validates quantity.
        """

        return quantity >= 0

    # -------------------------------------------------------------------------
    # Dashboard
    # -------------------------------------------------------------------------

    def dashboard(
        self,
        account,
        item_id,
    ):
        """
        Dashboard information.
        """

        stock = self.get(
            account,
            item_id,
        )

        return {

            "available": stock.get(
                "available_quantity",
            ),

            "sold": stock.get(
                "sold_quantity",
            ),

            "status": stock.get(
                "status",
            ),

        }

    # -------------------------------------------------------------------------
    # Health
    # -------------------------------------------------------------------------

    def health(
        self,
        account,
    ):
        """
        Service health.
        """

        try:

            self.env[
                "ml.user.service"
            ].me(
                account,
            )

            return {

                "service": "stock",

                "status": "ok",

            }

        except Exception as error:

            return {

                "service": "stock",

                "status": "error",

                "message": str(error),

            }