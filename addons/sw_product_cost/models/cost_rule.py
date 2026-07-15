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
        string="Rule Name",
        required=True,
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
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )

    rule_type = fields.Selection(
        [
            ("global", "Global"),
            ("category", "Product Category"),
            ("brand", "Brand"),
            ("product", "Product"),
        ],
        required=True,
        default="global",
    )

    product_id = fields.Many2one(
        "product.template",
        string="Product",
    )

    categ_id = fields.Many2one(
        "product.category",
        string="Category",
    )

    brand_id = fields.Many2one(
        "sw.product.brand",
        string="Brand",
    )

    line_ids = fields.One2many(
        "sw.product.cost.rule.line",
        "rule_id",
        string="Calculation Lines",
    )


    def get_applicable_rule(self, product):

        domain = [
            ("active", "=", True),
            "|",
            ("company_id", "=", product.company_id.id),
            ("company_id", "=", False),
        ]

        rules = self.search(
            domain,
            order="sequence asc"
        )

        for rule in rules:

            if rule.rule_type == "global":
                return rule

            if rule.rule_type == "product":
                if rule.product_id == product:
                    return rule

            if rule.rule_type == "category":
                if rule.categ_id == product.categ_id:
                    return rule

            if rule.rule_type == "brand":

                if hasattr(product, "brand_id"):

                    if rule.brand_id == product.brand_id:
                        return rule

        return False


    def calculate_cost(self, base_cost):

        self.ensure_one()

        result = base_cost

        for line in self.line_ids.sorted("sequence"):

            result = line.apply_operation(result)

        return result