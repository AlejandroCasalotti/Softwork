# -*- coding: utf-8 -*-

from odoo import fields, models


class SWProductCostRule(models.Model):
    """
    Product cost calculation rules.

    Defines margin rules that can be applied by:
    - Product
    - Brand
    - Category
    - Global rule

    Priority determines which rule is applied first.
    """

    _name = "sw.product.cost.rule"
    _description = "Product Cost Rule"
    _order = "sequence, id"

    # ---------------------------------------------------------
    # Basic information
    # ---------------------------------------------------------

    name = fields.Char(
        string="Rule Name",
        required=True,
    )

    active = fields.Boolean(
        string="Active",
        default=True,
    )

    sequence = fields.Integer(
        string="Priority",
        default=10,
        help="Lower values have higher priority.",
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )

    # ---------------------------------------------------------
    # Rule type
    # ---------------------------------------------------------

    rule_type = fields.Selection(
        selection=[
            ("global", "Global"),
            ("category", "Product Category"),
            ("brand", "Product Brand"),
            ("product", "Specific Product"),
        ],
        string="Rule Applies To",
        required=True,
        default="global",
    )

    # ---------------------------------------------------------
    # Targets
    # ---------------------------------------------------------

    product_id = fields.Many2one(
        comodel_name="product.template",
        string="Product",
    )

    categ_id = fields.Many2one(
        comodel_name="product.category",
        string="Product Category",
    )

    brand_id = fields.Many2one(
        comodel_name="product.brand",
        string="Brand",
    )

    # ---------------------------------------------------------
    # Cost calculation
    # ---------------------------------------------------------

    margin_type = fields.Selection(
        selection=[
            ("percentage", "Percentage"),
            ("fixed", "Fixed Amount"),
        ],
        string="Margin Type",
        default="percentage",
        required=True,
    )

    margin_value = fields.Float(
        string="Margin Value",
        required=True,
        default=0.0,
    )

    # ---------------------------------------------------------
    # Methods
    # ---------------------------------------------------------

    def calculate_sale_price(self, cost):
        """
        Calculate suggested sale price based on rule.

        Percentage margin example:

        Cost: 100
        Margin: 40%

        Sale price:
        100 / (1 - 0.40)

        Result:
        166.66
        """

        self.ensure_one()

        if self.margin_type == "percentage":

            margin = self.margin_value / 100

            if margin >= 1:
                return cost

            return cost / (1 - margin)

        elif self.margin_type == "fixed":

            return cost + self.margin_value

        return cost