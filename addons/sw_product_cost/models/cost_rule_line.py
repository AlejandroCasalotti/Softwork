# -*- coding: utf-8 -*-

from odoo import fields, models


class SWProductCostRuleLine(models.Model):
    """
    Individual calculation step inside a cost rule.

    A rule can contain multiple lines.
    Lines are executed sequentially according
    to sequence field.
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
    # Basic
    # ---------------------------------------------------------

    name = fields.Char(
        string="Description",
        required=True,
    )


    sequence = fields.Integer(
        string="Sequence",
        default=10,
        help="Execution order. Lower values execute first.",
    )


    active = fields.Boolean(
        default=True,
    )


    # ---------------------------------------------------------
    # Operation
    # ---------------------------------------------------------

    operation = fields.Selection(
        selection=[
            (
                "increase",
                "Increase Cost"
            ),
            (
                "discount",
                "Discount Cost"
            ),
            (
                "margin",
                "Sales Margin"
            ),
        ],
        string="Operation",
        required=True,
        default="increase",
    )


    # ---------------------------------------------------------
    # Value
    # ---------------------------------------------------------

    value_type = fields.Selection(
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
    # Calculation
    # ---------------------------------------------------------

    def apply(self, amount):

        self.ensure_one()

        result = amount


        # -----------------------------
        # Increase
        # -----------------------------

        if self.operation == "increase":

            if self.value_type == "percentage":

                result += (
                    amount *
                    self.value /
                    100
                )

            else:

                result += self.value



        # -----------------------------
        # Discount
        # -----------------------------

        elif self.operation == "discount":


            if self.value_type == "percentage":

                result -= (
                    amount *
                    self.value /
                    100
                )

            else:

                result -= self.value



        # -----------------------------
        # Margin
        # -----------------------------

        elif self.operation == "margin":


            if self.value_type == "percentage":

                margin = self.value / 100


                if margin < 1:

                    result = (
                        amount /
                        (1 - margin)
                    )

            else:

                result += self.value



        return result