# -*- coding: utf-8 -*-

from odoo import fields, models


class SWProductCostRuleLine(models.Model):
    """
    Product Cost Rule Lines.

    Allows cascading cost operations inside
    a single product cost rule.
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
    # Basic information
    # ---------------------------------------------------------

    name = fields.Char(
        string="Description",
        required=True,
    )


    sequence = fields.Integer(
        string="Sequence",
        default=10,
        help="Order in which this operation is executed.",
    )


    active = fields.Boolean(
        string="Active",
        default=True,
    )


    # ---------------------------------------------------------
    # Operation
    # ---------------------------------------------------------

    operation_type = fields.Selection(
        selection=[
            (
                "increase_percentage",
                "Increase Percentage"
            ),
            (
                "increase_fixed",
                "Increase Fixed Amount"
            ),
            (
                "discount_percentage",
                "Discount Percentage"
            ),
            (
                "discount_fixed",
                "Discount Fixed Amount"
            ),
        ],
        string="Operation",
        required=True,
        default="increase_percentage",
    )


    value = fields.Float(
        string="Value",
        required=True,
        default=0.0,
    )


    # ---------------------------------------------------------
    # Calculation
    # ---------------------------------------------------------

    def apply_operation(self, amount):
        """
        Apply this line operation.

        Receives current amount and returns
        calculated amount.
        """

        self.ensure_one()


        if not self.active:
            return amount


        # Increase %
        if self.operation_type == "increase_percentage":

            return amount + (
                amount * self.value / 100
            )


        # Increase fixed
        elif self.operation_type == "increase_fixed":

            return amount + self.value


        # Discount %
        elif self.operation_type == "discount_percentage":

            return amount - (
                amount * self.value / 100
            )


        # Discount fixed
        elif self.operation_type == "discount_fixed":

            return amount - self.value


        return amount