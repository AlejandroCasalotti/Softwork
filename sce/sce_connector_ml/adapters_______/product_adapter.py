# -*- coding: utf-8 -*-
#
# Softwork Commerce Engine (SCE)
# MercadoLibre Product Adapter
#

from __future__ import annotations

from odoo import models


class ProductAdapter(models.AbstractModel):
    """
    Converts Odoo products into MercadoLibre payloads.
    """

    _name = "sce.ml.product.adapter"
    _description = "MercadoLibre Product Adapter"

    # ---------------------------------------------------------
    # Export
    # ---------------------------------------------------------

    def to_ml(self, product):

        payload = {

            "title": product.name,

            "category_id": product.ml_category_id,

            "price": float(product.list_price),

            "currency_id": "ARS",

            "available_quantity": int(product.qty_available),

            "buying_mode": "buy_it_now",

            "condition": "new",

            "listing_type_id": product.ml_listing_type,

            "sale_terms": [],

            "pictures": [],

            "attributes": [],

        }

        return payload

    # ---------------------------------------------------------
    # Import
    # ---------------------------------------------------------

    def from_ml(self, data, product):

        values = {

            "name": data.get("title"),

            "list_price": data.get("price"),

        }

        product.write(values)

        return product