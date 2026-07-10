# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Mercado Libre Scheduled Jobs
"""

from __future__ import annotations

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class MLCron(models.Model):
    """
    Scheduled tasks for Mercado Libre connector.
    """

    _name = "sce.ml.cron"
    _description = "Mercado Libre Scheduled Jobs"

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _accounts(self):
        """
        Returns all active and connected Mercado Libre accounts.
        """

        return self.env[
            "sce.ml.account"
        ].search([
            ("active", "=", True),
            ("connected", "=", True),
        ])

    # -------------------------------------------------------------------------

    def _product_service(self):
        """
        Returns Product Service.
        """

        return self.env[
            "sce.ml.product.service"
        ]

    # -------------------------------------------------------------------------

    def _order_service(self):
        """
        Returns Order Service.
        """

        return self.env[
            "sce.ml.order.service"
        ]

    # -------------------------------------------------------------------------

    def _shipment_service(self):
        """
        Returns Shipment Service.
        """

        return self.env[
            "sce.ml.shipment.service"
        ]

    # -------------------------------------------------------------------------

    def _auth_service(self):
        """
        Returns Authentication Service.
        """

        return self.env[
            "sce.ml.auth.service"
        ]

    # -------------------------------------------------------------------------
    # Products
    # -------------------------------------------------------------------------

    def cron_import_products(self):
        """
        Imports products from Mercado Libre.
        """

        service = self._product_service()

        for account in self._accounts():

            try:

                service.import_recent_products(
                    account,
                )

                _logger.info(
                    "[SCE][ML] Products imported (%s)",
                    account.display_name,
                )

            except Exception:

                _logger.exception(
                    "[SCE][ML] Product import failed (%s)",
                    account.display_name,
                )

        return True

    # -------------------------------------------------------------------------

    def cron_sync_products(self):
        """
        Synchronizes imported products.
        """

        service = self._product_service()

        for account in self._accounts():

            try:

                service.synchronize_products(
                    account,
                )

                _logger.info(
                    "[SCE][ML] Products synchronized (%s)",
                    account.display_name,
                )

            except Exception:

                _logger.exception(
                    "[SCE][ML] Product synchronization failed (%s)",
                    account.display_name,
                )

        return True

            # -------------------------------------------------------------------------
    # Orders
    # -------------------------------------------------------------------------

    def cron_import_orders(self):
        """
        Imports recent Mercado Libre orders.
        """

        service = self._order_service()

        for account in self._accounts():

            try:

                service.import_recent_orders(
                    account,
                )

                _logger.info(
                    "[SCE][ML] Orders imported (%s)",
                    account.display_name,
                )

            except Exception:

                _logger.exception(
                    "[SCE][ML] Order import failed (%s)",
                    account.display_name,
                )

        return True

    # -------------------------------------------------------------------------

    def cron_sync_orders(self):
        """
        Synchronizes imported Mercado Libre orders.
        """

        service = self._order_service()

        for account in self._accounts():

            try:

                service.synchronize_pending_orders(
                    account,
                )

                _logger.info(
                    "[SCE][ML] Orders synchronized (%s)",
                    account.display_name,
                )

            except Exception:

                _logger.exception(
                    "[SCE][ML] Order synchronization failed (%s)",
                    account.display_name,
                )

        return True

    # -------------------------------------------------------------------------

    def cron_retry_failed_orders(self):
        """
        Retries failed order synchronizations.
        """

        service = self._order_service()

        for account in self._accounts():

            try:

                service.retry_failed_orders(
                    account,
                )

                _logger.info(
                    "[SCE][ML] Failed orders reprocessed (%s)",
                    account.display_name,
                )

            except Exception:

                _logger.exception(
                    "[SCE][ML] Failed order retry error (%s)",
                    account.display_name,
                )

        return True

    # -------------------------------------------------------------------------

    def cron_cleanup_orders(self):
        """
        Archives cancelled Mercado Libre orders.
        """

        service = self._order_service()

        for account in self._accounts():

            try:

                service.cleanup_cancelled_orders(
                    account,
                )

                _logger.info(
                    "[SCE][ML] Cancelled orders archived (%s)",
                    account.display_name,
                )

            except Exception:

                _logger.exception(
                    "[SCE][ML] Order cleanup failed (%s)",
                    account.display_name,
                )

        return True

            # -------------------------------------------------------------------------
    # Shipments
    # -------------------------------------------------------------------------

    def cron_import_shipments(self):
        """
        Imports recent Mercado Libre shipments.
        """

        service = self._shipment_service()

        for account in self._accounts():

            try:

                service.import_recent_shipments(
                    account,
                )

                _logger.info(
                    "[SCE][ML] Shipments imported (%s)",
                    account.display_name,
                )

            except Exception:

                _logger.exception(
                    "[SCE][ML] Shipment import failed (%s)",
                    account.display_name,
                )

        return True

    # -------------------------------------------------------------------------

    def cron_sync_shipments(self):
        """
        Synchronizes imported Mercado Libre shipments.
        """

        service = self._shipment_service()

        for account in self._accounts():

            try:

                service.synchronize_pending_shipments(
                    account,
                )

                _logger.info(
                    "[SCE][ML] Shipments synchronized (%s)",
                    account.display_name,
                )

            except Exception:

                _logger.exception(
                    "[SCE][ML] Shipment synchronization failed (%s)",
                    account.display_name,
                )

        return True

    # -------------------------------------------------------------------------

    def cron_retry_failed_shipments(self):
        """
        Retries failed shipment synchronizations.
        """

        service = self._shipment_service()

        for account in self._accounts():

            try:

                service.retry_failed_shipments(
                    account,
                )

                _logger.info(
                    "[SCE][ML] Failed shipments reprocessed (%s)",
                    account.display_name,
                )

            except Exception:

                _logger.exception(
                    "[SCE][ML] Failed shipment retry error (%s)",
                    account.display_name,
                )

        return True

    # -------------------------------------------------------------------------

    def cron_cleanup_shipments(self):
        """
        Archives delivered Mercado Libre shipments.
        """

        service = self._shipment_service()

        for account in self._accounts():

            try:

                service.cleanup_delivered_shipments(
                    account,
                )

                _logger.info(
                    "[SCE][ML] Delivered shipments archived (%s)",
                    account.display_name,
                )

            except Exception:

                _logger.exception(
                    "[SCE][ML] Shipment cleanup failed (%s)",
                    account.display_name,
                )

        return True

    # -------------------------------------------------------------------------
    # Logistics Synchronization
    # -------------------------------------------------------------------------

    def cron_sync_logistics(self):
        """
        Synchronizes logistics information for all pending shipments.
        """

        service = self._shipment_service()

        for account in self._accounts():

            try:

                shipments = self.env[
                    "sce.ml.shipment"
                ].search([
                    ("account_id", "=", account.id),
                    ("status", "not in", ("delivered", "cancelled")),
                ])

                for shipment in shipments:

                    service.synchronize_logistics(
                        shipment,
                    )

                _logger.info(
                    "[SCE][ML] Logistics synchronized (%s)",
                    account.display_name,
                )

            except Exception:

                _logger.exception(
                    "[SCE][ML] Logistics synchronization failed (%s)",
                    account.display_name,
                )

        return True

            # -------------------------------------------------------------------------
    # Authentication
    # -------------------------------------------------------------------------

    def cron_refresh_tokens(self):
        """
        Refreshes OAuth tokens for all connected accounts.
        """

        service = self._auth_service()

        for account in self._accounts():

            try:

                service.refresh_access_token(
                    account,
                )

                _logger.info(
                    "[SCE][ML] OAuth token refreshed (%s)",
                    account.display_name,
                )

            except Exception:

                _logger.exception(
                    "[SCE][ML] OAuth refresh failed (%s)",
                    account.display_name,
                )

        return True

    # -------------------------------------------------------------------------
    # Health Check
    # -------------------------------------------------------------------------

    def cron_health_check(self):
        """
        Executes connector health check.
        """

        product_service = self._product_service()
        order_service = self._order_service()
        shipment_service = self._shipment_service()

        for account in self._accounts():

            try:

                result = {

                    "products": product_service.health_check(
                        account,
                    ),

                    "orders": order_service.health_check(
                        account,
                    ),

                    "shipments": shipment_service.health_check(
                        account,
                    ),

                }

                _logger.info(
                    "[SCE][ML] Health Check (%s): %s",
                    account.display_name,
                    result,
                )

            except Exception:

                _logger.exception(
                    "[SCE][ML] Health Check failed (%s)",
                    account.display_name,
                )

        return True

    # -------------------------------------------------------------------------
    # Maintenance
    # -------------------------------------------------------------------------

    def cron_cleanup(self):
        """
        Executes connector maintenance.
        """

        for account in self._accounts():

            try:

                self._order_service().cleanup_cancelled_orders(
                    account,
                )

                self._shipment_service().cleanup_delivered_shipments(
                    account,
                )

                _logger.info(
                    "[SCE][ML] Cleanup finished (%s)",
                    account.display_name,
                )

            except Exception:

                _logger.exception(
                    "[SCE][ML] Cleanup failed (%s)",
                    account.display_name,
                )

        return True

    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    def cron_statistics(self):
        """
        Generates synchronization statistics.
        """

        for account in self._accounts():

            try:

                product_stats = self._product_service().statistics(
                    account,
                )

                order_stats = self._order_service().statistics(
                    account,
                )

                shipment_stats = self._shipment_service().statistics(
                    account,
                )

                account.message_post(
                    body=(
                        "<b>Synchronization Statistics</b><br/><br/>"

                        "<b>Products</b><br/>"
                        f"{product_stats}<br/><br/>"

                        "<b>Orders</b><br/>"
                        f"{order_stats}<br/><br/>"

                        "<b>Shipments</b><br/>"
                        f"{shipment_stats}"
                    )
                )

            except Exception:

                _logger.exception(
                    "[SCE][ML] Statistics failed (%s)",
                    account.display_name,
                )

        return True

    # -------------------------------------------------------------------------
    # Master Scheduler
    # -------------------------------------------------------------------------

    def cron_all(self):
        """
        Executes the complete Mercado Libre synchronization cycle.
        """

        _logger.info(
            "[SCE][ML] Starting synchronization cycle..."
        )

        self.cron_refresh_tokens()

        self.cron_import_products()
        self.cron_sync_products()

        self.cron_import_orders()
        self.cron_sync_orders()

        self.cron_import_shipments()
        self.cron_sync_shipments()

        self.cron_health_check()

        self.cron_statistics()

        _logger.info(
            "[SCE][ML] Synchronization cycle finished."
        )

        return True