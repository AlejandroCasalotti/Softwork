# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Mercado Libre Shipment
"""

from __future__ import annotations

from odoo import api, fields, models


class MLShipment(models.Model):
    _name = "sce.ml.shipment"
    _description = "Mercado Libre Shipment"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_created desc"

    # -------------------------------------------------------------------------
    # Relations
    # -------------------------------------------------------------------------

    account_id = fields.Many2one(
        comodel_name="sce.ml.account",
        string="Mercado Libre Account",
        required=True,
        ondelete="cascade",
        index=True,
        tracking=True,
    )

    company_id = fields.Many2one(
        related="account_id.company_id",
        store=True,
        readonly=True,
    )

    order_id = fields.Many2one(
        comodel_name="sce.ml.order",
        string="Mercado Libre Order",
        required=True,
        ondelete="cascade",
        index=True,
    )

    sale_order_id = fields.Many2one(
        related="order_id.sale_order_id",
        store=True,
        readonly=True,
    )

    partner_id = fields.Many2one(
        related="order_id.partner_id",
        store=True,
        readonly=True,
    )

    picking_id = fields.Many2one(
        comodel_name="stock.picking",
        string="Stock Picking",
        readonly=True,
        index=True,
    )

    # -------------------------------------------------------------------------
    # Shipment
    # -------------------------------------------------------------------------

    shipment_id = fields.Char(
        string="Shipment ID",
        required=True,
        copy=False,
        index=True,
        tracking=True,
    )

    shipping_mode = fields.Char(
        string="Shipping Mode",
    )

    logistic_type = fields.Char(
        string="Logistic Type",
    )

    status = fields.Selection(
        [
            ("pending", "Pending"),
            ("ready_to_ship", "Ready to Ship"),
            ("shipped", "Shipped"),
            ("delivered", "Delivered"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        tracking=True,
        index=True,
    )

    substatus = fields.Char(
        string="Substatus",
    )

    tracking_number = fields.Char(
        string="Tracking Number",
        index=True,
    )

    tracking_method = fields.Char(
        string="Carrier",
    )

    # -------------------------------------------------------------------------
    # Receiver
    # -------------------------------------------------------------------------

    receiver_name = fields.Char(
        string="Receiver",
    )

    receiver_phone = fields.Char(
        string="Phone",
    )

    street = fields.Char(
        string="Street",
    )

    city = fields.Char(
        string="City",
    )

    state = fields.Char(
        string="State",
    )

    zip = fields.Char(
        string="ZIP Code",
    )

    country = fields.Char(
        string="Country",
    )

    # -------------------------------------------------------------------------
    # Dates
    # -------------------------------------------------------------------------

    date_created = fields.Datetime(
        string="Created At",
    )

    date_shipped = fields.Datetime(
        string="Shipped At",
    )

    date_delivered = fields.Datetime(
        string="Delivered At",
    )

    last_sync_at = fields.Datetime(
        string="Last Synchronization",
        readonly=True,
    )

    # -------------------------------------------------------------------------
    # Synchronization
    # -------------------------------------------------------------------------

    sync_status = fields.Selection(
        [
            ("pending", "Pending"),
            ("success", "Success"),
            ("warning", "Warning"),
            ("error", "Error"),
        ],
        default="pending",
        tracking=True,
    )

    last_error = fields.Text(
        string="Last Error",
        readonly=True,
    )

    raw_data = fields.Json(
        string="Raw Response",
        readonly=True,
    )

    active = fields.Boolean(
        default=True,
    )

    # -------------------------------------------------------------------------
    # SQL Constraints
    # -------------------------------------------------------------------------

    _shipment_unique = models.Constraint(
        "UNIQUE(shipment_id)",
        "Shipment already exists.",
    )

    # -------------------------------------------------------------------------
    # Display
    # -------------------------------------------------------------------------

    @api.depends("shipment_id", "tracking_number")
    def _compute_display_name(self):
        for shipment in self:
            shipment.display_name = (
                shipment.tracking_number
                or shipment.shipment_id
            )

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def action_synchronize(self):
        self.ensure_one()

        return self.env[
            "sce.ml.shipment.service"
        ].synchronize_shipment(
            self
        )

    def action_update_status(self):
        self.ensure_one()

        return self.env[
            "sce.ml.shipment.service"
        ].update_status(
            self
        )

    def action_open_picking(self):
        self.ensure_one()

        if not self.picking_id:
            return False

        return {
            "type": "ir.actions.act_window",
            "res_model": "stock.picking",
            "res_id": self.picking_id.id,
            "view_mode": "form",
        }

    def action_open_sale_order(self):
        self.ensure_one()

        if not self.sale_order_id:
            return False

        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "res_id": self.sale_order_id.id,
            "view_mode": "form",
        }