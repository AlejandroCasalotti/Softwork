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

    applied_product_count = fields.Integer(
        string="Applied Products",
        compute="_compute_applied_product_count",
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

        base_domain = [
            ("active", "=", True),
            "|",
            ("company_id", "=", product.company_id.id),
            ("company_id", "=", False),
        ]

        # Priority: product > category > brand > global
        product_rule = Rule.search(
            base_domain + [("rule_type", "=", "product"), ("product_id.product_variant_ids", "in", product.product_variant_ids.ids)],
            order="sequence asc, id asc",
            limit=1,
        )
        if not product_rule:
            product_rule = Rule.search(
                base_domain + [("rule_type", "=", "product"), ("product_id", "=", product.id)],
                order="sequence asc, id asc",
                limit=1,
            )
        if product_rule:
            return product_rule

        category_rule = Rule.search(
            base_domain + [("rule_type", "=", "category"), ("categ_id", "=", product.categ_id.id)],
            order="sequence asc, id asc",
            limit=1,
        )
        if category_rule:
            return category_rule

        brand_rule = self.env["sw.product.cost.rule"]
        if "brand_id" in product._fields and product.brand_id:
            brand_rule = Rule.search(
                base_domain + [("rule_type", "=", "brand"), ("brand_id", "=", product.brand_id.id)],
                order="sequence asc, id asc",
                limit=1,
            )
        if brand_rule:
            return brand_rule

        global_rule = Rule.search(
            base_domain + [("rule_type", "=", "global")],
            order="sequence asc, id asc",
            limit=1,
        )
        return global_rule or False

    def _get_target_products(self):
        Product = self.env["product.template"]
        products = Product.browse()

        for rule in self:
            company_domain = ["|", ("company_id", "=", rule.company_id.id), ("company_id", "=", False)]

            if rule.rule_type == "product" and rule.product_id:
                products |= Product.search([("id", "=", rule.product_id.id)] + company_domain)
                continue

            if rule.rule_type == "category" and rule.categ_id:
                products |= Product.search([("categ_id", "=", rule.categ_id.id)] + company_domain)
                continue

            if rule.rule_type == "brand" and rule.brand_id and "brand_id" in Product._fields:
                products |= Product.search([("brand_id", "=", rule.brand_id.id)] + company_domain)
                continue

            if rule.rule_type == "global":
                products |= Product.search(company_domain)

        return products

    @api.depends("rule_type", "product_id", "categ_id", "brand_id", "active", "company_id")
    def _compute_applied_product_count(self):
        for rule in self:
            rule.applied_product_count = len(rule._get_target_products()) if rule.active else 0

    def _recompute_impacted_products(self):
        Product = self.env["product.template"]
        products = Product.search([])
        products = products.exists()
        if products:
            products._sw_recompute_prices()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._recompute_impacted_products()
        return records

    def write(self, vals):
        res = super().write(vals)
        self._recompute_impacted_products()
        return res

    def action_open_rule_stats_wizard(self):
        self.ensure_one()
        wizard = self.env["sw.product.cost.rule.stats.wizard"].sudo().create({
            "rule_id": self.id,
        })
        return {
            "type": "ir.actions.act_window",
            "name": "Regla de costo - Productos aplicados",
            "res_model": "sw.product.cost.rule.stats.wizard",
            "view_mode": "form",
            "target": "new",
            "res_id": wizard.id,
        }

    def unlink(self):
        res = super().unlink()
        self._recompute_impacted_products()
        return res