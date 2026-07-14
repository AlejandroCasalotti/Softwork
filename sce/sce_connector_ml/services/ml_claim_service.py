# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Mercado Libre Claim Service
"""

from __future__ import annotations

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class MLClaimService(models.AbstractModel):
    """
    Mercado Libre Claim Service.
    """

    _name = "ml.claim.service"
    _description = "Mercado Libre Claim Service"

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _client(self):
        return self.env["ml.api.client"]

    # -------------------------------------------------------------------------
    # Claim
    # -------------------------------------------------------------------------

    def get(
        self,
        account,
        claim_id,
    ):
        """
        Returns claim information.
        """

        return self._client().get(
            account,
            f"/post-purchase/v1/claims/{claim_id}",
        )

    # -------------------------------------------------------------------------
    # Search
    # -------------------------------------------------------------------------

    def search(
        self,
        account,
        status=None,
    ):

        params = {}

        if status:

            params["status"] = status

        return self._client().get(

            account,

            "/post-purchase/v1/claims/search",

            params=params,

        )

    # -------------------------------------------------------------------------
    # Messages
    # -------------------------------------------------------------------------

    def messages(
        self,
        account,
        claim_id,
    ):

        return self._client().get(

            account,

            f"/post-purchase/v1/claims/{claim_id}/messages",

        )

    # -------------------------------------------------------------------------
    # Dashboard
    # -------------------------------------------------------------------------

    def dashboard(
        self,
        account,
        claim_id,
    ):

        claim = self.get(
            account,
            claim_id,
        )

        return {

            "id": claim.get("id"),

            "type": claim.get("type"),

            "stage": claim.get("stage"),

            "status": claim.get("status"),

            "reason": claim.get("reason"),

            "resource_id": claim.get("resource_id"),

        }

    # -------------------------------------------------------------------------
    # Synchronize
    # -------------------------------------------------------------------------

    def synchronize(
        self,
        account,
        claim_id,
    ):

        claim = self.get(
            account,
            claim_id,
        )

        self.env["sce.log"].log_info(

            "Mercado Libre claim synchronized.",

            account_id=account.id,

            payload=claim,

        )

        return claim

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
            ].me(
                account
            )

            return {

                "service": "claim",

                "status": "ok",

            }

        except Exception as error:

            return {

                "service": "claim",

                "status": "error",

                "message": str(error),

            }