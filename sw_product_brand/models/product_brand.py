# -*- coding: utf-8 -*-

"""
Softwork Product Brand

Brand model.

This model stores product brands/manufacturers and their
business information.
"""

from __future__ import annotations

from odoo import fields, models


class ProductBrand(models.Model):
    """Product Brand."""

    _name = "sw.product.brand"
    _description = "Product Brand"
    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
    ]
    _order = "sequence, name"

    _sql_constraints = [
        (
            "code_company_uniq",
            "unique(code, company_id)",
            "The brand code must be unique per company.",
        ),
    ]

    # ---------------------------------------------------------
    # General
    # ---------------------------------------------------------

    active = fields.Boolean(
        string="Active",
        default=True,
        tracking=True,
    )

    sequence = fields.Integer(
        string="Sequence",
        default=10,
    )

    name = fields.Char(
        string="Brand",
        required=True,
        index=True,
        tracking=True,
    )

    code = fields.Char(
        string="Code",
        index=True,
        tracking=True,
    )

    description = fields.Text(
        string="Description",
    )

    notes = fields.Html(
        string="Internal Notes",
    )

    # ---------------------------------------------------------
    # Image
    # ---------------------------------------------------------

    image_1920 = fields.Image(
        string="Logo",
        max_width=1920,
        max_height=1920,
    )

    color = fields.Integer(
        string="Color Index",
        default=0,
    )

    # ---------------------------------------------------------
    # Contact
    # ---------------------------------------------------------

    website = fields.Char(
        string="Website",
    )

    email = fields.Char(
        string="Email",
    )

    phone = fields.Char(
        string="Phone",
    )

    country_id = fields.Many2one(
        "res.country",
        string="Country",
    )

    # ---------------------------------------------------------
    # Company
    # ---------------------------------------------------------

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        index=True,
    )

    # ---------------------------------------------------------
    # Statistics
    # ---------------------------------------------------------

    product_count = fields.Integer(
        string="Products",
        compute="_compute_product_count",
    )

    # ---------------------------------------------------------
    # Compute
    # ---------------------------------------------------------

    def _compute_product_count(self):
        """Compute the number of products linked to each brand."""
        template_model = self.env["product.template"]

        for brand in self:
            brand.product_count = template_model.search_count([
                ("brand_id", "=", brand.id),
            ])