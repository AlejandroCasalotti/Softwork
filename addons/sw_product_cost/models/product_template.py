# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools.float_utils import float_is_zero


class ProductTemplate(models.Model):
    _inherit = "product.template"

    sw_cost_rule_id = fields.Many2one(
        comodel_name="sw.product.cost.rule",
        string="Applied Cost Rule",
        copy=False,
        index=True,
    )
    sw_base_cost = fields.Float(
        string="Base Cost",
        copy=False,
        help="Initial cost before applying rules.",
    )
    sw_final_cost = fields.Float(
        string="Calculated Cost",
        copy=False,
        help="Final cost after cascade rules.",
    )
    sw_suggested_price = fields.Float(
        string="Suggested Sale Price",
        copy=False,
    )
    sw_sale_margin_percent = fields.Float(
        string="Sales Margin (%)",
        default=0.0,
        help="Margin percentage to calculate sales price from calculated cost.",
    )

    def _sw_get_base_cost_data(self):
        """Proveedor primero (determinístico), fallback a standard_price."""
        self.ensure_one()

        Supplier = self.env["product.supplierinfo"]
        qty = 1.0

        domain = [
            ("min_qty", "<=", qty),
            "|",
            ("product_tmpl_id", "=", self.id),
            ("product_id", "in", self.product_variant_ids.ids),
        ]
        suppliers = Supplier.search(domain, order="sequence asc, min_qty asc, id asc", limit=1)

        if suppliers:
            supplier = suppliers[0]
            supplier_price = supplier.price or 0.0
            supplier_currency = supplier.currency_id or supplier.company_id.currency_id or self.company_id.currency_id
            company_currency = self.company_id.currency_id
            conversion_date = fields.Date.context_today(self)

            if supplier_currency and company_currency:
                base_cost = supplier_currency._convert(
                    supplier_price,
                    company_currency,
                    self.company_id,
                    conversion_date,
                )
            else:
                base_cost = supplier_price

            return base_cost, {
                "price": supplier_price,
                "currency": supplier_currency,
                "supplier": supplier,
                "date": conversion_date,
                "is_fallback": False,
            }

        return (self.standard_price or 0.0), {
            "price": self.standard_price or 0.0,
            "currency": self.company_id.currency_id,
            "supplier": False,
            "date": fields.Date.context_today(self),
            "is_fallback": True,
        }

    def _sw_calculate_cost_without_margin_rule(self, base_cost, rule):
        self.ensure_one()
        result = base_cost
        for line in rule.line_ids.sorted(key=lambda l: (l.sequence, l.id)):
            if not line.active:
                continue
            result = line.apply(result)

        rounding = self.currency_id.rounding if self.currency_id else 0.01
        if float_is_zero(result, precision_rounding=rounding):
            result = 0.0
        return result

    def _sw_apply_cost_rule(self, base_cost):
        self.ensure_one()
        Rule = self.env["sw.product.cost.rule"]

        base_domain = [
            ("active", "=", True),
            "|",
            ("company_id", "=", self.company_id.id),
            ("company_id", "=", False),
        ]

        product_rule = Rule.search(
            base_domain + [("rule_type", "=", "product"), ("product_id", "=", self.id)],
            order="sequence asc, id asc",
            limit=1,
        )
        if product_rule:
            return product_rule, self._sw_calculate_cost_without_margin_rule(base_cost, product_rule)

        category_rule = Rule.search(
            base_domain + [("rule_type", "=", "category"), ("categ_id", "=", self.categ_id.id)],
            order="sequence asc, id asc",
            limit=1,
        )
        if category_rule:
            return category_rule, self._sw_calculate_cost_without_margin_rule(base_cost, category_rule)

        if "brand_id" in self._fields and self.brand_id:
            brand_rule = Rule.search(
                base_domain + [("rule_type", "=", "brand"), ("brand_id", "=", self.brand_id.id)],
                order="sequence asc, id asc",
                limit=1,
            )
            if brand_rule:
                return brand_rule, self._sw_calculate_cost_without_margin_rule(base_cost, brand_rule)

        global_rule = Rule.search(
            base_domain + [("rule_type", "=", "global")],
            order="sequence asc, id asc",
            limit=1,
        )
        if global_rule:
            return global_rule, self._sw_calculate_cost_without_margin_rule(base_cost, global_rule)

        return False, base_cost

    def _sw_recompute_prices(self):
        for product in self.exists():
            base_cost, _supplier_data = product._sw_get_base_cost_data()
            rule, calculated_cost = product._sw_apply_cost_rule(base_cost)

            margin = (product.sw_sale_margin_percent or 0.0) / 100.0
            suggested_price = calculated_cost * (1.0 + margin)

            vals_to_write = {
                "sw_base_cost": base_cost,
                "sw_cost_rule_id": rule.id if (rule and rule.exists()) else False,
                "sw_final_cost": calculated_cost,
                "sw_suggested_price": suggested_price,
                "list_price": suggested_price,
            }

            product.with_context(sw_skip_recompute=True).write(vals_to_write)

            if product.product_variant_id:
                product.product_variant_id.with_context(sw_skip_recompute=True).write({
                    "standard_price": calculated_cost,
                })

    def action_sw_recompute_cost_rule(self):
        self._sw_recompute_prices()
        return True

    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)
        products._sw_recompute_prices()
        return products

    def write(self, vals):
        if self.env.context.get("sw_skip_recompute"):
            return super().write(vals)

        res = super().write(vals)

        watched = {
            "seller_ids",
            "categ_id",
            "brand_id",
            "company_id",
            "sw_sale_margin_percent",
            "standard_price",
        }
        if watched.intersection(vals.keys()):
            self._sw_recompute_prices()

        return res