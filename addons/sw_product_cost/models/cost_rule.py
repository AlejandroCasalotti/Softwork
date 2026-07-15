# -*- coding: utf-8 -*-

from odoo import fields, models


class SWProductCostRule(models.Model):

    _name = "sw.product.cost.rule"
    _description = "Product Cost Rule"
    _order = "sequence, id"


    name = fields.Char(
        required=True,
    )


    active = fields.Boolean(
        default=True,
    )


    sequence = fields.Integer(
        default=10,
    )


    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
    )


    rule_type = fields.Selection(
        [
            ("global","Global"),
            ("category","Category"),
            ("brand","Brand"),
            ("product","Product"),
        ],
        required=True,
        default="global",
    )


    product_id = fields.Many2one(
        "product.template",
    )


    categ_id = fields.Many2one(
        "product.category",
    )


    brand_id = fields.Many2one(
        "sw.product.brand",
    )


    line_ids = fields.One2many(
        "sw.product.cost.rule.line",
        "rule_id",
        string="Calculation Steps",
        copy=True,
    )