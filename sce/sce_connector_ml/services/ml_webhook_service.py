# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Mercado Libre Webhook Service
"""

from __future__ import annotations

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class MLWebhookService(models.AbstractModel):
    """
    Mercado Libre Webhook Service.
    """

    _name = "ml.webhook.service"
    _description = "Mercado Libre Webhook Service"

    # -------------------------------------------------------------------------
    # Process Webhook
    # -------------------------------------------------------------------------

    def process(
        self,
        account,
        payload,
        headers=None,
    ):
        """
        Main webhook dispatcher.
        """

        topic = payload.get("topic")
        resource = payload.get("resource")

        self.env["sce.log"].log_info(
            "Mercado Libre webhook received.",
            account_id=account.id,
            payload=payload,
        )

        webhook = self.env["sce.webhook"].create({

            "account_id": account.id,

            "event": topic,

            "payload": payload,

            "headers": headers or {},

            "external_resource": resource,

        })

        handler = getattr(

            self,

            "_handle_%s" % topic.replace(".", "_"),

            None,

        )

        if handler:

            handler(
                account,
                payload,
                webhook,
            )

        else:

            self._enqueue_generic(
                account,
                topic,
                payload,
            )

        return webhook

    # -------------------------------------------------------------------------
    # Orders
    # -------------------------------------------------------------------------

    def _handle_orders(
        self,
        account,
        payload,
        webhook,
    ):
        """
        Order notification.
        """

        self.env["sce.kernel"].enqueue(

            account,

            "sync_order",

            payload,

        )

    # -------------------------------------------------------------------------
    # Items
    # -------------------------------------------------------------------------

    def _handle_items(
        self,
        account,
        payload,
        webhook,
    ):

        self.env["sce.kernel"].enqueue(

            account,

            "sync_product",

            payload,

        )

    # -------------------------------------------------------------------------
    # Questions
    # -------------------------------------------------------------------------

    def _handle_questions(
        self,
        account,
        payload,
        webhook,
    ):

        self.env["sce.kernel"].enqueue(

            account,

            "sync_question",

            payload,

        )

    # -------------------------------------------------------------------------
    # Messages
    # -------------------------------------------------------------------------

    def _handle_messages(
        self,
        account,
        payload,
        webhook,
    ):

        self.env["sce.kernel"].enqueue(

            account,

            "sync_message",

            payload,

        )

    # -------------------------------------------------------------------------
    # Shipments
    # -------------------------------------------------------------------------

    def _handle_shipments(
        self,
        account,
        payload,
        webhook,
    ):

        self.env["sce.kernel"].enqueue(

            account,

            "sync_shipment",

            payload,

        )

    # -------------------------------------------------------------------------
    # Claims
    # -------------------------------------------------------------------------

    def _handle_claims(
        self,
        account,
        payload,
        webhook,
    ):

        self.env["sce.kernel"].enqueue(

            account,

            "sync_claim",

            payload,

        )

    # -------------------------------------------------------------------------
    # Payments
    # -------------------------------------------------------------------------

    def _handle_payments(
        self,
        account,
        payload,
        webhook,
    ):

        self.env["sce.kernel"].enqueue(

            account,

            "sync_payment",

            payload,

        )

    # -------------------------------------------------------------------------
    # Generic
    # -------------------------------------------------------------------------

    def _enqueue_generic(
        self,
        account,
        topic,
        payload,
    ):

        self.env["sce.kernel"].enqueue(

            account,

            topic,

            payload,

        )

    # -------------------------------------------------------------------------
    # Signature Validation
    # -------------------------------------------------------------------------

    def validate_signature(
        self,
        headers,
        body=None,
    ):
        """
        Placeholder for Mercado Libre signature validation.
        """

        return True

    # -------------------------------------------------------------------------
    # Dashboard
    # -------------------------------------------------------------------------

    def dashboard(
        self,
        account,
    ):

        total = self.env["sce.webhook"].search_count([

            ("account_id", "=", account.id),

        ])

        failed = self.env["sce.webhook"].search_count([

            ("account_id", "=", account.id),

            ("state", "=", "failed"),

        ])

        return {

            "received": total,

            "failed": failed,

            "processed": total - failed,

        }

    # -------------------------------------------------------------------------
    # Retry
    # -------------------------------------------------------------------------

    def retry_failed(
        self,
        account,
    ):

        webhooks = self.env["sce.webhook"].search([

            ("account_id", "=", account.id),

            ("state", "=", "failed"),

        ])

        for webhook in webhooks:

            webhook.process()

        return len(webhooks)

    # -------------------------------------------------------------------------
    # Health
    # -------------------------------------------------------------------------

    def health(
        self,
        account,
    ):

        try:

            self.env["ml.user.service"].me(
                account
            )

            return {

                "service": "webhook",

                "status": "ok",

            }

        except Exception as error:

            return {

                "service": "webhook",

                "status": "error",

                "message": str(error),

            }