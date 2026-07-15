# -*- coding: utf-8 -*-

from odoo import fields, models


class SWProductCostRule(models.Model):
    """
    Product cost calculation rule.

    Supports cascade calculation through rule lines.
    """

    _name = "sw.product.cost.rule"
    _description = "Product Cost Rule"
    _order = "sequence, id"

    name = fields.Char(
        string="Rule Name",
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
            ("global", "Global"),
            ("category", "Product Category"),
            ("brand", "Product Brand"),
            ("product", "Specific Product"),
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


    # Cascade lines

    line_ids = fields.One2many(
        "sw.product.cost.rule.line",
        "rule_id",
        string="Calculation Steps",
        copy=True,
    )


    def calculate_cost(self, base_cost):
        """
        Execute cascade calculation.

        Example:

        Cost = 100

        +10% freight
        -5% discount
        +30% margin

        Result is calculated sequentially.
        """

        self.ensure_one()

        value = base_cost

        for line in self.line_ids.sorted("sequence"):

            value = line.apply(value)

        return value


    def calculate_sale_price(self, cost):

        self.ensure_one()

        value = cost

        for line in self.line_ids.sorted("sequence"):

            if line.operation == "margin":
                value = line.apply(value)

        return value