# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Mercado Libre Question Service
"""

from __future__ import annotations

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class MLQuestionService(models.AbstractModel):
    """
    Mercado Libre Questions Service.
    """

    _name = "ml.question.service"
    _description = "Mercado Libre Question Service"

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _client(self):
        return self.env["ml.api.client"]

    # -------------------------------------------------------------------------
    # Questions by Item
    # -------------------------------------------------------------------------

    def get_questions(
        self,
        account,
        item_id,
        status=None,
        limit=50,
        offset=0,
    ):
        """
        Returns questions of one publication.
        """

        params = {
            "item_id": item_id,
            "limit": limit,
            "offset": offset,
        }

        if status:
            params["status"] = status

        return self._client().get(
            account,
            "/questions/search",
            params=params,
        )

    # -------------------------------------------------------------------------
    # One Question
    # -------------------------------------------------------------------------

    def get(
        self,
        account,
        question_id,
    ):
        """
        Returns one question.
        """

        return self._client().get(
            account,
            f"/questions/{question_id}",
        )

    # -------------------------------------------------------------------------
    # Pending Questions
    # -------------------------------------------------------------------------

    def pending(
        self,
        account,
        limit=100,
    ):
        """
        Returns unanswered questions.
        """

        return self._client().get(
            account,
            "/questions/search",
            params={
                "status": "UNANSWERED",
                "limit": limit,
            },
        )

    # -------------------------------------------------------------------------
    # Answer Question
    # -------------------------------------------------------------------------

    def answer(
        self,
        account,
        question_id,
        text,
    ):
        """
        Answers a Mercado Libre question.
        """

        payload = {
            "question_id": question_id,
            "text": text,
        }

        return self._client().post(
            account,
            "/answers",
            json=payload,
        )

    # -------------------------------------------------------------------------
    # Delete Answer
    # -------------------------------------------------------------------------

    def delete_answer(
        self,
        account,
        answer_id,
    ):
        """
        Deletes an answer.
        """

        return self._client().delete(
            account,
            f"/answers/{answer_id}",
        )

    # -------------------------------------------------------------------------
    # Count Pending
    # -------------------------------------------------------------------------

    def count_pending(
        self,
        account,
    ):
        """
        Returns pending questions count.
        """

        result = self.pending(account)

        return len(
            result.get(
                "questions",
                [],
            )
        )

    # -------------------------------------------------------------------------
    # Has Pending
    # -------------------------------------------------------------------------

    def has_pending(
        self,
        account,
    ):
        """
        Checks pending questions.
        """

        return self.count_pending(
            account
        ) > 0

    # -------------------------------------------------------------------------
    # Last Questions
    # -------------------------------------------------------------------------

    def latest(
        self,
        account,
        limit=10,
    ):
        """
        Returns latest questions.
        """

        result = self._client().get(
            account,
            "/questions/search",
            params={
                "sort_fields": "date_created",
                "sort_types": "DESC",
                "limit": limit,
            },
        )

        return result.get(
            "questions",
            [],
        )

    # -------------------------------------------------------------------------
    # Search by Seller
    # -------------------------------------------------------------------------

    def seller_questions(
        self,
        account,
        seller_id,
        limit=100,
    ):
        """
        Returns seller questions.
        """

        return self._client().get(
            account,
            "/questions/search",
            params={
                "seller_id": seller_id,
                "limit": limit,
            },
        )

    # -------------------------------------------------------------------------
    # Search by Item
    # -------------------------------------------------------------------------

    def item_questions(
        self,
        account,
        item_id,
    ):
        """
        Shortcut.
        """

        return self.get_questions(
            account,
            item_id,
        )

    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    def statistics(
        self,
        account,
    ):
        """
        Returns questions statistics.
        """

        pending = self.count_pending(
            account
        )

        latest = self.latest(
            account,
            limit=100,
        )

        answered = 0

        unanswered = 0

        for question in latest:

            if question.get("status") == "ANSWERED":
                answered += 1
            else:
                unanswered += 1

        return {

            "pending": pending,

            "answered": answered,

            "unanswered": unanswered,

            "total": answered + unanswered,

        }

    # -------------------------------------------------------------------------
    # Synchronize
    # -------------------------------------------------------------------------

    def synchronize(
        self,
        account,
    ):
        """
        Placeholder for future synchronization.
        """

        questions = self.latest(
            account,
            limit=100,
        )

        _logger.info(
            "Retrieved %s Mercado Libre questions.",
            len(questions),
        )

        return questions

    # -------------------------------------------------------------------------
    # Notification Helper
    # -------------------------------------------------------------------------

    def notify_pending(
        self,
        account,
    ):
        """
        Returns pending questions for dashboard.
        """

        return {

            "pending": self.count_pending(
                account
            ),

            "questions": self.pending(
                account
            ).get(
                "questions",
                [],
            ),

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

            self.pending(account)

            return True

        except Exception:

            return False