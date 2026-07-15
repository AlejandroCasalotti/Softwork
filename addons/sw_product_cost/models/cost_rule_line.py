# -*- coding: utf-8 -*-

from odoo import fields, models


class SWProductCostRuleLine(models.Model):

    _name = "sw.product.cost.rule.line"
    _description = "Product Cost Rule Line"
    _order = "sequence, id"


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
            ("increase", "Increase"),
            ("decrease", "Discount"),
        ],
        required=True,
        default="increase",
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
    )


    def apply_operation(self, amount):

        self.ensure_one()

        result = amount


        if self.value_type == "percentage":

            factor = self.value / 100

            if self.operation == "increase":

                result += amount * factor


            elif self.operation == "decrease":

                result -= amount * factor


        elif self.value_type == "fixed":

            if self.operation == "increase":

                result += self.value


            elif self.operation == "decrease":

                result -= self.value


        return max(result, 0)