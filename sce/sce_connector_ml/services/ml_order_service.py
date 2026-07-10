# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Mercado Libre Order Service
"""

from __future__ import annotations

from typing import Any

from odoo import fields


class MLOrderService:
    """
    Business logic for Mercado Libre orders.
    """

    def __init__(self, env) -> None:
        self.env = env
        self.auth_service = env["sce.ml.auth.service"]

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def import_order(
        self,
        ml_order,
    ):
        """
        Imports a Mercado Libre order into Odoo.
        """

        client = self.auth_service.api_client(
            ml_order.account_id,
        )

        data = client.get_order(
            ml_order.order_id,
        )

        sale_order = self._create_sale_order(
            ml_order,
            data,
        )

        ml_order.write({
            "sale_order_id": sale_order.id,
            "partner_id": sale_order.partner_id.id,
            "status": data.get("status"),
            "payment_status": data.get("payments", [{}])[0].get(
                "status"
            ),
            "shipping_status": data.get(
                "shipping",
                {},
            ).get(
                "status"
            ),
            "total_amount": data.get("total_amount"),
            "paid_amount": data.get("paid_amount"),
            "currency_id": data.get("currency_id"),
            "last_sync_at": fields.Datetime.now(),
            "sync_status": "success",
            "last_error": False,
            "raw_data": data,
        })

        return sale_order

    # -------------------------------------------------------------------------

    def synchronize_order(
        self,
        ml_order,
    ):
        """
        Synchronizes a Mercado Libre order.
        """

        client = self.auth_service.api_client(
            ml_order.account_id,
        )

        data = client.get_order(
            ml_order.order_id,
        )

        self.update_order_status(
            ml_order,
            data=data,
        )

        self.update_payment_status(
            ml_order,
            data=data,
        )

        self.update_shipping_status(
            ml_order,
            data=data,
        )

        ml_order.write({
            "last_sync_at": fields.Datetime.now(),
            "sync_status": "success",
            "last_error": False,
            "raw_data": data,
        })

        return ml_order

    # -------------------------------------------------------------------------

    def import_orders(
        self,
        account,
        offset: int = 0,
        limit: int = 50,
    ):
        """
        Imports a batch of Mercado Libre orders.
        """

        client = self.auth_service.api_client(
            account,
        )

        response = client.get_orders(
            offset=offset,
            limit=limit,
        )

        results = self.env["sce.ml.order"]

        for item in response.get("results", []):

            order = self._find_or_create_order(
                account,
                item,
            )

            self.import_order(
                order,
            )

            results |= order

        return results

    # -------------------------------------------------------------------------

    def synchronize_orders(
        self,
        account,
    ):
        """
        Synchronizes every imported order.
        """

        orders = self.env[
            "sce.ml.order"
        ].search([
            ("account_id", "=", account.id),
        ])

        for order in orders:
            self.synchronize_order(
                order,
            )

        return orders

    # -------------------------------------------------------------------------
    # Internal
    # -------------------------------------------------------------------------

    def _find_or_create_order(
        self,
        account,
        data: dict[str, Any],
    ):
        """
        Finds or creates the integration record.
        """

        order = self.env[
            "sce.ml.order"
        ].search([
            ("order_id", "=", str(data["id"])),
        ], limit=1)

        if order:
            return order

        return self.env[
            "sce.ml.order"
        ].create({
            "account_id": account.id,
            "order_id": str(data["id"]),
            "buyer_id": str(
                data.get(
                    "buyer",
                    {},
                ).get("id", "")
            ),
            "buyer_nickname": data.get(
                "buyer",
                {},
            ).get(
                "nickname"
            ),
            "status": data.get("status"),
            "date_created": data.get(
                "date_created"
            ),
        })

            # -------------------------------------------------------------------------
    # Sale Order
    # -------------------------------------------------------------------------

    def _create_sale_order(
        self,
        ml_order,
        data: dict[str, Any],
    ):
        """
        Creates or updates the Sale Order.
        """

        if ml_order.sale_order_id:

            sale_order = ml_order.sale_order_id

            sale_order.order_line.unlink()

        else:

            partner = self._find_partner(
                ml_order,
                data,
            )

            sale_order = self.env[
                "sale.order"
            ].create({
                "partner_id": partner.id,
                "company_id": ml_order.company_id.id,
                "client_order_ref": ml_order.order_id,
                "origin": f"Mercado Libre {ml_order.order_id}",
            })

        self._create_order_lines(
            sale_order,
            data,
        )

        return sale_order

    # -------------------------------------------------------------------------

    def _create_order_lines(
        self,
        sale_order,
        data: dict[str, Any],
    ):
        """
        Creates Sale Order lines.
        """

        SaleOrderLine = self.env[
            "sale.order.line"
        ]

        for item in data.get(
            "order_items",
            [],
        ):

            product = self._find_product(
                item,
            )

            SaleOrderLine.create({

                "order_id": sale_order.id,

                "product_id": product.id,

                "name": item.get(
                    "item",
                    {},
                ).get(
                    "title",
                    product.display_name,
                ),

                "product_uom_qty": item.get(
                    "quantity",
                    1,
                ),

                "price_unit": item.get(
                    "unit_price",
                    0.0,
                ),

            })

    # -------------------------------------------------------------------------

    def _find_product(
        self,
        item: dict[str, Any],
    ):
        """
        Finds the corresponding Odoo product.
        """

        item_id = item.get(
            "item",
            {},
        ).get(
            "id"
        )

        publication = self.env[
            "sce.ml.publication"
        ].search(
            [
                ("item_id", "=", item_id),
            ],
            limit=1,
        )

        if publication:

            variant = publication.product_tmpl_id.product_variant_id

            if variant:

                return variant

        seller_sku = None

        for attribute in item.get(
            "item",
            {},
        ).get(
            "attributes",
            [],
        ):

            if attribute.get("id") == "SELLER_SKU":

                seller_sku = attribute.get(
                    "value_name"
                )

                break

        if seller_sku:

            product = self.env[
                "product.product"
            ].search(
                [
                    ("default_code", "=", seller_sku),
                ],
                limit=1,
            )

            if product:

                return product

        raise ValueError(
            f"Product not found for Mercado Libre item {item_id}"
        )

    # -------------------------------------------------------------------------

    def _update_sale_order(
        self,
        sale_order,
        data: dict[str, Any],
    ):
        """
        Updates an existing Sale Order.
        """

        sale_order.write({

            "client_order_ref": str(
                data.get("id")
            ),

            "note": data.get(
                "tags",
                [],
            ) and ", ".join(
                data.get(
                    "tags",
                    [],
                )
            ) or False,

        })

        sale_order.order_line.unlink()

        self._create_order_lines(
            sale_order,
            data,
        )

        return sale_order

            # -------------------------------------------------------------------------
    # Partner
    # -------------------------------------------------------------------------

    def _find_partner(
        self,
        ml_order,
        data: dict[str, Any],
    ):
        """
        Finds or creates the customer.
        """

        buyer = data.get(
            "buyer",
            {},
        )

        partner = self.env[
            "res.partner"
        ].search(
            [
                ("x_ml_buyer_id", "=", str(buyer.get("id"))),
            ],
            limit=1,
        )

        if partner:

            self._update_partner(
                partner,
                buyer,
            )

            return partner

        return self._create_partner(
            ml_order,
            buyer,
        )

    # -------------------------------------------------------------------------

    def _create_partner(
        self,
        ml_order,
        buyer: dict[str, Any],
    ):
        """
        Creates a new customer.
        """

        values = {

            "name": buyer.get(
                "nickname"
            )
            or buyer.get("first_name")
            or "Mercado Libre Customer",

            "company_id": ml_order.company_id.id,

            "email": buyer.get("email"),

            "phone": buyer.get("phone"),

            "mobile": buyer.get("alternative_phone"),

            "customer_rank": 1,

            "x_ml_buyer_id": str(
                buyer.get("id")
            ),

        }

        partner = self.env[
            "res.partner"
        ].create(
            values
        )

        return partner

    # -------------------------------------------------------------------------

    def _update_partner(
        self,
        partner,
        buyer: dict[str, Any],
    ):
        """
        Updates customer information.
        """

        values = {}

        if buyer.get("email"):

            values["email"] = buyer.get(
                "email"
            )

        if buyer.get("phone"):

            values["phone"] = buyer.get(
                "phone"
            )

        if buyer.get("alternative_phone"):

            values["mobile"] = buyer.get(
                "alternative_phone"
            )

        if buyer.get("nickname"):

            values["name"] = buyer.get(
                "nickname"
            )

        if values:

            partner.write(
                values
            )

        return partner

    # -------------------------------------------------------------------------
    # Shipping Address
    # -------------------------------------------------------------------------

    def _create_shipping_partner(
        self,
        partner,
        shipping: dict[str, Any],
    ):
        """
        Creates or updates the delivery address.
        """

        receiver = shipping.get(
            "receiver_address",
            {},
        )

        address = self.env[
            "res.partner"
        ].search(
            [
                ("parent_id", "=", partner.id),
                ("type", "=", "delivery"),
                (
                    "street",
                    "=",
                    receiver.get(
                        "address_line",
                        "",
                    ),
                ),
            ],
            limit=1,
        )

        values = {

            "parent_id": partner.id,

            "type": "delivery",

            "name": receiver.get(
                "receiver_name"
            )
            or partner.name,

            "street": receiver.get(
                "address_line"
            ),

            "city": receiver.get(
                "city",
                {},
            ).get(
                "name"
            ),

            "zip": receiver.get(
                "zip_code"
            ),

            "phone": receiver.get(
                "receiver_phone"
            ),

        }

        if address:

            address.write(
                values
            )

            return address

        return self.env[
            "res.partner"
        ].create(
            values
        )

    # -------------------------------------------------------------------------
    # Buyer Helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _buyer_name(
        buyer: dict[str, Any],
    ) -> str:
        """
        Returns the buyer display name.
        """

        if buyer.get("nickname"):
            return buyer["nickname"]

        full_name = " ".join(
            filter(
                None,
                [
                    buyer.get("first_name"),
                    buyer.get("last_name"),
                ],
            )
        )

        if full_name:

            return full_name

        return "Mercado Libre Customer"

    @staticmethod
    def _buyer_email(
        buyer: dict[str, Any],
    ) -> str | None:
        """
        Returns buyer email.
        """

        return buyer.get("email")

    @staticmethod
    def _buyer_phone(
        buyer: dict[str, Any],
    ) -> str | None:
        """
        Returns buyer phone.
        """

        return (
            buyer.get("phone")
            or buyer.get("alternative_phone")
        )

            # -------------------------------------------------------------------------
    # Order Status
    # -------------------------------------------------------------------------

    def update_order_status(
        self,
        ml_order,
        data: dict[str, Any] | None = None,
    ):
        """
        Updates the order status.
        """

        if data is None:

            client = self.auth_service.api_client(
                ml_order.account_id,
            )

            data = client.get_order(
                ml_order.order_id,
            )

        ml_order.write({
            "status": data.get("status"),
            "last_sync_at": fields.Datetime.now(),
        })

        if ml_order.sale_order_id:

            sale_order = ml_order.sale_order_id

            if (
                data.get("status") == "cancelled"
                and sale_order.state not in ("cancel",)
            ):
                sale_order.action_cancel()

        return ml_order

    # -------------------------------------------------------------------------
    # Payment
    # -------------------------------------------------------------------------

    def update_payment_status(
        self,
        ml_order,
        data: dict[str, Any] | None = None,
    ):
        """
        Updates payment information.
        """

        if data is None:

            client = self.auth_service.api_client(
                ml_order.account_id,
            )

            data = client.get_order(
                ml_order.order_id,
            )

        payment = {}

        payments = data.get(
            "payments",
            [],
        )

        if payments:

            payment = payments[0]

        ml_order.write({

            "payment_status": payment.get(
                "status"
            ),

            "paid_amount": payment.get(
                "total_paid_amount",
                payment.get(
                    "transaction_amount",
                    0.0,
                ),
            ),

            "last_sync_at": fields.Datetime.now(),

        })

        return payment

    # -------------------------------------------------------------------------
    # Shipping
    # -------------------------------------------------------------------------

    def update_shipping_status(
        self,
        ml_order,
        data: dict[str, Any] | None = None,
    ):
        """
        Updates shipping information.
        """

        if data is None:

            client = self.auth_service.api_client(
                ml_order.account_id,
            )

            data = client.get_order(
                ml_order.order_id,
            )

        shipping = data.get(
            "shipping",
            {},
        )

        ml_order.write({

            "shipping_id": str(
                shipping.get("id", "")
            ),

            "shipping_status": shipping.get(
                "status"
            ),

            "last_sync_at": fields.Datetime.now(),

        })

        return shipping

    # -------------------------------------------------------------------------
    # Shipment
    # -------------------------------------------------------------------------

    def synchronize_shipment(
        self,
        ml_order,
    ):
        """
        Synchronizes shipment details.
        """

        if not ml_order.shipping_id:
            return {}

        client = self.auth_service.api_client(
            ml_order.account_id,
        )

        shipment = client.get_shipment(
            ml_order.shipping_id,
        )

        ml_order.write({

            "shipping_status": shipment.get(
                "status"
            ),

            "last_sync_at": fields.Datetime.now(),

        })

        return shipment

    # -------------------------------------------------------------------------
    # Payment Details
    # -------------------------------------------------------------------------

    def synchronize_payments(
        self,
        ml_order,
    ):
        """
        Synchronizes payment information.
        """

        client = self.auth_service.api_client(
            ml_order.account_id,
        )

        payments = client.get_order_payments(
            ml_order.order_id,
        )

        if payments:

            payment = payments[0]

            ml_order.write({

                "payment_status": payment.get(
                    "status"
                ),

                "paid_amount": payment.get(
                    "total_paid_amount",
                    0.0,
                ),

                "last_sync_at": fields.Datetime.now(),

            })

        return payments

    # -------------------------------------------------------------------------
    # Full Status Synchronization
    # -------------------------------------------------------------------------

    def synchronize_status(
        self,
        ml_order,
    ):
        """
        Synchronizes order, payment and shipment status.
        """

        client = self.auth_service.api_client(
            ml_order.account_id,
        )

        data = client.get_order(
            ml_order.order_id,
        )

        self.update_order_status(
            ml_order,
            data=data,
        )

        self.update_payment_status(
            ml_order,
            data=data,
        )

        self.update_shipping_status(
            ml_order,
            data=data,
        )

        ml_order.write({

            "sync_status": "success",

            "last_sync_at": fields.Datetime.now(),

            "last_error": False,

        })

        return ml_order

            # -------------------------------------------------------------------------
    # Batch Import
    # -------------------------------------------------------------------------

    def import_recent_orders(
        self,
        account,
        days: int = 7,
    ):
        """
        Imports recent orders.
        """

        client = self.auth_service.api_client(
            account,
        )

        response = client.get_recent_orders(
            days=days,
        )

        orders = self.env["sce.ml.order"]

        for data in response.get("results", []):

            order = self._find_or_create_order(
                account,
                data,
            )

            self.import_order(
                order,
            )

            orders |= order

        return orders

    # -------------------------------------------------------------------------

    def import_pending_orders(
        self,
        account,
    ):
        """
        Imports pending orders.
        """

        client = self.auth_service.api_client(
            account,
        )

        response = client.get_orders(
            status="paid",
        )

        orders = self.env["sce.ml.order"]

        for data in response.get("results", []):

            order = self._find_or_create_order(
                account,
                data,
            )

            self.import_order(
                order,
            )

            orders |= order

        return orders

    # -------------------------------------------------------------------------

    def synchronize_pending_orders(
        self,
        account,
    ):
        """
        Synchronizes pending orders.
        """

        orders = self.env[
            "sce.ml.order"
        ].search([
            ("account_id", "=", account.id),
            ("status", "!=", "cancelled"),
        ])

        for order in orders:

            self.synchronize_order(
                order,
            )

        return orders

    # -------------------------------------------------------------------------
    # Search Helpers
    # -------------------------------------------------------------------------

    def find_order(
        self,
        account,
        order_id: str,
    ):
        """
        Finds an imported order.
        """

        return self.env[
            "sce.ml.order"
        ].search(
            [
                ("account_id", "=", account.id),
                ("order_id", "=", str(order_id)),
            ],
            limit=1,
        )

    # -------------------------------------------------------------------------

    def exists(
        self,
        account,
        order_id: str,
    ) -> bool:
        """
        Returns True if the order exists.
        """

        return bool(
            self.find_order(
                account,
                order_id,
            )
        )

    # -------------------------------------------------------------------------

    def get_sale_order(
        self,
        account,
        order_id: str,
    ):
        """
        Returns the Sale Order linked to a Mercado Libre order.
        """

        order = self.find_order(
            account,
            order_id,
        )

        return order.sale_order_id if order else False

    # -------------------------------------------------------------------------
    # Retry
    # -------------------------------------------------------------------------

    def retry_failed_orders(
        self,
        account,
    ):
        """
        Retries failed synchronizations.
        """

        orders = self.env[
            "sce.ml.order"
        ].search([
            ("account_id", "=", account.id),
            ("sync_status", "=", "error"),
        ])

        for order in orders:

            try:

                self.import_order(
                    order,
                )

            except Exception as exc:

                order.write({
                    "last_error": str(exc),
                })

        return orders

    # -------------------------------------------------------------------------
    # Maintenance
    # -------------------------------------------------------------------------

    def cleanup_cancelled_orders(
        self,
        account,
    ):
        """
        Archives cancelled orders.
        """

        orders = self.env[
            "sce.ml.order"
        ].search([
            ("account_id", "=", account.id),
            ("status", "=", "cancelled"),
            ("active", "=", True),
        ])

        orders.write({
            "active": False,
        })

        return orders

    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    def statistics(
        self,
        account,
    ):
        """
        Returns synchronization statistics.
        """

        Order = self.env["sce.ml.order"]

        return {

            "orders": Order.search_count([
                ("account_id", "=", account.id),
            ]),

            "success": Order.search_count([
                ("account_id", "=", account.id),
                ("sync_status", "=", "success"),
            ]),

            "errors": Order.search_count([
                ("account_id", "=", account.id),
                ("sync_status", "=", "error"),
            ]),

            "pending": Order.search_count([
                ("account_id", "=", account.id),
                ("sync_status", "=", "pending"),
            ]),
        }

            # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    @staticmethod
    def validate_order(
        data: dict[str, Any],
    ) -> None:
        """
        Validates the minimum information required to import an order.
        """

        if not data.get("id"):
            raise ValueError(
                "Order ID is required."
            )

        if not data.get("buyer"):
            raise ValueError(
                "Buyer information is required."
            )

        if not data.get("order_items"):
            raise ValueError(
                "Order items are required."
            )

    # -------------------------------------------------------------------------
    # Batch Operations
    # -------------------------------------------------------------------------

    def import_batch(
        self,
        account,
        orders: list[dict[str, Any]],
    ):
        """
        Imports a batch of orders already retrieved from the API.
        """

        imported = self.env["sce.ml.order"]

        for data in orders:

            self.validate_order(
                data,
            )

            order = self._find_or_create_order(
                account,
                data,
            )

            self.import_order(
                order,
            )

            imported |= order

        return imported

    # -------------------------------------------------------------------------

    def synchronize_batch(
        self,
        orders,
    ):
        """
        Synchronizes a batch of imported orders.
        """

        for order in orders:

            self.synchronize_order(
                order,
            )

        return orders

    # -------------------------------------------------------------------------
    # Utilities
    # -------------------------------------------------------------------------

    @staticmethod
    def is_paid(
        ml_order,
    ) -> bool:
        """
        Returns True if the order has been paid.
        """

        return ml_order.payment_status in (
            "approved",
            "paid",
            "accredited",
        )

    @staticmethod
    def is_cancelled(
        ml_order,
    ) -> bool:
        """
        Returns True if the order is cancelled.
        """

        return ml_order.status == "cancelled"

    @staticmethod
    def has_shipping(
        ml_order,
    ) -> bool:
        """
        Returns True if the order has shipping information.
        """

        return bool(
            ml_order.shipping_id
        )

    # -------------------------------------------------------------------------
    # Diagnostics
    # -------------------------------------------------------------------------

    def ping(
        self,
        account,
    ) -> bool:
        """
        Checks whether the Mercado Libre Orders API is reachable.
        """

        try:

            client = self.auth_service.api_client(
                account,
            )

            client.get_orders(
                limit=1,
            )

            return True

        except Exception:

            return False

    # -------------------------------------------------------------------------
    # Maintenance
    # -------------------------------------------------------------------------

    def recalculate_statistics(
        self,
        account,
    ):
        """
        Recalculates order statistics.
        """

        stats = self.statistics(
            account,
        )

        account.message_post(
            body=(
                "Mercado Libre synchronization statistics:"
                "<br/>"
                f"Orders: {stats['orders']}<br/>"
                f"Success: {stats['success']}<br/>"
                f"Pending: {stats['pending']}<br/>"
                f"Errors: {stats['errors']}"
            )
        )

        return stats

    # -------------------------------------------------------------------------
    # Health Check
    # -------------------------------------------------------------------------

    def health_check(
        self,
        account,
    ):
        """
        Performs a service health check.
        """

        return {
            "api": self.ping(
                account,
            ),
            "orders": self.statistics(
                account,
            ),
        }