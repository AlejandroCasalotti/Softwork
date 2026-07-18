# -*- coding: utf-8 -*-

"""
Softwork Product Brand
Brand model.
"""

from odoo import api, fields, models


class ProductBrand(models.Model):
    """Product Brand."""

    _name = "sw.product.brand"
    _description = "Product Brand"
    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
    ]
    _order = "sequence, name"

    # -------------------------------------------------------------------------
    # General
    # -------------------------------------------------------------------------

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
        help="Internal brand code.",
    )

    display_name = fields.Char(
        compute="_compute_display_name",
        store=True,
    )

    description = fields.Text(
        string="Description",
    )

    notes = fields.Html(
        string="Internal Notes",
    )

    # -------------------------------------------------------------------------
    # Image
    # -------------------------------------------------------------------------

    image_1920 = fields.Image(
        string="Logo",
    )

    color = fields.Integer(
        string="Color",
        default=0,
    )

    # -------------------------------------------------------------------------
    # Contact
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # Company
    # -------------------------------------------------------------------------

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        index=True,
    )

    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    product_count = fields.Integer(
        string="Products",
        compute="_compute_product_count",
    )

    # -------------------------------------------------------------------------
    # Compute
    # -------------------------------------------------------------------------

    @api.depends("name", "code")
    def _compute_display_name(self):
        """Compute display name."""

        for record in self:
            if record.code:
                record.display_name = f"[{record.code}] {record.name}"
            else:
                record.display_name = record.name

    @api.depends()
    def _compute_product_count(self):
        """Compute number of products."""

        template = self.env["product.template"]

        for record in self:
            record.product_count = template.search_count([
                ("brand_id", "=", record.id),
            ])

    # -------------------------------------------------------------------------
    # Constraints
    # -------------------------------------------------------------------------

    @api.constrains("code", "company_id")
    def _check_code_company(self):
        """Ensure code is unique per company."""

        for record in self:
            if not record.code:
                continue

            duplicate = self.search([
                ("id", "!=", record.id),
                ("company_id", "=", record.company_id.id),
                ("code", "=", record.code),
            ], limit=1)

            if duplicate:
                from odoo.exceptions import ValidationError

                raise ValidationError(
                    "The brand code must be unique per company."
                )

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def action_open_products(self):
        """Open products of this brand."""

        self.ensure_one()

        return {
            "type": "ir.actions.act_window",
            "name": "Products",
            "res_model": "product.template",
            "view_mode": "list,form",
            "domain": [
                ("brand_id", "=", self.id),
            ],
            "context": {
                "default_brand_id": self.id,
            },
        }