# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Mercado Libre User Service
"""

from __future__ import annotations

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class MLUserService(models.AbstractModel):
    """
    Mercado Libre User Service.
    """

    _name = "ml.user.service"
    _description = "Mercado Libre User Service"

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _client(self):
        return self.env["ml.api.client"]

    # -------------------------------------------------------------------------
    # Current User
    # -------------------------------------------------------------------------

    def me(
        self,
        account,
    ):
        """
        Returns authenticated user.
        """

        return self._client().get(
            account,
            "/users/me",
        )

    # -------------------------------------------------------------------------
    # User by ID
    # -------------------------------------------------------------------------

    def get(
        self,
        account,
        user_id,
    ):
        """
        Returns one Mercado Libre user.
        """

        return self._client().get(
            account,
            f"/users/{user_id}",
        )

    # -------------------------------------------------------------------------
    # Seller Information
    # -------------------------------------------------------------------------

    def seller(
        self,
        account,
    ):
        """
        Returns seller profile.
        """

        data = self.me(account)

        return {

            "id": data.get("id"),

            "nickname": data.get("nickname"),

            "email": data.get("email"),

            "country_id": data.get("country_id"),

            "site_id": data.get("site_id"),

            "status": data.get("status"),

            "registration_date": data.get(
                "registration_date"
            ),

        }

    # -------------------------------------------------------------------------
    # Reputation
    # -------------------------------------------------------------------------

    def reputation(
        self,
        account,
    ):
        """
        Returns seller reputation.
        """

        data = self.me(account)

        return data.get(
            "seller_reputation",
            {},
        )

    # -------------------------------------------------------------------------
    # Addresses
    # -------------------------------------------------------------------------

    def addresses(
        self,
        account,
    ):
        """
        Returns seller addresses.
        """

        data = self.me(account)

        return data.get(
            "addresses",
            [],
        )

    # -------------------------------------------------------------------------
    # Shipping Preferences
    # -------------------------------------------------------------------------

    def shipping_preferences(
        self,
        account,
    ):
        """
        Returns shipping preferences.
        """

        user = self.me(account)

        return self._client().get(
            account,
            f"/users/{user['id']}/shipping_preferences",
        )

    # -------------------------------------------------------------------------
    # Brands
    # -------------------------------------------------------------------------

    def brands(
        self,
        account,
    ):
        """
        Returns seller brands.
        """

        user = self.me(account)

        return self._client().get(
            account,
            f"/users/{user['id']}/brands",
        )

    # -------------------------------------------------------------------------
    # Store
    # -------------------------------------------------------------------------

    def store(
        self,
        account,
    ):
        """
        Returns Mercado Shops information.
        """

        user = self.me(account)

        return self._client().get(
            account,
            f"/users/{user['id']}/stores",
        )

    # -------------------------------------------------------------------------
    # Update Local Account
    # -------------------------------------------------------------------------

    def synchronize(
        self,
        account,
    ):
        """
        Synchronizes seller data with sce.account.
        """

        data = self.me(account)

        account.write({

            "external_user_id": str(
                data.get("id")
            ),

            "external_user_name":
                data.get("nickname"),

            "external_email":
                data.get("email"),

        })

        _logger.info(

            "Mercado Libre account synchronized (%s)",

            account.name,

        )

        return data

    # -------------------------------------------------------------------------
    # Account Summary
    # -------------------------------------------------------------------------

    def summary(
        self,
        account,
    ):
        """
        Returns seller summary.
        """

        profile = self.seller(account)

        reputation = self.reputation(account)

        return {

            "profile": profile,

            "reputation": reputation,

        }

    # -------------------------------------------------------------------------
    # Permissions
    # -------------------------------------------------------------------------

    def permissions(
        self,
        account,
    ):
        """
        Returns OAuth scopes.
        """

        return account.get_configuration(
            "scopes"
        )

    # -------------------------------------------------------------------------
    # Verify Authentication
    # -------------------------------------------------------------------------

    def authenticated(
        self,
        account,
    ):
        """
        Checks if account is authenticated.
        """

        try:

            self.me(account)

            return True

        except Exception:

            return False

    # -------------------------------------------------------------------------
    # Validate Seller
    # -------------------------------------------------------------------------

    def validate(
        self,
        account,
    ):
        """
        Validates account information.
        """

        data = self.me(account)

        return bool(
            data.get("id")
        )

    # -------------------------------------------------------------------------
    # Dashboard Information
    # -------------------------------------------------------------------------

    def dashboard(
        self,
        account,
    ):
        """
        Information for dashboard widgets.
        """

        seller = self.seller(account)

        reputation = self.reputation(account)

        return {

            "nickname":
                seller.get("nickname"),

            "email":
                seller.get("email"),

            "site":
                seller.get("site_id"),

            "country":
                seller.get("country_id"),

            "status":
                seller.get("status"),

            "reputation":
                reputation,

        }

    # -------------------------------------------------------------------------
    # Health Check
    # -------------------------------------------------------------------------

    def health(
        self,
        account,
    ):
        """
        Service health.
        """

        try:

            self.me(account)

            return {

                "service": "user",

                "status": "ok",

            }

        except Exception as error:

            return {

                "service": "user",

                "status": "error",

                "message": str(error),

            }