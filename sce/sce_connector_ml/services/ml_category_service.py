# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Mercado Libre Category Service

Provides access to Mercado Libre categories,
attributes and category prediction.
"""

from __future__ import annotations

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class MLCategoryService(models.AbstractModel):
    """
    Mercado Libre Category Service.
    """

    _name = "ml.category.service"
    _description = "Mercado Libre Category Service"

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _client(self):
        """
        Returns API client.
        """
        return self.env["ml.api.client"]

    # -------------------------------------------------------------------------
    # Root Categories
    # -------------------------------------------------------------------------

    def root(self, account):
        """
        Returns root categories for account site.
        """

        endpoint = f"/sites/{account.site_id.code}/categories"

        return self._client().get(
            account,
            endpoint,
        )

    # -------------------------------------------------------------------------
    # Search
    # -------------------------------------------------------------------------

    def search(
        self,
        account,
        query,
        limit=20,
    ):
        """
        Searches categories by text.
        """

        endpoint = (
            f"/sites/{account.site_id.code}"
            "/domain_discovery/search"
        )

        params = {
            "q": query,
            "limit": limit,
        }

        return self._client().get(
            account,
            endpoint,
            params=params,
        )

    # -------------------------------------------------------------------------
    # Predict
    # -------------------------------------------------------------------------

    def predict(
        self,
        account,
        title,
    ):
        """
        Predicts category from title.
        """

        result = self.search(
            account,
            title,
            limit=1,
        )

        if result:
            return result[0]

        return {}

    # -------------------------------------------------------------------------
    # Category
    # -------------------------------------------------------------------------

    def get(
        self,
        account,
        category_id,
    ):
        """
        Returns category information.
        """

        endpoint = (
            f"/categories/{category_id}"
        )

        return self._client().get(
            account,
            endpoint,
        )

    # -------------------------------------------------------------------------
    # Children
    # -------------------------------------------------------------------------

    def children(
        self,
        account,
        category_id,
    ):
        """
        Returns child categories.
        """

        category = self.get(
            account,
            category_id,
        )

        return category.get(
            "children_categories",
            [],
        )

    # -------------------------------------------------------------------------
    # Path
    # -------------------------------------------------------------------------

    def path(
        self,
        account,
        category_id,
    ):
        """
        Returns complete category path.
        """

        category = self.get(
            account,
            category_id,
        )

        return category.get(
            "path_from_root",
            [],
        )

    # -------------------------------------------------------------------------
    # Attributes
    # -------------------------------------------------------------------------

    def attributes(
        self,
        account,
        category_id,
    ):
        """
        Returns category attributes.
        """

        endpoint = (
            f"/categories/{category_id}/attributes"
        )

        return self._client().get(
            account,
            endpoint,
        )

    # -------------------------------------------------------------------------
    # Listing Types
    # -------------------------------------------------------------------------

    def listing_types(
        self,
        account,
        category_id,
    ):
        """
        Returns available listing types.
        """

        endpoint = (
            f"/categories/{category_id}/listing_types"
        )

        return self._client().get(
            account,
            endpoint,
        )

    # -------------------------------------------------------------------------
    # Shipping
    # -------------------------------------------------------------------------

    def shipping_options(
        self,
        account,
        category_id,
    ):
        """
        Returns shipping preferences.
        """

        endpoint = (
            f"/categories/{category_id}"
            "/shipping_preferences"
        )

        return self._client().get(
            account,
            endpoint,
        )

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    def validate(
        self,
        account,
        category_id,
    ):
        """
        Checks if category exists.
        """

        try:

            category = self.get(
                account,
                category_id,
            )

            return bool(category)

        except Exception:

            _logger.exception(
                "Invalid Mercado Libre category %s",
                category_id,
            )

            return False