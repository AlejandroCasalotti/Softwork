# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Mercado Libre Message Service
"""

from __future__ import annotations

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class MLMessageService(models.AbstractModel):
    """
    Mercado Libre Messages Service.
    """

    _name = "ml.message.service"
    _description = "Mercado Libre Message Service"

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _client(self):
        return self.env["ml.api.client"]

    # -------------------------------------------------------------------------
    # Conversations
    # -------------------------------------------------------------------------

    def conversations(
        self,
        account,
        order_id,
    ):
        """
        Returns conversations for an order.
        """

        return self._client().get(
            account,
            f"/messages/orders/{order_id}"
        )

    # -------------------------------------------------------------------------
    # Conversation
    # -------------------------------------------------------------------------

    def conversation(
        self,
        account,
        conversation_id,
    ):
        """
        Returns one conversation.
        """

        return self._client().get(
            account,
            f"/messages/{conversation_id}"
        )

    # -------------------------------------------------------------------------
    # Messages
    # -------------------------------------------------------------------------

    def messages(
        self,
        account,
        conversation_id,
    ):
        """
        Returns messages of a conversation.
        """

        return self._client().get(
            account,
            f"/messages/{conversation_id}/messages"
        )

    # -------------------------------------------------------------------------
    # Send Message
    # -------------------------------------------------------------------------

    def send(
        self,
        account,
        conversation_id,
        text,
    ):
        """
        Sends a message.
        """

        payload = {

            "text": text,

        }

        return self._client().post(
            account,
            f"/messages/{conversation_id}/messages",
            json=payload,
        )

    # -------------------------------------------------------------------------
    # Mark Read
    # -------------------------------------------------------------------------

    def mark_as_read(
        self,
        account,
        conversation_id,
    ):
        """
        Marks conversation as read.
        """

        return self._client().post(
            account,
            f"/messages/{conversation_id}/read"
        )

    # -------------------------------------------------------------------------
    # Attachments
    # -------------------------------------------------------------------------

    def attachments(
        self,
        account,
        message_id,
    ):
        """
        Returns attachments.
        """

        return self._client().get(
            account,
            f"/messages/{message_id}/attachments"
        )

    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    def statistics(
        self,
        account,
        order_id,
    ):
        """
        Returns conversation statistics.
        """

        conversations = self.conversations(
            account,
            order_id,
        )

        total = len(
            conversations.get(
                "results",
                [],
            )
        )

        unread = 0

        for conv in conversations.get(
            "results",
            [],
        ):

            if not conv.get(
                "read",
                True,
            ):

                unread += 1

        return {

            "total": total,

            "unread": unread,

            "read": total - unread,

        }

    # -------------------------------------------------------------------------
    # Latest Messages
    # -------------------------------------------------------------------------

    def latest(
        self,
        account,
        order_id,
        limit=20,
    ):
        """
        Returns latest conversations.
        """

        conversations = self.conversations(
            account,
            order_id,
        )

        return conversations.get(
            "results",
            [],
        )[:limit]

    # -------------------------------------------------------------------------
    # Synchronization
    # -------------------------------------------------------------------------

    def synchronize(
        self,
        account,
        order_id=None,
    ):
        """
        Placeholder for future synchronization.
        """

        if not order_id:

            return []

        messages = self.latest(
            account,
            order_id,
            limit=100,
        )

        _logger.info(

            "Retrieved %s Mercado Libre conversations.",

            len(messages),

        )

        return messages

    # -------------------------------------------------------------------------
    # Search
    # -------------------------------------------------------------------------

    def search(
        self,
        account,
        order_id,
        text,
    ):
        """
        Searches messages containing text.
        """

        conversations = self.messages(
            account,
            order_id,
        )

        results = []

        for message in conversations.get(
            "results",
            [],
        ):

            body = message.get(
                "text",
                "",
            )

            if text.lower() in body.lower():

                results.append(
                    message
                )

        return results

    # -------------------------------------------------------------------------
    # Dashboard
    # -------------------------------------------------------------------------

    def dashboard(
        self,
        account,
        order_id,
    ):
        """
        Dashboard information.
        """

        stats = self.statistics(
            account,
            order_id,
        )

        return {

            "statistics": stats,

            "latest": self.latest(
                account,
                order_id,
                limit=5,
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

            return {

                "service": "messages",

                "status": "ok",

            }

        except Exception as error:

            return {

                "service": "messages",

                "status": "error",

                "message": str(error),

            }