# -*- coding: utf-8 -*-

from odoo import fields, models


class SWProductCostRule(models.Model):
    """
    Product cost calculation rules.

    Defines rules that can be applied by:
    - Product
    - Brand
    - Category
    - Global rule

    A rule can contain multiple calculation steps
    executed sequentially.
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
    # Legacy margin configuration
    #
    # Kept for compatibility with old rules
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
    # Cascade calculation lines
    # ---------------------------------------------------------

    line_ids = fields.One2many(
        comodel_name="sw.product.cost.rule.line",
        inverse_name="rule_id",
        string="Calculation Steps",
        copy=True,
    )


    # ---------------------------------------------------------
    # Calculation engine
    # ---------------------------------------------------------

    def calculate_sale_price(self, cost):
        """
        Calculate sale price applying all rule lines
        sequentially.

        Example:

        Cost:
            1000

        + Transport 5%
        + Insurance 2%
        - Supplier Discount 10%
        + Sales Margin 40%

        Result:
            Final sale price
        """

        self.ensure_one()

        price = cost or 0.0


        # -----------------------------------------------------
        # New cascade engine
        # -----------------------------------------------------

        if self.line_ids:

            for line in self.line_ids.sorted(
                key=lambda x: x.sequence
            ):

                value = line.value or 0.0


                if line.calculation_type == "extra_percentage":

                    price += (
                        price *
                        value /
                        100
                    )


                elif line.calculation_type == "extra_fixed":

                    price += value


                elif line.calculation_type == "discount_percentage":

                    price -= (
                        price *
                        value /
                        100
                    )


                elif line.calculation_type == "discount_fixed":

                    price -= value


                elif line.calculation_type == "margin_percentage":

                    margin = value / 100

                    if margin < 1:

                        price = (
                            price /
                            (1 - margin)
                        )


                elif line.calculation_type == "margin_fixed":

                    price += value


            return price



        # -----------------------------------------------------
        # Legacy calculation
        # -----------------------------------------------------

        if self.margin_type == "percentage":

            margin = self.margin_value / 100


            if margin >= 1:
                return price


            return price / (1 - margin)



        elif self.margin_type == "fixed":

            return price + self.margin_value



        return price