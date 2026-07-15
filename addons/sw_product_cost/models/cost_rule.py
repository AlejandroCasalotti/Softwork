# -*- coding: utf-8 -*-

from odoo import fields, models


class SWProductCostRule(models.Model):
    """
    Product cost calculation rule.

    A rule contains multiple calculation lines.
    Lines are executed sequentially.
    """

    _name = "sw.product.cost.rule"
    _description = "Product Cost Rule"
    _order = "sequence, id"


    name = fields.Char(
        required=True,
        string="Rule Name",
    )


    active = fields.Boolean(
        default=True,
    )


    sequence = fields.Integer(
        default=10,
        string="Priority",
    )


    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        required=True,
    )


    rule_type = fields.Selection(
        [
            ("global", "Global"),
            ("category", "Category"),
            ("brand", "Brand"),
            ("product", "Product"),
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
    )


    def calculate_cost(self, cost):

        self.ensure_one()

        result = cost

        for line in self.line_ids.sorted(
            key=lambda x: x.sequence
        ):
            result = line.apply(result)

        return result


    def match_product(self, product):

        self.ensure_one()

        if self.rule_type == "global":
            return True


        if self.rule_type == "product":
            return self.product_id == product


        if self.rule_type == "category":
            return self.categ_id == product.categ_id


        if self.rule_type == "brand":

            if hasattr(product, "brand_id"):
                return self.brand_id == product.brand_id


        return False