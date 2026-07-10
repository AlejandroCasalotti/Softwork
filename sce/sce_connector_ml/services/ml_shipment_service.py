# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Mercado Libre Shipment Service
"""

from __future__ import annotations

from typing import Any

from odoo import fields


class MLShipmentService:
    """
    Business logic for Mercado Libre shipments.
    """

    def __init__(self, env) -> None:
        self.env = env
        self.auth_service = env["sce.ml.auth.service"]

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def import_shipment(
        self,
        shipment,
    ):
        """
        Imports a Mercado Libre shipment.
        """

        client = self.auth_service.api_client(
            shipment.account_id,
        )

        data = client.get_shipment(
            shipment.shipment_id,
        )

        self._update_shipment(
            shipment,
            data,
        )

        self._link_picking(
            shipment,
        )

        return shipment

    # -------------------------------------------------------------------------

    def synchronize_shipment(
        self,
        shipment,
    ):
        """
        Synchronizes shipment information.
        """

        client = self.auth_service.api_client(
            shipment.account_id,
        )

        data = client.get_shipment(
            shipment.shipment_id,
        )

        self._update_shipment(
            shipment,
            data,
        )

        return shipment

    # -------------------------------------------------------------------------

    def import_shipments(
        self,
        account,
        limit: int = 50,
        offset: int = 0,
    ):
        """
        Imports shipments from Mercado Libre.
        """

        client = self.auth_service.api_client(
            account,
        )

        response = client.get_shipments(
            limit=limit,
            offset=offset,
        )

        shipments = self.env[
            "sce.ml.shipment"
        ]

        for item in response.get(
            "results",
            [],
        ):

            shipment = self._find_or_create(
                account,
                item,
            )

            self.import_shipment(
                shipment,
            )

            shipments |= shipment

        return shipments

    # -------------------------------------------------------------------------

    def synchronize_shipments(
        self,
        account,
    ):
        """
        Synchronizes all imported shipments.
        """

        shipments = self.env[
            "sce.ml.shipment"
        ].search([
            ("account_id", "=", account.id),
        ])

        for shipment in shipments:

            self.synchronize_shipment(
                shipment,
            )

        return shipments

    # -------------------------------------------------------------------------
    # Internal
    # -------------------------------------------------------------------------

    def _find_or_create(
        self,
        account,
        data: dict[str, Any],
    ):
        """
        Finds or creates a shipment.
        """

        shipment = self.env[
            "sce.ml.shipment"
        ].search([
            (
                "shipment_id",
                "=",
                str(data["id"]),
            ),
        ], limit=1)

        if shipment:
            return shipment

        order = self.env[
            "sce.ml.order"
        ].search([
            (
                "shipping_id",
                "=",
                str(data["id"]),
            ),
        ], limit=1)

        return self.env[
            "sce.ml.shipment"
        ].create({

            "account_id": account.id,

            "order_id": order.id,

            "shipment_id": str(
                data["id"]
            ),

            "status": data.get(
                "status"
            ),

            "date_created": data.get(
                "date_created"
            ),

        })

            # -------------------------------------------------------------------------
    # Shipment Update
    # -------------------------------------------------------------------------

    def _update_shipment(
        self,
        shipment,
        data: dict[str, Any],
    ):
        """
        Updates shipment information.
        """

        receiver = data.get(
            "receiver_address",
            {},
        )

        shipment.write({

            "status": data.get(
                "status"
            ),

            "substatus": data.get(
                "substatus"
            ),

            "shipping_mode": data.get(
                "shipping_mode"
            ),

            "logistic_type": data.get(
                "logistic_type"
            ),

            "tracking_number": data.get(
                "tracking_number"
            ),

            "tracking_method": data.get(
                "tracking_method"
            ),

            "receiver_name": receiver.get(
                "receiver_name"
            ),

            "receiver_phone": receiver.get(
                "receiver_phone"
            ),

            "street": receiver.get(
                "address_line"
            ),

            "city": receiver.get(
                "city",
                {},
            ).get(
                "name"
            ),

            "state": receiver.get(
                "state",
                {},
            ).get(
                "name"
            ),

            "zip": receiver.get(
                "zip_code"
            ),

            "country": receiver.get(
                "country",
                {},
            ).get(
                "name"
            ),

            "date_shipped": data.get(
                "date_shipped"
            ),

            "date_delivered": data.get(
                "date_delivered"
            ),

            "last_sync_at": fields.Datetime.now(),

            "sync_status": "success",

            "last_error": False,

            "raw_data": data,

        })

        return shipment

    # -------------------------------------------------------------------------
    # Tracking
    # -------------------------------------------------------------------------

    def update_tracking(
        self,
        shipment,
    ):
        """
        Updates shipment tracking information.
        """

        client = self.auth_service.api_client(
            shipment.account_id,
        )

        data = client.get_shipment(
            shipment.shipment_id,
        )

        shipment.write({

            "tracking_number": data.get(
                "tracking_number"
            ),

            "tracking_method": data.get(
                "tracking_method"
            ),

            "status": data.get(
                "status"
            ),

            "substatus": data.get(
                "substatus"
            ),

            "last_sync_at": fields.Datetime.now(),

        })

        return shipment

    # -------------------------------------------------------------------------
    # Receiver Address
    # -------------------------------------------------------------------------

    def update_receiver(
        self,
        shipment,
    ):
        """
        Updates receiver information.
        """

        client = self.auth_service.api_client(
            shipment.account_id,
        )

        data = client.get_shipment(
            shipment.shipment_id,
        )

        receiver = data.get(
            "receiver_address",
            {},
        )

        shipment.write({

            "receiver_name": receiver.get(
                "receiver_name"
            ),

            "receiver_phone": receiver.get(
                "receiver_phone"
            ),

            "street": receiver.get(
                "address_line"
            ),

            "city": receiver.get(
                "city",
                {},
            ).get(
                "name"
            ),

            "state": receiver.get(
                "state",
                {},
            ).get(
                "name"
            ),

            "zip": receiver.get(
                "zip_code"
            ),

            "country": receiver.get(
                "country",
                {},
            ).get(
                "name"
            ),

            "last_sync_at": fields.Datetime.now(),

        })

        return shipment

    # -------------------------------------------------------------------------
    # Shipment Dates
    # -------------------------------------------------------------------------

    def update_dates(
        self,
        shipment,
    ):
        """
        Updates shipment dates.
        """

        client = self.auth_service.api_client(
            shipment.account_id,
        )

        data = client.get_shipment(
            shipment.shipment_id,
        )

        shipment.write({

            "date_created": data.get(
                "date_created"
            ),

            "date_shipped": data.get(
                "date_shipped"
            ),

            "date_delivered": data.get(
                "date_delivered"
            ),

            "last_sync_at": fields.Datetime.now(),

        })

        return shipment

            # -------------------------------------------------------------------------
    # Stock Picking
    # -------------------------------------------------------------------------

    def _link_picking(
        self,
        shipment,
    ):
        """
        Links the shipment to the corresponding stock picking.
        """

        if shipment.picking_id:
            return shipment.picking_id

        if not shipment.sale_order_id:
            return False

        picking = self.env[
            "stock.picking"
        ].search(
            [
                ("sale_id", "=", shipment.sale_order_id.id),
                ("state", "!=", "cancel"),
            ],
            order="id desc",
            limit=1,
        )

        if picking:

            shipment.write({
                "picking_id": picking.id,
            })

        return picking

    # -------------------------------------------------------------------------

    def synchronize_picking(
        self,
        shipment,
    ):
        """
        Synchronizes the linked stock picking.
        """

        picking = self._link_picking(
            shipment,
        )

        if not picking:
            return False

        if shipment.tracking_number:

            picking.write({

                "carrier_tracking_ref": shipment.tracking_number,

            })

        return picking

    # -------------------------------------------------------------------------

    def update_picking_tracking(
        self,
        shipment,
    ):
        """
        Updates tracking number in stock picking.
        """

        picking = self._link_picking(
            shipment,
        )

        if not picking:
            return False

        if shipment.tracking_number:

            picking.write({

                "carrier_tracking_ref": shipment.tracking_number,

            })

        return picking

    # -------------------------------------------------------------------------

    def validate_picking(
        self,
        shipment,
    ):
        """
        Validates the stock picking when shipment is shipped.
        """

        picking = self._link_picking(
            shipment,
        )

        if not picking:
            return False

        if (
            shipment.status == "shipped"
            and picking.state == "assigned"
        ):

            picking.button_validate()

        return picking

    # -------------------------------------------------------------------------

    def complete_picking(
        self,
        shipment,
    ):
        """
        Completes the stock picking when shipment is delivered.
        """

        picking = self._link_picking(
            shipment,
        )

        if not picking:
            return False

        if (
            shipment.status == "delivered"
            and picking.state not in (
                "done",
                "cancel",
            )
        ):

            picking.button_validate()

        return picking

    # -------------------------------------------------------------------------

    def synchronize_inventory(
        self,
        shipment,
    ):
        """
        Synchronizes shipment with Odoo inventory.
        """

        picking = self._link_picking(
            shipment,
        )

        if not picking:
            return False

        self.update_picking_tracking(
            shipment,
        )

        self.validate_picking(
            shipment,
        )

        self.complete_picking(
            shipment,
        )

        return picking

            # -------------------------------------------------------------------------
    # Tracking History
    # -------------------------------------------------------------------------

    def get_tracking(
        self,
        shipment,
    ):
        """
        Returns shipment tracking information.
        """

        client = self.auth_service.api_client(
            shipment.account_id,
        )

        return client.get_shipment(
            shipment.shipment_id,
        )

    # -------------------------------------------------------------------------

    def get_tracking_history(
        self,
        shipment,
    ):
        """
        Returns shipment tracking history.
        """

        client = self.auth_service.api_client(
            shipment.account_id,
        )

        return client.get_tracking_history(
            shipment.shipment_id,
        )

    # -------------------------------------------------------------------------

    def synchronize_tracking_history(
        self,
        shipment,
    ):
        """
        Synchronizes shipment tracking history.
        """

        history = self.get_tracking_history(
            shipment,
        )

        shipment.message_post(
            body=(
                "<b>Tracking synchronized.</b><br/>"
                f"Events: {len(history.get('events', []))}"
            )
        )

        return history

    # -------------------------------------------------------------------------
    # Carrier
    # -------------------------------------------------------------------------

    def get_carrier(
        self,
        shipment,
    ):
        """
        Returns shipment carrier information.
        """

        client = self.auth_service.api_client(
            shipment.account_id,
        )

        return client.get_carrier(
            shipment.shipment_id,
        )

    # -------------------------------------------------------------------------

    def synchronize_carrier(
        self,
        shipment,
    ):
        """
        Synchronizes carrier information.
        """

        carrier = self.get_carrier(
            shipment,
        )

        shipment.write({

            "tracking_method": carrier.get(
                "name"
            ),

            "last_sync_at": fields.Datetime.now(),

        })

        return carrier

    # -------------------------------------------------------------------------
    # Shipment Events
    # -------------------------------------------------------------------------

    def get_events(
        self,
        shipment,
    ):
        """
        Returns shipment events.
        """

        history = self.get_tracking_history(
            shipment,
        )

        return history.get(
            "events",
            [],
        )

    # -------------------------------------------------------------------------

    def synchronize_events(
        self,
        shipment,
    ):
        """
        Synchronizes shipment events.
        """

        events = self.get_events(
            shipment,
        )

        if not events:
            return []

        body = "<b>Shipment Events</b><br/><br/>"

        for event in events:

            body += (
                f"{event.get('date','')} - "
                f"{event.get('status','')}<br/>"
            )

        shipment.message_post(
            body=body,
        )

        shipment.write({

            "last_sync_at": fields.Datetime.now(),

        })

        return events

    # -------------------------------------------------------------------------
    # Shipment Status
    # -------------------------------------------------------------------------

    def update_status(
        self,
        shipment,
    ):
        """
        Updates shipment status.
        """

        client = self.auth_service.api_client(
            shipment.account_id,
        )

        data = client.get_shipment(
            shipment.shipment_id,
        )

        shipment.write({

            "status": data.get(
                "status"
            ),

            "substatus": data.get(
                "substatus"
            ),

            "last_sync_at": fields.Datetime.now(),

        })

        return shipment

    # -------------------------------------------------------------------------
    # Complete Synchronization
    # -------------------------------------------------------------------------

    def synchronize_logistics(
        self,
        shipment,
    ):
        """
        Synchronizes all logistics information.
        """

        self.update_tracking(
            shipment,
        )

        self.synchronize_carrier(
            shipment,
        )

        self.synchronize_events(
            shipment,
        )

        self.synchronize_inventory(
            shipment,
        )

        shipment.write({

            "sync_status": "success",

            "last_sync_at": fields.Datetime.now(),

            "last_error": False,

        })

        return shipment

            # -------------------------------------------------------------------------
    # Batch Import
    # -------------------------------------------------------------------------

    def import_recent_shipments(
        self,
        account,
        days: int = 7,
    ):
        """
        Imports recent shipments.
        """

        client = self.auth_service.api_client(
            account,
        )

        response = client.get_recent_shipments(
            days=days,
        )

        shipments = self.env[
            "sce.ml.shipment"
        ]

        for data in response.get(
            "results",
            [],
        ):

            shipment = self._find_or_create(
                account,
                data,
            )

            self.import_shipment(
                shipment,
            )

            shipments |= shipment

        return shipments

    # -------------------------------------------------------------------------

    def synchronize_pending_shipments(
        self,
        account,
    ):
        """
        Synchronizes all non-delivered shipments.
        """

        shipments = self.env[
            "sce.ml.shipment"
        ].search([
            ("account_id", "=", account.id),
            ("status", "not in", ("delivered", "cancelled")),
        ])

        for shipment in shipments:

            self.synchronize_shipment(
                shipment,
            )

        return shipments

    # -------------------------------------------------------------------------
    # Search Helpers
    # -------------------------------------------------------------------------

    def find_shipment(
        self,
        account,
        shipment_id: str,
    ):
        """
        Finds a shipment by Mercado Libre shipment ID.
        """

        return self.env[
            "sce.ml.shipment"
        ].search(
            [
                ("account_id", "=", account.id),
                ("shipment_id", "=", str(shipment_id)),
            ],
            limit=1,
        )

    # -------------------------------------------------------------------------

    def exists(
        self,
        account,
        shipment_id: str,
    ) -> bool:
        """
        Returns True if the shipment already exists.
        """

        return bool(
            self.find_shipment(
                account,
                shipment_id,
            )
        )

    # -------------------------------------------------------------------------

    def get_picking(
        self,
        account,
        shipment_id: str,
    ):
        """
        Returns the linked stock picking.
        """

        shipment = self.find_shipment(
            account,
            shipment_id,
        )

        return shipment.picking_id if shipment else False

    # -------------------------------------------------------------------------
    # Retry
    # -------------------------------------------------------------------------

    def retry_failed_shipments(
        self,
        account,
    ):
        """
        Retries failed shipment synchronizations.
        """

        shipments = self.env[
            "sce.ml.shipment"
        ].search([
            ("account_id", "=", account.id),
            ("sync_status", "=", "error"),
        ])

        for shipment in shipments:

            try:

                self.synchronize_shipment(
                    shipment,
                )

            except Exception as exc:

                shipment.write({

                    "last_error": str(exc),

                })

        return shipments

    # -------------------------------------------------------------------------
    # Maintenance
    # -------------------------------------------------------------------------

    def cleanup_delivered_shipments(
        self,
        account,
    ):
        """
        Archives delivered shipments.
        """

        shipments = self.env[
            "sce.ml.shipment"
        ].search([
            ("account_id", "=", account.id),
            ("status", "=", "delivered"),
            ("active", "=", True),
        ])

        shipments.write({

            "active": False,

        })

        return shipments

    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    def statistics(
        self,
        account,
    ):
        """
        Returns shipment synchronization statistics.
        """

        Shipment = self.env[
            "sce.ml.shipment"
        ]

        return {

            "shipments": Shipment.search_count([
                ("account_id", "=", account.id),
            ]),

            "success": Shipment.search_count([
                ("account_id", "=", account.id),
                ("sync_status", "=", "success"),
            ]),

            "pending": Shipment.search_count([
                ("account_id", "=", account.id),
                ("sync_status", "=", "pending"),
            ]),

            "errors": Shipment.search_count([
                ("account_id", "=", account.id),
                ("sync_status", "=", "error"),
            ]),

            "delivered": Shipment.search_count([
                ("account_id", "=", account.id),
                ("status", "=", "delivered"),
            ]),

        }

            # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    @staticmethod
    def validate_shipment(
        data: dict[str, Any],
    ) -> None:
        """
        Validates the minimum information required to import a shipment.
        """

        if not data.get("id"):
            raise ValueError(
                "Shipment ID is required."
            )

        if not data.get("status"):
            raise ValueError(
                "Shipment status is required."
            )

    # -------------------------------------------------------------------------
    # Batch Operations
    # -------------------------------------------------------------------------

    def import_batch(
        self,
        account,
        shipments: list[dict[str, Any]],
    ):
        """
        Imports a batch of shipments already retrieved from the API.
        """

        imported = self.env[
            "sce.ml.shipment"
        ]

        for data in shipments:

            self.validate_shipment(
                data,
            )

            shipment = self._find_or_create(
                account,
                data,
            )

            self.import_shipment(
                shipment,
            )

            imported |= shipment

        return imported

    # -------------------------------------------------------------------------

    def synchronize_batch(
        self,
        shipments,
    ):
        """
        Synchronizes a batch of shipments.
        """

        for shipment in shipments:

            self.synchronize_shipment(
                shipment,
            )

        return shipments

    # -------------------------------------------------------------------------
    # Utilities
    # -------------------------------------------------------------------------

    @staticmethod
    def is_delivered(
        shipment,
    ) -> bool:
        """
        Returns True if the shipment has been delivered.
        """

        return shipment.status == "delivered"

    @staticmethod
    def is_cancelled(
        shipment,
    ) -> bool:
        """
        Returns True if the shipment has been cancelled.
        """

        return shipment.status == "cancelled"

    @staticmethod
    def has_tracking(
        shipment,
    ) -> bool:
        """
        Returns True if a tracking number exists.
        """

        return bool(
            shipment.tracking_number
        )

    @staticmethod
    def is_pending(
        shipment,
    ) -> bool:
        """
        Returns True if the shipment is pending.
        """

        return shipment.status in (
            "pending",
            "ready_to_ship",
        )

    # -------------------------------------------------------------------------
    # Diagnostics
    # -------------------------------------------------------------------------

    def ping(
        self,
        account,
    ) -> bool:
        """
        Checks whether the Mercado Libre Shipments API is reachable.
        """

        try:

            client = self.auth_service.api_client(
                account,
            )

            client.get_shipments(
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
        Recalculates shipment statistics.
        """

        stats = self.statistics(
            account,
        )

        account.message_post(
            body=(
                "Mercado Libre shipment statistics:"
                "<br/>"
                f"Shipments: {stats['shipments']}<br/>"
                f"Delivered: {stats['delivered']}<br/>"
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
        Performs a shipment service health check.
        """

        return {

            "api": self.ping(
                account,
            ),

            "statistics": self.statistics(
                account,
            ),

        }