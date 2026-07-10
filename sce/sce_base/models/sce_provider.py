# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Base Provider
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from odoo import fields, models


class SCEProvider(models.AbstractModel, ABC):
    """
    Base provider for all marketplace integrations.
    """

    _name = "sce.provider"

    _description = "SCE Base Provider"

    # -------------------------------------------------------------------------
    # Identity
    # -------------------------------------------------------------------------

    provider_code = fields.Char(
        string="Provider Code",
        readonly=True,
    )

    provider_name = fields.Char(
        string="Provider",
        readonly=True,
    )

    provider_version = fields.Char(
        string="Version",
        readonly=True,
    )

    # -------------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------------

    def code(self):
        """
        Provider unique code.
        """

        raise NotImplementedError()

    # -------------------------------------------------------------------------

    def name(self):
        """
        Provider display name.
        """

        raise NotImplementedError()

    # -------------------------------------------------------------------------

    def version(self):
        """
        Provider version.
        """

        return "1.0.0"

    # -------------------------------------------------------------------------

    def description(self):

        return ""

    # -------------------------------------------------------------------------

    def author(self):

        return "Softwork"

    # -------------------------------------------------------------------------

    def website(self):

        return "https://swsistemas.com"

    # -------------------------------------------------------------------------
    # Connection
    # -------------------------------------------------------------------------

    @abstractmethod
    def test_connection(
        self,
        connector,
    ):
        """
        Tests provider connectivity.
        """

    # -------------------------------------------------------------------------

    @abstractmethod
    def health_check(
        self,
        connector,
    ):
        """
        Executes provider diagnostics.
        """

    # -------------------------------------------------------------------------

    @abstractmethod
    def synchronize(
        self,
        connector,
    ):
        """
        Executes synchronization.
        """

            # -------------------------------------------------------------------------
    # Products
    # -------------------------------------------------------------------------

    @abstractmethod
    def import_products(
        self,
        account,
    ):
        """
        Imports products from the marketplace.
        """

    # -------------------------------------------------------------------------

    @abstractmethod
    def export_products(
        self,
        account,
    ):
        """
        Exports products to the marketplace.
        """

    # -------------------------------------------------------------------------

    @abstractmethod
    def update_product(
        self,
        publication,
    ):
        """
        Updates a published product.
        """

    # -------------------------------------------------------------------------

    @abstractmethod
    def delete_product(
        self,
        publication,
    ):
        """
        Removes a product from the marketplace.
        """

    # -------------------------------------------------------------------------

    @abstractmethod
    def synchronize_stock(
        self,
        account,
    ):
        """
        Synchronizes product stock.
        """

    # -------------------------------------------------------------------------

    @abstractmethod
    def synchronize_prices(
        self,
        account,
    ):
        """
        Synchronizes product prices.
        """

    # -------------------------------------------------------------------------

    @abstractmethod
    def synchronize_publications(
        self,
        account,
    ):
        """
        Synchronizes marketplace publications.
        """

    # -------------------------------------------------------------------------

    @abstractmethod
    def import_categories(
        self,
        account,
    ):
        """
        Imports marketplace categories.
        """

    # -------------------------------------------------------------------------

    @abstractmethod
    def import_attributes(
        self,
        account,
    ):
        """
        Imports marketplace attributes.
        """

    # -------------------------------------------------------------------------

    @abstractmethod
    def upload_images(
        self,
        publication,
    ):
        """
        Uploads product images.
        """

    # -------------------------------------------------------------------------

    @abstractmethod
    def remove_images(
        self,
        publication,
    ):
        """
        Removes product images.
        """

            # -------------------------------------------------------------------------
    # Orders
    # -------------------------------------------------------------------------

    @abstractmethod
    def import_orders(
        self,
        account,
    ):
        """
        Imports orders from marketplace.
        """

    # -------------------------------------------------------------------------

    @abstractmethod
    def synchronize_orders(
        self,
        account,
    ):
        """
        Synchronizes existing orders.
        """

    # -------------------------------------------------------------------------

    @abstractmethod
    def update_order_status(
        self,
        order,
    ):
        """
        Updates marketplace order status.
        """

    # -------------------------------------------------------------------------

    @abstractmethod
    def cancel_order(
        self,
        order,
    ):
        """
        Cancels a marketplace order.
        """

    # -------------------------------------------------------------------------

    @abstractmethod
    def refund_order(
        self,
        order,
    ):
        """
        Processes order refund.
        """

    # -------------------------------------------------------------------------
    # Shipments
    # -------------------------------------------------------------------------

    @abstractmethod
    def import_shipments(
        self,
        account,
    ):
        """
        Imports shipments.
        """

    # -------------------------------------------------------------------------

    @abstractmethod
    def synchronize_shipments(
        self,
        account,
    ):
        """
        Synchronizes shipment information.
        """

    # -------------------------------------------------------------------------

    @abstractmethod
    def update_tracking(
        self,
        shipment,
    ):
        """
        Updates tracking information.
        """

    # -------------------------------------------------------------------------

    @abstractmethod
    def print_shipping_label(
        self,
        shipment,
    ):
        """
        Generates shipping label.
        """

    # -------------------------------------------------------------------------
    # Customer Communication
    # -------------------------------------------------------------------------

    @abstractmethod
    def import_messages(
        self,
        account,
    ):
        """
        Imports customer messages.
        """

    # -------------------------------------------------------------------------

    @abstractmethod
    def send_message(
        self,
        message,
    ):
        """
        Sends a message to marketplace customer.
        """

    # -------------------------------------------------------------------------

    @abstractmethod
    def import_questions(
        self,
        account,
    ):
        """
        Imports marketplace questions.
        """

    # -------------------------------------------------------------------------

    @abstractmethod
    def answer_question(
        self,
        question,
    ):
        """
        Answers marketplace question.
        """

    # -------------------------------------------------------------------------
    # Returns
    # -------------------------------------------------------------------------

    @abstractmethod
    def import_returns(
        self,
        account,
    ):
        """
        Imports returns.
        """

    # -------------------------------------------------------------------------

    @abstractmethod
    def synchronize_returns(
        self,
        account,
    ):
        """
        Synchronizes return status.
        """

            # -------------------------------------------------------------------------
    # Payments
    # -------------------------------------------------------------------------

    @abstractmethod
    def import_payments(
        self,
        account,
    ):
        """
        Imports payment information.
        """

    # -------------------------------------------------------------------------

    @abstractmethod
    def synchronize_payments(
        self,
        account,
    ):
        """
        Synchronizes payment status.
        """

    # -------------------------------------------------------------------------
    # Billing
    # -------------------------------------------------------------------------

    @abstractmethod
    def create_invoice(
        self,
        order,
    ):
        """
        Creates invoice information.
        """

    # -------------------------------------------------------------------------

    @abstractmethod
    def synchronize_invoices(
        self,
        account,
    ):
        """
        Synchronizes invoice information.
        """

    # -------------------------------------------------------------------------
    # Webhooks
    # -------------------------------------------------------------------------

    @abstractmethod
    def register_webhooks(
        self,
        account,
    ):
        """
        Registers marketplace webhooks.
        """

    # -------------------------------------------------------------------------

    @abstractmethod
    def process_webhook(
        self,
        webhook,
    ):
        """
        Processes incoming webhook.
        """

    # -------------------------------------------------------------------------
    # Synchronization
    # -------------------------------------------------------------------------

    def synchronize_all(
        self,
        account,
    ):
        """
        Executes full synchronization.

        Providers can override this method
        if they require custom behavior.
        """

        return {

            "products":
                self.synchronize_products(account),

            "orders":
                self.synchronize_orders(account),

            "shipments":
                self.synchronize_shipments(account),

            "payments":
                self.synchronize_payments(account),

        }

    # -------------------------------------------------------------------------
    # Capabilities
    # -------------------------------------------------------------------------

    def capabilities(self):
        """
        Returns provider capabilities.
        """

        return [

            "products",
            "orders",
            "shipments",

        ]

    # -------------------------------------------------------------------------
    # Configuration
    # -------------------------------------------------------------------------

    def get_configuration_schema(self):
        """
        Returns provider configuration fields.
        """

        return {}

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def log(
        self,
        level,
        message,
        **kwargs,
    ):
        """
        Provider logging helper.
        """

        self.env["sce.log"].create({

            "level": level,

            "message": message,

            **kwargs,

        })

    # -------------------------------------------------------------------------

    def create_job(
        self,
        account,
        job_type,
        payload=None,
    ):
        """
        Creates synchronization job.
        """

        return self.env["sce.job"].create({

            "account_id":
                account.id,

            "type":
                job_type,

            "payload":
                payload or {},

        })

    # -------------------------------------------------------------------------

    def create_queue_item(
        self,
        account,
        action,
        payload=None,
    ):
        """
        Creates queue entry.
        """

        return self.env["sce.queue"].create({

            "account_id":
                account.id,

            "action":
                action,

            "payload":
                payload or {},

        })