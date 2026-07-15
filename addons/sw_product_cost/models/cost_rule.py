# -*- coding: utf-8 -*-

from odoo import fields, models


class SWProductCostRule(models.Model):
    """
    Product cost calculation rules.

    Defines how the final sale price is calculated.

    Priority:
        1. Product rule
        2. Brand rule
        3. Category rule
        4. Global rule

    Calculation flow:

        Base Cost
            +
        Cascade Lines
            +
        Margin
            =
        Suggested Sale Price
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
        comodel_name="sw.product.brand",
        string="Brand",
    )


    # ---------------------------------------------------------
    # Margin configuration
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

    line_ids = fields.One2many(
        comodel_name="sw.product.cost.rule.line",
        inverse_name="rule_id",
        string="Calculation Lines",
        copy=True,
    )


    # ---------------------------------------------------------
    # Calculation engine
    # ---------------------------------------------------------

    def calculate_sale_price(self, cost):
        """
        Calculates final sale price.

        Example:

        Cost:
            100

        Lines:
            + transport 10
            + import tax 5%

        Margin:
            30%

        Result:
            final suggested price
        """

        self.ensure_one()


        result = cost


        # -----------------------------------------------------
        # Apply cascade lines
        # -----------------------------------------------------

        for line in self.line_ids.sorted(
            key=lambda x: x.sequence
        ):

            result = line.apply(result)


        # -----------------------------------------------------
        # Apply margin
        # -----------------------------------------------------

        if self.margin_type == "percentage":

            margin = self.margin_value / 100


            if margin < 1:

                result = result / (1 - margin)


        elif self.margin_type == "fixed":

            result += self.margin_value


        return result