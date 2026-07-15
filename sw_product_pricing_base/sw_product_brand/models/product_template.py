# -*- coding: utf-8 -*-

"""
Softwork Product Brand

Extends product.template to add brand information.
"""

from __future__ import annotations

from odoo import fields, models


class ProductTemplate(models.Model):
    """Extend Product Template."""

    _inherit = "product.template"

    brand_id = fields.Many2one(
        comodel_name="sw.product.brand",
        string="Brand",
        index=True,
        tracking=True,
        help="Brand or manufacturer associated with this product.",
    )

    brand_code = fields.Char(
        string="Brand Code",
        related="brand_id.code",
        store=True,
        readonly=True,
    )

    brand_logo = fields.Image(
        string="Brand Logo",
        related="brand_id.image_1920",
        readonly=True,
    )