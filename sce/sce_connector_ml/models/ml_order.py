# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Mercado Libre Order
"""

from __future__ import annotations

from odoo import api, fields, models


class MLOrder(models.Model):
    _name = "sce.ml.order"
    _description = "Mercado Libre Order"
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

    sale_order_id = fields.Many2one(
        comodel_name="sale.order",
        string="Sales Order",
        readonly=True,
        index=True,
    )

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Customer",
        readonly=True,
        index=True,
    )

    # -------------------------------------------------------------------------
    # Mercado Libre
    # -------------------------------------------------------------------------

    order_id = fields.Char(
        string="Order ID",
        required=True,
        copy=False,
        index=True,
        tracking=True,
    )

    status = fields.Selection(
        [
            ("confirmed", "Confirmed"),
            ("payment_required", "Payment Required"),
            ("payment_in_process", "Payment in Process"),
            ("paid", "Paid"),
            ("cancelled", "Cancelled"),
        ],
        string="Order Status",
        tracking=True,
        index=True,
    )

    substatus = fields.Char(
        string="Substatus",
    )

    payment_status = fields.Char(
        string="Payment Status",
    )

    shipping_status = fields.Char(
        string="Shipping Status",
    )

    currency_id = fields.Char(
        string="Currency",
    )

    total_amount = fields.Float(
        string="Total Amount",
        digits="Product Price",
    )

    paid_amount = fields.Float(
        string="Paid Amount",
        digits="Product Price",
    )

    # -------------------------------------------------------------------------
    # Buyer
    # -------------------------------------------------------------------------

    buyer_id = fields.Char(
        string="Buyer ID",
        index=True,
    )

    buyer_nickname = fields.Char(
        string="Buyer",
    )

    # -------------------------------------------------------------------------
    # Shipment
    # -------------------------------------------------------------------------

    shipping_id = fields.Char(
        string="Shipping ID",
        index=True,
    )

    # -------------------------------------------------------------------------
    # Dates
    # -------------------------------------------------------------------------

    date_created = fields.Datetime(
        string="Created At",
        readonly=True,
    )

    date_closed = fields.Datetime(
        string="Closed At",
        readonly=True,
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

    _order_unique = models.Constraint(
        "UNIQUE(order_id)",
        "The Mercado Libre Order already exists.",
    )

    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    @api.depends("sale_order_id")
    def _compute_display_name(self):
        for record in self:
            if record.sale_order_id:
                record.display_name = (
                    f"{record.order_id} - "
                    f"{record.sale_order_id.name}"
                )
            else:
                record.display_name = record.order_id

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

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

    def action_synchronize(self):
        self.ensure_one()

        return self.env[
            "sce.ml.order.service"
        ].synchronize_order(
            self
        )

    def action_import(self):
        self.ensure_one()

        return self.env[
            "sce.ml.order.service"
        ].import_order(
            self
        )

    def action_update_status(self):
        self.ensure_one()

        return self.env[
            "sce.ml.order.service"
        ].update_order_status(
            self
        )