# -*- coding: utf-8 -*-

"""
Softwork Product Brand

Product Template extension.
"""

from odoo import fields, models


class ProductTemplate(models.Model):
    """Extend Product Template."""

    _inherit = "product.template"

    # -------------------------------------------------------------------------
    # Softwork
    # -------------------------------------------------------------------------

    brand_id = fields.Many2one(
        comodel_name="sw.product.brand",
        string="Brand",
        index=True,
        tracking=True,
        ondelete="restrict",
        help="Brand or manufacturer of this product.",
    )

    brand_code = fields.Char(
        string="Brand Code",
        related="brand_id.code",
        store=True,
        readonly=True,
    )

    brand_country_id = fields.Many2one(
        comodel_name="res.country",
        string="Brand Country",
        related="brand_id.country_id",
        store=True,
        readonly=True,
    )

    brand_logo = fields.Image(
        string="Brand Logo",
        related="brand_id.image_1920",
        readonly=True,
    )