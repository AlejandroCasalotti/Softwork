# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Mercado Libre Publication
"""

from __future__ import annotations

from odoo import api, fields, models


class MLPublication(models.Model):
    _name = "sce.ml.publication"
    _description = "Mercado Libre Publication"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "write_date desc"

    # -------------------------------------------------------------------------
    # Relations
    # -------------------------------------------------------------------------

    product_tmpl_id = fields.Many2one(
        comodel_name="product.template",
        string="Product",
        required=True,
        ondelete="cascade",
        index=True,
        tracking=True,
    )

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

    # -------------------------------------------------------------------------
    # Mercado Libre Publication
    # -------------------------------------------------------------------------

    item_id = fields.Char(
        string="Item ID",
        copy=False,
        index=True,
        tracking=True,
    )

    permalink = fields.Char(
        string="Permalink",
        readonly=True,
    )

    catalog_listing = fields.Boolean(
        string="Catalog Listing",
        readonly=True,
    )

    listing_type = fields.Char(
        string="Listing Type",
    )

    buying_mode = fields.Char(
        string="Buying Mode",
    )

    status = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("paused", "Paused"),
            ("closed", "Closed"),
            ("under_review", "Under Review"),
            ("inactive", "Inactive"),
            ("error", "Error"),
        ],
        default="draft",
        tracking=True,
        index=True,
    )

    sub_status = fields.Char(
        string="Sub Status",
        readonly=True,
    )

    health = fields.Integer(
        string="Health",
        readonly=True,
    )

    # -------------------------------------------------------------------------
    # Commercial Information
    # -------------------------------------------------------------------------

    title = fields.Char(
        string="Title",
    )

    category_id = fields.Char(
        string="Category ID",
    )

    currency_id = fields.Char(
        string="Currency",
    )

    price = fields.Float(
        string="Price",
        digits="Product Price",
    )

    available_quantity = fields.Integer(
        string="Available Quantity",
    )

    sold_quantity = fields.Integer(
        string="Sold Quantity",
        readonly=True,
    )

    condition = fields.Selection(
        [
            ("new", "New"),
            ("used", "Used"),
        ],
    )

    warranty = fields.Char()

    # -------------------------------------------------------------------------
    # Synchronization
    # -------------------------------------------------------------------------

    published_at = fields.Datetime()

    last_sync_at = fields.Datetime()

    last_price_sync = fields.Datetime()

    last_stock_sync = fields.Datetime()

    last_error = fields.Text()

    sync_status = fields.Selection(
        [
            ("pending", "Pending"),
            ("success", "Success"),
            ("warning", "Warning"),
            ("error", "Error"),
        ],
        default="pending",
    )

    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    visit_count = fields.Integer(
        readonly=True,
    )

    question_count = fields.Integer(
        readonly=True,
    )

    order_count = fields.Integer(
        readonly=True,
    )

    # -------------------------------------------------------------------------
    # Active
    # -------------------------------------------------------------------------

    active = fields.Boolean(
        default=True,
    )

    # -------------------------------------------------------------------------
    # SQL
    # -------------------------------------------------------------------------

    _item_unique = models.Constraint(
        "UNIQUE(item_id)",
        "The Mercado Libre Item ID already exists.",
    )

    # -------------------------------------------------------------------------
    # Computed
    # -------------------------------------------------------------------------

    @api.depends("item_id")
    def _compute_display_name(self):
        for record in self:
            if record.item_id:
                record.display_name = f"{record.item_id} - {record.product_tmpl_id.display_name}"
            else:
                record.display_name = record.product_tmpl_id.display_name

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def action_open_permalink(self):
        self.ensure_one()

        if not self.permalink:
            return False

        return {
            "type": "ir.actions.act_url",
            "url": self.permalink,
            "target": "new",
        }

    def action_sync(self):
        self.ensure_one()

        return self.env[
            "sce.ml.product.service"
        ].synchronize_publication(
            self
        )

    def action_update_stock(self):
        self.ensure_one()

        return self.env[
            "sce.ml.product.service"
        ].update_publication_stock(
            self
        )

    def action_update_price(self):
        self.ensure_one()

        return self.env[
            "sce.ml.product.service"
        ].update_publication_price(
            self
        )

    def action_pause(self):
        self.ensure_one()

        return self.env[
            "sce.ml.product.service"
        ].pause_publication(
            self
        )

    def action_activate(self):
        self.ensure_one()

        return self.env[
            "sce.ml.product.service"
        ].activate_publication(
            self
        )

    def action_close(self):
        self.ensure_one()

        return self.env[
            "sce.ml.product.service"
        ].close_publication(
            self
        )