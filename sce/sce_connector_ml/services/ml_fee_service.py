# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Mercado Libre Fee Service

Handles listing types, fees, sale commissions and
shipping cost estimations.
"""

from __future__ import annotations

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class MLFeeService(models.AbstractModel):
    """
    Mercado Libre Fee Service.
    """

    _name = "ml.fee.service"
    _description = "Mercado Libre Fee Service"

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _client(self):
        return self.env["ml.api.client"]

    # -------------------------------------------------------------------------
    # Listing Types
    # -------------------------------------------------------------------------

    def listing_types(
        self,
        account,
        site_id=None,
    ):
        """
        Returns available listing types.
        """

        site = site_id or account.site_id.code

        return self._client().get(
            account,
            f"/sites/{site}/listing_types",
        )

    # -------------------------------------------------------------------------
    # Listing Type
    # -------------------------------------------------------------------------

    def listing_type(
        self,
        account,
        listing_type_id,
    ):
        """
        Returns listing type information.
        """

        return self._client().get(
            account,
            f"/listing_types/{listing_type_id}",
        )

    # -------------------------------------------------------------------------
    # Sale Fee
    # -------------------------------------------------------------------------

    def sale_fee(
        self,
        account,
        category_id,
        price,
        listing_type_id,
        currency_id="ARS",
    ):
        """
        Returns estimated Mercado Libre fee.
        """

        endpoint = (
            "/sites/%s/listing_prices"
            % account.site_id.code
        )

        params = {
            "price": price,
            "listing_type_id": listing_type_id,
            "category_id": category_id,
            "currency_id": currency_id,
        }

        result = self._client().get(
            account,
            endpoint,
            params=params,
        )

        if isinstance(result, list) and result:
            return result[0]

        return result

    # -------------------------------------------------------------------------
    # Commission
    # -------------------------------------------------------------------------

    def commission(
        self,
        account,
        category_id,
        price,
        listing_type_id,
    ):
        """
        Returns commission amount.
        """

        fee = self.sale_fee(
            account,
            category_id,
            price,
            listing_type_id,
        )

        return fee.get(
            "sale_fee_amount",
            0.0,
        )

    # -------------------------------------------------------------------------
    # Percentage
    # -------------------------------------------------------------------------

    def percentage(
        self,
        account,
        category_id,
        price,
        listing_type_id,
    ):
        """
        Returns fee percentage.
        """

        fee = self.sale_fee(
            account,
            category_id,
            price,
            listing_type_id,
        )

        return fee.get(
            "sale_fee_details",
            {},
        ).get(
            "percentage_fee",
            0.0,
        )

    # -------------------------------------------------------------------------
    # Fixed Fee
    # -------------------------------------------------------------------------

    def fixed_fee(
        self,
        account,
        category_id,
        price,
        listing_type_id,
    ):
        """
        Returns fixed fee.
        """

        fee = self.sale_fee(
            account,
            category_id,
            price,
            listing_type_id,
        )

        return fee.get(
            "sale_fee_details",
            {},
        ).get(
            "fixed_fee",
            0.0,
        )

    # -------------------------------------------------------------------------
    # Shipping Cost
    # -------------------------------------------------------------------------

    def shipping_cost(
        self,
        account,
        item_id,
        zip_code=None,
    ):
        """
        Returns estimated shipping cost.
        """

        endpoint = (
            f"/items/{item_id}/shipping_options"
        )

        params = {}

        if zip_code:
            params["zip_code"] = zip_code

        return self._client().get(
            account,
            endpoint,
            params=params,
        )

    # -------------------------------------------------------------------------
    # Free Shipping
    # -------------------------------------------------------------------------

    def free_shipping(
        self,
        account,
        category_id,
    ):
        """
        Returns free shipping rules.
        """

        endpoint = (
            f"/categories/{category_id}/shipping_preferences"
        )

        return self._client().get(
            account,
            endpoint,
        )

    # -------------------------------------------------------------------------
    # Profit Estimation
    # -------------------------------------------------------------------------

    def estimate_profit(
        self,
        account,
        category_id,
        listing_type_id,
        sale_price,
        cost_price,
    ):
        """
        Calculates estimated profit.
        """

        commission = self.commission(
            account,
            category_id,
            sale_price,
            listing_type_id,
        )

        profit = (
            sale_price
            - commission
            - cost_price
        )

        return {

            "sale_price": sale_price,

            "cost_price": cost_price,

            "commission": commission,

            "profit": profit,

            "margin": (
                (profit / sale_price) * 100
                if sale_price
                else 0.0
            ),

        }

    # -------------------------------------------------------------------------
    # Validate Listing Type
    # -------------------------------------------------------------------------

    def validate_listing_type(
        self,
        account,
        listing_type_id,
    ):
        """
        Validates listing type.
        """

        try:

            return bool(

                self.listing_type(
                    account,
                    listing_type_id,
                )

            )

        except Exception:

            _logger.exception(
                "Invalid listing type."
            )

            return False