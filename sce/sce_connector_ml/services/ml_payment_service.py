# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Mercado Libre Payment Service
"""

from __future__ import annotations

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class MLPaymentService(models.AbstractModel):
    """
    Mercado Libre Payment Service.
    """

    _name = "ml.payment.service"
    _description = "Mercado Libre Payment Service"

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _client(self):
        return self.env["ml.api.client"]

    # -------------------------------------------------------------------------
    # Payment
    # -------------------------------------------------------------------------

    def get(
        self,
        account,
        payment_id,
    ):
        """
        Returns payment information.
        """

        return self._client().get(
            account,
            f"/payments/{payment_id}",
        )

    # -------------------------------------------------------------------------
    # Order Payments
    # -------------------------------------------------------------------------

    def from_order(
        self,
        account,
        order_id,
    ):
        """
        Returns all payments of an order.
        """

        order = self.env[
            "ml.order.service"
        ].get(
            account,
            order_id,
        )

        payments = []

        for payment in order.get(
            "payments",
            [],
        ):

            if payment.get("id"):

                payments.append(

                    self.get(
                        account,
                        payment["id"],
                    )

                )

        return payments

    # -------------------------------------------------------------------------
    # Status
    # -------------------------------------------------------------------------

    def status(
        self,
        account,
        payment_id,
    ):

        payment = self.get(
            account,
            payment_id,
        )

        return payment.get(
            "status"
        )

    # -------------------------------------------------------------------------
    # Approved
    # -------------------------------------------------------------------------

    def approved(
        self,
        account,
        payment_id,
    ):

        return (

            self.status(
                account,
                payment_id,
            )

            ==

            "approved"

        )

    # -------------------------------------------------------------------------
    # Dashboard
    # -------------------------------------------------------------------------

    def dashboard(
        self,
        account,
        payment_id,
    ):

        payment = self.get(
            account,
            payment_id,
        )

        return {

            "id": payment.get("id"),

            "status": payment.get("status"),

            "status_detail": payment.get("status_detail"),

            "transaction_amount": payment.get(
                "transaction_amount"
            ),

            "currency": payment.get(
                "currency_id"
            ),

            "date_created": payment.get(
                "date_created"
            ),

        }

    # -------------------------------------------------------------------------
    # Synchronize
    # -------------------------------------------------------------------------

    def synchronize(
        self,
        account,
        payment_id,
    ):

        payment = self.get(
            account,
            payment_id,
        )

        self.env["sce.log"].log_info(

            "Mercado Libre payment synchronized.",

            account_id=account.id,

            payload=payment,

        )

        return payment

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

                "service": "payment",

                "status": "ok",

            }

        except Exception as error:

            return {

                "service": "payment",

                "status": "error",

                "message": str(error),

            }