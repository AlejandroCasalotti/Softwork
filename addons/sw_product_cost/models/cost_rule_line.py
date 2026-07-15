# -*- coding: utf-8 -*-

from odoo import fields, models


class SWProductCostRuleLine(models.Model):

    _name = "sw.product.cost.rule.line"
    _description = "Product Cost Rule Line"
    _order = "sequence,id"


    rule_id = fields.Many2one(
        "sw.product.cost.rule",
        required=True,
        ondelete="cascade",
    )


    name = fields.Char(
        required=True,
    )


    sequence = fields.Integer(
        default=10,
    )


    operation = fields.Selection(
        [
            ("margin", "Margin"),
            ("discount", "Discount"),
            ("extra_cost", "Extra Cost"),
        ],
        required=True,
        default="margin",
    )


    value_type = fields.Selection(
        [
            ("percentage", "Percentage"),
            ("fixed", "Fixed Amount"),
        ],
        required=True,
        default="percentage",
    )


    value = fields.Float(
        required=True,
        default=0,
    )


    def apply(self, amount):

        self.ensure_one()


        if self.operation == "margin":

            if self.value_type == "percentage":
                return amount / (
                    1 - (self.value / 100)
                )

            return amount + self.value



        if self.operation == "discount":

            if self.value_type == "percentage":
                return amount * (
                    1 - (self.value / 100)
                )

            return amount - self.value



        if self.operation == "extra_cost":

            if self.value_type == "percentage":
                return amount * (
                    1 + (self.value / 100)
                )

            return amount + self.value


        return amount