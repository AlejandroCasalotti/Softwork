# -*- coding: utf-8 -*-

from odoo import fields, models


class SWProductCostRule(models.Model):
    """
    Product cost calculation rules.

    Rules can be applied by:
    - Product
    - Category
    - Brand
    - Global

    The rule supports chained calculations:
    Base cost
        +
    Additional costs
        +
    Margin
        -
    Discounts
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
    # Rule scope
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
        comodel_name="sw.product.brand",
        string="Brand",
    )


    # ---------------------------------------------------------
    # Margin
    # ---------------------------------------------------------

    margin_type = fields.Selection(
        selection=[
            (
                "percentage",
                "Percentage"
            ),
            (
                "fixed",
                "Fixed Amount"
            ),
        ],
        string="Margin Type",
        default="percentage",
        required=True,
    )


    margin_value = fields.Float(
        string="Margin Value",
        default=0.0,
    )


    # ---------------------------------------------------------
    # Cascade calculation lines
    # ---------------------------------------------------------

    extra_cost_ids = fields.One2many(
        comodel_name="sw.product.cost.rule.line",
        inverse_name="rule_id",
        string="Additional Costs",
        domain=[
            ("line_type", "=", "cost")
        ],
    )


    discount_ids = fields.One2many(
        comodel_name="sw.product.cost.rule.line",
        inverse_name="rule_id",
        string="Discounts",
        domain=[
            ("line_type", "=", "discount")
        ],
    )


    # ---------------------------------------------------------
    # Calculation
    # ---------------------------------------------------------

    def calculate_sale_price(self, cost):
        """
        Execute complete cost calculation.

        Example:

        Base cost:
            100

        Extra cost:
            +10

        Margin:
            +30%

        Discount:
            -5%

        Result:
            136.85
        """

        self.ensure_one()


        result = cost


        # -----------------------------------------------------
        # Additional costs
        # -----------------------------------------------------

        for line in self.extra_cost_ids.sorted(
            key=lambda x: x.sequence
        ):

            result = line.apply(result)


        # -----------------------------------------------------
        # Margin
        # -----------------------------------------------------

        if self.margin_type == "percentage":

            margin = self.margin_value / 100

            if margin < 1:

                result = result / (1 - margin)


        elif self.margin_type == "fixed":

            result += self.margin_value


        # -----------------------------------------------------
        # Discounts
        # -----------------------------------------------------

        for line in self.discount_ids.sorted(
            key=lambda x: x.sequence
        ):

            result = line.apply(result)


        return result