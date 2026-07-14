# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Mercado Libre Notification Service
"""

from __future__ import annotations

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class MLNotificationService(models.AbstractModel):
    """
    Central notification dispatcher for Mercado Libre.
    """

    _name = "ml.notification.service"
    _description = "Mercado Libre Notification Service"

    # -------------------------------------------------------------------------
    # Dispatcher
    # -------------------------------------------------------------------------

    def dispatch(
        self,
        account,
        notification,
    ):
        """
        Dispatch notification according to topic.
        """

        topic = notification.get("topic")

        resource = notification.get("resource")

        user_id = notification.get("user_id")

        _logger.info(
            "ML Notification | Topic=%s Resource=%s User=%s",
            topic,
            resource,
            user_id,
        )

        handlers = {

            "orders": self.process_order,

            "items": self.process_item,

            "shipments": self.process_shipment,

            "questions": self.process_question,

            "messages": self.process_message,

            "claims": self.process_claim,

            "payments": self.process_payment,

            "users": self.process_user,

        }

        handler = handlers.get(topic)

        if handler:

            return handler(
                account,
                notification,
            )

        _logger.warning(
            "Unsupported notification topic: %s",
            topic,
        )

        return False

    # -------------------------------------------------------------------------
    # Order
    # -------------------------------------------------------------------------

    def process_order(
        self,
        account,
        notification,
    ):

        return self._enqueue(
            account,
            "sync_order",
            notification,
        )

    # -------------------------------------------------------------------------
    # Item
    # -------------------------------------------------------------------------

    def process_item(
        self,
        account,
        notification,
    ):

        return self._enqueue(
            account,
            "sync_item",
            notification,
        )

    # -------------------------------------------------------------------------
    # Shipment
    # -------------------------------------------------------------------------

    def process_shipment(
        self,
        account,
        notification,
    ):

        return self._enqueue(
            account,
            "sync_shipment",
            notification,
        )

    # -------------------------------------------------------------------------
    # Question
    # -------------------------------------------------------------------------

    def process_question(
        self,
        account,
        notification,
    ):

        return self._enqueue(
            account,
            "sync_question",
            notification,
        )

    # -------------------------------------------------------------------------
    # Message
    # -------------------------------------------------------------------------

    def process_message(
        self,
        account,
        notification,
    ):

        return self._enqueue(
            account,
            "sync_message",
            notification,
        )

    # -------------------------------------------------------------------------
    # Claim
    # -------------------------------------------------------------------------

    def process_claim(
        self,
        account,
        notification,
    ):

        return self._enqueue(
            account,
            "sync_claim",
            notification,
        )

    # -------------------------------------------------------------------------
    # Payment
    # -------------------------------------------------------------------------

    def process_payment(
        self,
        account,
        notification,
    ):

        return self._enqueue(
            account,
            "sync_payment",
            notification,
        )

    # -------------------------------------------------------------------------
    # User
    # -------------------------------------------------------------------------

    def process_user(
        self,
        account,
        notification,
    ):

        return self._enqueue(
            account,
            "sync_user",
            notification,
        )

    # -------------------------------------------------------------------------
    # Queue Creation
    # -------------------------------------------------------------------------

    def _enqueue(
        self,
        account,
        action,
        payload,
    ):
        """
        Creates queue item for async processing.
        """

        queue = self.env["sce.queue"].create({

            "account_id": account.id,

            "action": action,

            "payload": payload,

            "priority": "2",

        })

        _logger.info(
            "Queue created (%s) for %s",
            queue.id,
            action,
        )

        return queue

    # -------------------------------------------------------------------------
    # Manual Processing
    # -------------------------------------------------------------------------

    def process_now(
        self,
        account,
        notification,
    ):
        """
        Immediate processing without queue.
        """

        topic = notification.get("topic")

        if topic == "orders":

            return self.env[
                "ml.order.service"
            ].synchronize(
                account
            )

        if topic == "items":

            return self.env[
                "ml.product.service"
            ].synchronize(
                account
            )

        if topic == "shipments":

            return self.env[
                "ml.shipment.service"
            ].synchronize(
                account
            )

        if topic == "questions":

            return self.env[
                "ml.question.service"
            ].synchronize(
                account
            )

        return False

    # -------------------------------------------------------------------------
    # Health
    # -------------------------------------------------------------------------

    def health(self):

        return {

            "service": "notification",

            "status": "ok",

        }

    # -------------------------------------------------------------------------
    # Supported Topics
    # -------------------------------------------------------------------------

    def supported_topics(self):

        return [

            "orders",

            "items",

            "shipments",

            "questions",

            "messages",

            "claims",

            "payments",

            "users",

        ]

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    def validate(
        self,
        notification,
    ):

        return (

            isinstance(
                notification,
                dict,
            )

            and

            "topic" in notification

            and

            "resource" in notification

        )

    # -------------------------------------------------------------------------
    # Entry Point
    # -------------------------------------------------------------------------

    def receive(
        self,
        account,
        notification,
    ):
        """
        Main entry point for ML webhooks.
        """

        if not self.validate(
            notification
        ):

            raise ValueError(
                "Invalid Mercado Libre notification."
            )

        return self.dispatch(
            account,
            notification,
        )