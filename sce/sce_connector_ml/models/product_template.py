# -*- coding: utf-8 -*-
"""
Softwork Commerce Engine (SCE)

Mercado Libre Product Extension
"""

from __future__ import annotations

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # -------------------------------------------------------------------------
    # Relations
    # -------------------------------------------------------------------------

    ml_publication_ids = fields.One2many(
        comodel_name="sce.ml.publication",
        inverse_name="product_tmpl_id",
        string="Mercado Libre Publications",
    )

    ml_publication_count = fields.Integer(
        string="Mercado Libre Publications",
        compute="_compute_ml_publication_count",
    )

    # -------------------------------------------------------------------------
    # Mercado Libre
    # -------------------------------------------------------------------------

    ml_enabled = fields.Boolean(
        string="Publish in Mercado Libre",
        default=False,
        copy=False,
    )

    ml_title = fields.Char(
        string="Mercado Libre Title",
        copy=True,
    )

    ml_description = fields.Html(
        string="Mercado Libre Description",
        sanitize=False,
        translate=True,
    )

    ml_category_id = fields.Char(
        string="Category ID",
        copy=True,
    )

    ml_listing_type = fields.Char(
        string="Listing Type",
        default="gold_special",
    )

    ml_buying_mode = fields.Char(
        string="Buying Mode",
        default="buy_it_now",
    )

    ml_condition = fields.Selection(
        [
            ("new", "New"),
            ("used", "Used"),
        ],
        string="Condition",
        default="new",
    )

    ml_warranty = fields.Char(
        string="Warranty",
    )

    ml_currency_id = fields.Char(
        string="Currency",
        default="ARS",
    )

    ml_video_id = fields.Char(
        string="Video ID",
    )

    ml_brand = fields.Char(
        string="Brand",
    )

    ml_model = fields.Char(
        string="Model",
    )

    # -------------------------------------------------------------------------
    # Synchronization
    # -------------------------------------------------------------------------

    ml_last_export = fields.Datetime(
        string="Last Export",
        readonly=True,
        copy=False,
    )

    ml_last_sync = fields.Datetime(
        string="Last Synchronization",
        readonly=True,
        copy=False,
    )

    ml_sync_status = fields.Selection(
        [
            ("draft", "Draft"),
            ("published", "Published"),
            ("paused", "Paused"),
            ("closed", "Closed"),
            ("error", "Error"),
        ],
        string="Synchronization Status",
        default="draft",
        copy=False,
    )

    ml_last_error = fields.Text(
        string="Last Error",
        readonly=True,
        copy=False,
    )

    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    def _compute_ml_publication_count(self):

        for product in self:

            product.ml_publication_count = len(
                product.ml_publication_ids
            )

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def action_open_ml_publications(self):

        self.ensure_one()

        return {
            "type": "ir.actions.act_window",
            "name": "Mercado Libre Publications",
            "res_model": "sce.ml.publication",
            "view_mode": "list,form",
            "domain": [
                ("product_tmpl_id", "=", self.id),
            ],
        }

    def action_publish_ml(self):

        self.ensure_one()

        return self.env[
            "sce.ml.product.service"
        ].publish_product(
            self
        )

    def action_update_ml(self):

        self.ensure_one()

        return self.env[
            "sce.ml.product.service"
        ].update_product(
            self
        )

    def action_update_ml_stock(self):

        self.ensure_one()

        return self.env[
            "sce.ml.product.service"
        ].update_stock(
            self
        )

    def action_update_ml_price(self):

        self.ensure_one()

        return self.env[
            "sce.ml.product.service"
        ].update_price(
            self
        )

    def action_pause_ml(self):

        self.ensure_one()

        return self.env[
            "sce.ml.product.service"
        ].pause_product(
            self
        )

    def action_activate_ml(self):

        self.ensure_one()

        return self.env[
            "sce.ml.product.service"
        ].activate_product(
            self
        )

    def action_close_ml(self):

        self.ensure_one()

        return self.env[
            "sce.ml.product.service"
        ].close_product(
            self
        )