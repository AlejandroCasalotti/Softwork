# -*- coding: utf-8 -*-

from odoo import fields, models


class SWProductCostRuleLine(models.Model):

    _name = "sw.product.cost.rule.line"
    _description = "Product Cost Rule Line"
    _order = "sequence, id"


    rule_id = fields.Many2one(
        comodel_name="sw.product.cost.rule",
        string="Rule",
        required=True,
        ondelete="cascade",
    )


    name = fields.Char(
        string="Description",
        required=True,
    )


    sequence = fields.Integer(
        string="Sequence",
        default=10,
    )


    active = fields.Boolean(
        default=True,
    )


    operation = fields.Selection(
        selection=[
            ("increase", "Increase"),
            ("discount", "Discount"),
            ("margin", "Sales Margin"),
        ],
        string="Operation",
        required=True,
        default="increase",
    )


    value_type = fields.Selection(
        selection=[
            ("percentage", "Percentage"),
            ("fixed", "Fixed Amount"),
        ],
        string="Value Type",
        required=True,
        default="percentage",
    )


    value = fields.Float(
        string="Value",
        required=True,
        default=0,
    )


    def apply(self, amount):

        self.ensure_one()


        if self.value_type == "percentage":


            percent = self.value / 100


            if self.operation == "discount":

                return amount * (
                    1 - percent
                )


            elif self.operation == "increase":

                return amount * (
                    1 + percent
                )


            elif self.operation == "margin":

                if percent >= 1:
                    return amount

                return amount / (
                    1 - percent
                )


        elif self.value_type == "fixed":


            if self.operation == "discount":

                return amount - self.value


            else:

                return amount + self.value


        return amount