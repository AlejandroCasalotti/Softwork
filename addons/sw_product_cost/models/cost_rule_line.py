# -*- coding: utf-8 -*-

from odoo import fields, models


class SWProductCostRuleLine(models.Model):
    """
    Product Cost Rule Line.

    Each line represents one step of the
    cost calculation cascade.

    Example:

    Cost: 100

    Line 1:
    Discount 10%

    Result:
    90

    Line 2:
    Freight +5%

    Result:
    94.50

    Line 3:
    Margin +30%

    Result:
    135
    """

    _name = "sw.product.cost.rule.line"
    _description = "Product Cost Rule Line"
    _order = "sequence, id"


    # ---------------------------------------------------------
    # Relation
    # ---------------------------------------------------------

    rule_id = fields.Many2one(
        comodel_name="sw.product.cost.rule",
        string="Cost Rule",
        required=True,
        ondelete="cascade",
    )


    # ---------------------------------------------------------
    # Basic data
    # ---------------------------------------------------------

    name = fields.Char(
        string="Description",
        required=True,
    )


    sequence = fields.Integer(
        string="Sequence",
        default=10,
        help="Execution order.",
    )


    active = fields.Boolean(
        string="Active",
        default=True,
    )


    # ---------------------------------------------------------
    # Operation
    # ---------------------------------------------------------

    operation = fields.Selection(
        selection=[
            (
                "discount",
                "Discount",
            ),
            (
                "surcharge",
                "Surcharge",
            ),
            (
                "margin",
                "Sales Margin",
            ),
            (
                "add",
                "Add Fixed Amount",
            ),
            (
                "subtract",
                "Subtract Fixed Amount",
            ),
        ],
        string="Operation",
        required=True,
        default="surcharge",
    )


    # ---------------------------------------------------------
    # Value type
    # ---------------------------------------------------------

    value_type = fields.Selection(
        selection=[
            (
                "percentage",
                "Percentage",
            ),
            (
                "fixed",
                "Fixed Amount",
            ),
        ],
        string="Value Type",
        required=True,
        default="percentage",
    )


    value = fields.Float(
        string="Value",
        required=True,
        default=0.0,
    )


    # ---------------------------------------------------------
    # Calculation engine
    # ---------------------------------------------------------

    def apply(self, amount):

        self.ensure_one()


        if not self.active:
            return amount


        value = self.value


        # Percentage operations

        if self.value_type == "percentage":

            factor = value / 100


            if self.operation == "discount":

                return amount - (
                    amount * factor
                )


            if self.operation in (
                "surcharge",
                "margin",
            ):

                return amount + (
                    amount * factor
                )


        # Fixed operations

        if self.value_type == "fixed":


            if self.operation in (
                "add",
                "surcharge",
                "margin",
            ):

                return amount + value



            if self.operation in (
                "subtract",
                "discount",
            ):

                return amount - value



        return amount