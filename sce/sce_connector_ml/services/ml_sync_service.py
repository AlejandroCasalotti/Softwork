# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Mercado Libre Synchronization Service
"""

from __future__ import annotations

import logging
from odoo import models

_logger = logging.getLogger(__name__)


class MLSyncService(models.AbstractModel):
    """
    Main synchronization orchestrator.

    Executes synchronization processes
    in a controlled order.
    """

    _name = "sce.ml.sync.service"
    _description = "Mercado Libre Synchronization Service"

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    def _log(self, account, level, message, **kwargs):
        values = {
            "account_id": account.id,
            "connector_id": account.connector_id.id,
            "plugin_id": account.plugin_id.id,
            "category": "synchronization",
        }
        values.update(kwargs)

        self.env["sce.log"].create_log(
            level=level,
            message=message,
            **values,
        )

    # ---------------------------------------------------------
    # Main Synchronization
    # ---------------------------------------------------------

    def synchronize(self, account):
        """
        Executes complete synchronization.
        """

        self._log(
            account,
            "info",
            "Starting Mercado Libre synchronization.",
        )

        result = {
            "products": False,
            "stock": False,
            "prices": False,
            "orders": False,
            "shipments": False,
            "messages": False,
            "questions": False,
        }

        try:

            if account.sync_products:
                result["products"] = self.sync_products(account)

            if account.sync_stock:
                result["stock"] = self.sync_stock(account)

            if account.sync_prices:
                result["prices"] = self.sync_prices(account)

            if account.sync_orders:
                result["orders"] = self.sync_orders(account)

            if account.sync_shipments:
                result["shipments"] = self.sync_shipments(account)

            result["messages"] = self.sync_messages(account)
            result["questions"] = self.sync_questions(account)

            account.update_sync_status(
                "success",
                "Synchronization completed successfully."
            )

            self._log(
                account,
                "info",
                "Synchronization finished successfully."
            )

            return result

        except Exception as error:

            account.update_sync_status(
                "error",
                str(error),
            )

            self._log(
                account,
                "error",
                str(error),
            )

            raise

    # ---------------------------------------------------------
    # Individual Synchronizations
    # ---------------------------------------------------------

    def sync_products(self, account):

        service = self.env[
            "sce.ml.product.service"
        ]

        return service.import_products(account)

    # ---------------------------------------------------------

    def sync_stock(self, account):

        service = self.env[
            "sce.ml.stock.service"
        ]

        return service.export_stock(account)

    # ---------------------------------------------------------

    def sync_prices(self, account):

        service = self.env[
            "sce.ml.price.service"
        ]

        return service.export_prices(account)

    # ---------------------------------------------------------

    def sync_orders(self, account):

        service = self.env[
            "sce.ml.order.service"
        ]

        return service.import_orders(account)

    # ---------------------------------------------------------
    # Remaining Synchronizations
    # ---------------------------------------------------------

    def sync_shipments(self, account):
        """
        Imports and updates Mercado Libre shipments.
        """

        service = self.env[
            "sce.ml.shipment.service"
        ]

        return service.import_shipments(account)

    # ---------------------------------------------------------

    def sync_messages(self, account):
        """
        Imports marketplace messages.
        """

        service = self.env[
            "sce.ml.message.service"
        ]

        return service.import_messages(account)

    # ---------------------------------------------------------

    def sync_questions(self, account):
        """
        Imports marketplace questions.
        """

        service = self.env[
            "sce.ml.question.service"
        ]

        return service.import_questions(account)

    # ---------------------------------------------------------
    # Partial Synchronization
    # ---------------------------------------------------------

    def synchronize_resource(
        self,
        account,
        resource,
    ):
        """
        Synchronizes a single resource.
        """

        methods = {

            "products":
                self.sync_products,

            "stock":
                self.sync_stock,

            "prices":
                self.sync_prices,

            "orders":
                self.sync_orders,

            "shipments":
                self.sync_shipments,

            "messages":
                self.sync_messages,

            "questions":
                self.sync_questions,

        }

        method = methods.get(resource)

        if not method:

            raise ValueError(
                "Unknown synchronization resource: %s"
                % resource
            )

        self._log(

            account,

            "info",

            "Synchronizing resource: %s"
            % resource,

        )

        return method(account)

    # ---------------------------------------------------------
    # Incremental Synchronization
    # ---------------------------------------------------------

    def synchronize_incremental(
        self,
        account,
    ):
        """
        Executes incremental synchronization.
        """

        self._log(

            account,

            "info",

            "Starting incremental synchronization.",

        )

        result = {}

        if account.sync_orders:

            result["orders"] = self.sync_orders(
                account
            )

        if account.sync_shipments:

            result["shipments"] = self.sync_shipments(
                account
            )

        result["messages"] = self.sync_messages(
            account
        )

        result["questions"] = self.sync_questions(
            account
        )

        account.update_sync_status(

            "success",

            "Incremental synchronization completed.",

        )

        return result

    # ---------------------------------------------------------
    # Scheduled Synchronization
    # ---------------------------------------------------------

    def synchronize_scheduled(
        self,
    ):
        """
        Called by cron.
        """

        accounts = self.env[
            "sce.account"
        ].search([

            ("state", "=", "connected"),

            ("auto_sync", "=", True),

            ("active", "=", True),

        ])

        results = []

        for account in accounts:

            try:

                results.append({

                    "account":
                        account.id,

                    "result":
                        self.synchronize_incremental(
                            account
                        ),

                })

            except Exception as error:

                self._log(

                    account,

                    "error",

                    str(error),

                )

        return results

    # ---------------------------------------------------------
    # Retry
    # ---------------------------------------------------------

    def retry_failed_jobs(
        self,
        account=None,
    ):
        """
        Retries failed synchronization jobs.
        """

        domain = [

            ("state", "=", "failed"),

        ]

        if account:

            domain.append(

                ("account_id", "=", account.id)

            )

        jobs = self.env[
            "sce.job"
        ].search(domain)

        for job in jobs:

            try:

                job.retry()

            except Exception as error:

                _logger.exception(error)

        return len(jobs)

    # ---------------------------------------------------------
    # Statistics
    # ---------------------------------------------------------

    def get_statistics(
        self,
        account,
    ):
        """
        Returns synchronization statistics.
        """

        return {

            "products":
                account.products_synced,

            "orders":
                account.orders_synced,

            "shipments":
                account.shipments_synced,

            "last_sync":
                account.last_sync,

            "status":
                account.last_sync_status,

            "message":
                account.last_sync_message,

        }

    # ---------------------------------------------------------
    # Health Check
    # ---------------------------------------------------------

    def health_check(
        self,
        account,
    ):
        """
        Returns connector health information.
        """

        provider = account.get_provider()

        connection = provider.test_connection(
            account
        )

        return {

            "connected":
                connection,

            "account":
                account.external_user_name,

            "last_sync":
                account.last_sync,

            "state":
                account.state,

            "connector":
                account.connector_code,

        }