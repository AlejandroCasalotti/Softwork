# -*- coding: utf-8 -*-

from odoo import fields, models


class SWProductCostRuleLine(models.Model):
    """
    Individual calculation step inside a cost rule.
    """

    _name = "sw.product.cost.rule.line"
    _description = "Product Cost Rule Line"
    _order = "sequence, id"


    rule_id = fields.Many2one(
        comodel_name="sw.product.cost.rule",
        string="Rule",
        required=True,
        ondelete="cascade",
    )


    sequence = fields.Integer(
        string="Sequence",
        default=10,
    )


    name = fields.Char(
        string="Description",
        required=True,
    )


    calculation_type = fields.Selection(
        selection=[
            ("extra_percentage", "Extra Cost (%)"),
            ("extra_fixed", "Extra Cost Fixed"),
            ("discount_percentage", "Discount (%)"),
            ("discount_fixed", "Discount Fixed"),
            ("margin_percentage", "Sale Margin (%)"),
            ("margin_fixed", "Sale Margin Fixed"),
        ],
        string="Operation",
        required=True,
        default="margin_percentage",
    )


    value = fields.Float(
        string="Value",
        required=True,
        default=0.0,
    )