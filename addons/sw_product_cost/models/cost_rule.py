# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SWProductCostRule(models.Model):
    """
    Product cost calculation rule.
    A rule contains multiple calculation lines that are
    executed sequentially (cascade).
    Example:
    Cost 100
    - Discount 10%
    + Freight 5%
    + Margin 30%
    Each line modifies the previous result.
    """

    _name = "sw.product.cost.rule"
    _description = "Product Cost Rule"
    _order = "sequence, id"

    # ---------------------------------------------------------
    # Basic information
    # ---------------------------------------------------------

    name = fields.Char(
        string="Rule Name",
        required=True,
    )

    active = fields.Boolean(
        string="Active",
        default=True,
    )

    sequence = fields.Integer(
        string="Priority",
        default=10,
        help="Lower values are applied first.",
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        index=True,
    )


    # ---------------------------------------------------------
    # Applicability
    # ---------------------------------------------------------

    rule_type = fields.Selection(
        selection=[
            ("global", "Global"),
            ("category", "Product Category"),
            ("brand", "Product Brand"),
            ("product", "Specific Product"),
        ],
        string="Apply To",
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


    # ---------------------------------------------------------
    # Cascade lines
    # ---------------------------------------------------------

    line_ids = fields.One2many(
        "sw.product.cost.rule.line",
        "rule_id",
        string="Calculation Steps",
        copy=True,
    )


    # ---------------------------------------------------------
    # Validation
    # ---------------------------------------------------------

    @api.constrains(
        "rule_type",
        "product_id",
        "categ_id",
        "brand_id",
    )
    def _check_rule_target(self):

        for rule in self:

            if rule.rule_type == "product" and not rule.product_id:
                raise ValidationError(
                    "Product rule requires a product."
                )

            if rule.rule_type == "category" and not rule.categ_id:
                raise ValidationError(
                    "Category rule requires a category."
                )

            if rule.rule_type == "brand" and not rule.brand_id:
                raise ValidationError(
                    "Brand rule requires a brand."
                )


    # ---------------------------------------------------------
    # Calculation engine
    # ---------------------------------------------------------

    def calculate_cost(self, base_cost):

        self.ensure_one()

        result = base_cost

        lines = self.line_ids.sorted(
            key=lambda x: x.sequence
        )

        for line in lines:

            result = line.apply(
                result
            )

        return result


    # ---------------------------------------------------------
    # Helper
    # ---------------------------------------------------------

    def get_rule_for_product(self, product):

        Rule = self.env["sw.product.cost.rule"]

        rules = Rule.search(
            [
                ("active", "=", True),
                "|",
                    ("company_id", "=", product.company_id.id),
                    ("company_id", "=", False),
            ],
            order="sequence asc",
        )


        for rule in rules:

            if rule.rule_type == "global":
                return rule


            if (
                rule.rule_type == "product"
                and rule.product_id == product
            ):
                return rule


            if (
                rule.rule_type == "category"
                and rule.categ_id == product.categ_id
            ):
                return rule


            if (
                rule.rule_type == "brand"
                and hasattr(product, "brand_id")
                and rule.brand_id == product.brand_id
            ):
                return rule


        return False
