# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Mercado Libre Currency Service

Provides access to Mercado Libre currencies,
exchange rates and currency validation.
"""

from __future__ import annotations

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class MLCurrencyService(models.AbstractModel):
    """
    Mercado Libre Currency Service.
    """

    _name = "ml.currency.service"
    _description = "Mercado Libre Currency Service"

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _client(self):
        return self.env["ml.api.client"]

    # -------------------------------------------------------------------------
    # Currencies
    # -------------------------------------------------------------------------

    def currencies(
        self,
        account,
    ):
        """
        Returns all Mercado Libre currencies.
        """

        return self._client().get(
            account,
            "/currencies",
        )

    # -------------------------------------------------------------------------
    # Currency
    # -------------------------------------------------------------------------

    def currency(
        self,
        account,
        currency_id,
    ):
        """
        Returns information about one currency.
        """

        return self._client().get(
            account,
            f"/currencies/{currency_id}",
        )

    # -------------------------------------------------------------------------
    # Validate
    # -------------------------------------------------------------------------

    def exists(
        self,
        account,
        currency_id,
    ):
        """
        Checks if currency exists.
        """

        try:

            return bool(
                self.currency(
                    account,
                    currency_id,
                )
            )

        except Exception:

            return False

    # -------------------------------------------------------------------------
    # Decimal Places
    # -------------------------------------------------------------------------

    def decimals(
        self,
        account,
        currency_id,
    ):
        """
        Returns decimal places.
        """

        currency = self.currency(
            account,
            currency_id,
        )

        return currency.get(
            "decimal_places",
            2,
        )

    # -------------------------------------------------------------------------
    # Symbol
    # -------------------------------------------------------------------------

    def symbol(
        self,
        account,
        currency_id,
    ):
        """
        Returns currency symbol.
        """

        currency = self.currency(
            account,
            currency_id,
        )

        return currency.get(
            "symbol",
            "",
        )

    # -------------------------------------------------------------------------
    # Description
    # -------------------------------------------------------------------------

    def description(
        self,
        account,
        currency_id,
    ):
        """
        Returns currency description.
        """

        currency = self.currency(
            account,
            currency_id,
        )

        return currency.get(
            "description",
            "",
        )

    # -------------------------------------------------------------------------
    # Exchange Rate
    # -------------------------------------------------------------------------

    def exchange_rate(
        self,
        account,
        from_currency,
        to_currency,
    ):
        """
        Returns exchange rate between currencies.

        Mercado Libre usually publishes rates
        relative to the site currency.
        """

        if from_currency == to_currency:
            return 1.0

        endpoint = (
            "/currency_conversions/search"
        )

        result = self._client().get(
            account,
            endpoint,
            params={
                "from": from_currency,
                "to": to_currency,
            },
        )

        if isinstance(result, dict):
            return result.get(
                "ratio",
                1.0,
            )

        return 1.0

    # -------------------------------------------------------------------------
    # Convert Amount
    # -------------------------------------------------------------------------

    def convert(
        self,
        account,
        amount,
        from_currency,
        to_currency,
    ):
        """
        Converts an amount.
        """

        rate = self.exchange_rate(
            account,
            from_currency,
            to_currency,
        )

        return round(
            amount * rate,
            2,
        )

    # -------------------------------------------------------------------------
    # Site Currency
    # -------------------------------------------------------------------------

    def site_currency(
        self,
        account,
    ):
        """
        Returns marketplace default currency.
        """

        site = self._client().get(
            account,
            f"/sites/{account.site_id.code}",
        )

        return site.get(
            "default_currency_id",
            "ARS",
        )

    # -------------------------------------------------------------------------
    # Is Default Currency
    # -------------------------------------------------------------------------

    def is_default(
        self,
        account,
        currency_id,
    ):
        """
        Checks whether the currency is
        the site's default currency.
        """

        return (
            currency_id ==
            self.site_currency(account)
        )

    # -------------------------------------------------------------------------
    # Format Amount
    # -------------------------------------------------------------------------

    def format_amount(
        self,
        account,
        amount,
        currency_id,
    ):
        """
        Returns formatted amount.
        """

        symbol = self.symbol(
            account,
            currency_id,
        )

        decimals = self.decimals(
            account,
            currency_id,
        )

        return (
            f"{symbol} "
            f"{amount:,.{decimals}f}"
        )

    # -------------------------------------------------------------------------
    # Supported Currency
    # -------------------------------------------------------------------------

    def supported(
        self,
        account,
        currency_id,
    ):
        """
        Alias for exists().
        """

        return self.exists(
            account,
            currency_id,
        )

    # -------------------------------------------------------------------------
    # Currency Mapping
    # -------------------------------------------------------------------------

    def odoo_currency(
        self,
        currency_id,
    ):
        """
        Returns Odoo currency.
        """

        return self.env[
            "res.currency"
        ].search(
            [
                (
                    "name",
                    "=",
                    currency_id,
                )
            ],
            limit=1,
        )

    # -------------------------------------------------------------------------
    # Synchronize Currencies
    # -------------------------------------------------------------------------

    def sync(
        self,
        account,
    ):
        """
        Synchronizes Mercado Libre currencies
        with Odoo currencies.
        """

        currencies = self.currencies(
            account,
        )

        synced = 0

        for data in currencies:

            currency = self.odoo_currency(
                data["id"],
            )

            if currency:

                currency.write({

                    "symbol":
                        data.get(
                            "symbol",
                            currency.symbol,
                        ),

                })

                synced += 1

        _logger.info(
            "Synchronized %s currencies.",
            synced,
        )

        return synced

    # -------------------------------------------------------------------------
    # Information
    # -------------------------------------------------------------------------

    def info(
        self,
        account,
        currency_id,
    ):
        """
        Returns simplified currency information.
        """

        data = self.currency(
            account,
            currency_id,
        )

        return {

            "id": data.get("id"),

            "description": data.get("description"),

            "symbol": data.get("symbol"),

            "decimal_places": data.get("decimal_places"),

        }