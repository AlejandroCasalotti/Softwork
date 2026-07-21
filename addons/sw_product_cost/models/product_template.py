# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductTemplate(models.Model):
    """
    Extension of product.template for advanced
    cost calculation management.
    """

    _inherit = "product.template"

    # ---------------------------------------------------------
    # Applied rule
    # ---------------------------------------------------------

    sw_cost_rule_id = fields.Many2one(
        comodel_name="sw.product.cost.rule",
        string="Applied Cost Rule",
        compute="_compute_sw_cost_values",
        store=True,
    )

    # ---------------------------------------------------------
    # Base cost
    # ---------------------------------------------------------

    sw_base_cost = fields.Float(
        string="Base Cost",
        compute="_compute_sw_cost_values",
        store=True,
        help="Initial cost before applying rules.",
    )

    # ---------------------------------------------------------
    # Final calculated cost
    # ---------------------------------------------------------

    sw_final_cost = fields.Float(
        string="Calculated Cost",
        compute="_compute_sw_cost_values",
        store=True,
        help="Final cost after cascade rules.",
    )

    # ---------------------------------------------------------
    # Suggested sale price
    # ---------------------------------------------------------

    sw_suggested_price = fields.Float(
        string="Suggested Sale Price",
        compute="_compute_sw_cost_values",
        store=True,
    )

    sw_sale_margin_percent = fields.Float(
        string="Sales Margin (%)",
        default=0.0,
        help="Margin percentage to calculate sales price from calculated cost.",
    )

    # ---------------------------------------------------------
    # Compute engine
    # ---------------------------------------------------------

    @api.depends(
        "categ_id",
        "company_id",
        "brand_id",
        "seller_ids",
        "seller_ids.sequence",
        "seller_ids.min_qty",
        "seller_ids.price",
        "seller_ids.currency_id",
        "sw_sale_margin_percent",
    )
    def _compute_sw_cost_values(self):
        # compute should be pure assignment to avoid frontend/owl instability
        for product in self:
            base_cost, _supplier_data = product._sw_get_base_cost_data()
            rule, calculated_cost = product._sw_apply_cost_rule(base_cost)
            margin = (product.sw_sale_margin_percent or 0.0) / 100.0
            suggested_price = calculated_cost * (1.0 + margin)

            product.sw_base_cost = base_cost
            product.sw_cost_rule_id = rule
            product.sw_final_cost = calculated_cost
            product.sw_suggested_price = suggested_price

    def _sw_get_base_cost_data(self):
        self.ensure_one()
        supplier_data = self.env["product.supplierinfo"].get_reference_cost_data(self, quantity=1.0)
        supplier_price = supplier_data.get("price", 0.0)
        supplier_currency = supplier_data.get("currency") or self.company_id.currency_id
        company_currency = self.company_id.currency_id
        conversion_date = supplier_data.get("date") or fields.Date.context_today(self)

        if supplier_currency and company_currency:
            base_cost = supplier_currency._convert(
                supplier_price,
                company_currency,
                self.company_id,
                conversion_date,
            )
        else:
            base_cost = supplier_price or self.standard_price
        return base_cost, supplier_data

    def _sw_calculate_cost_without_margin_rule(self, base_cost, rule):
        self.ensure_one()
        result = base_cost
        for line in rule.line_ids.sorted(key=lambda l: (l.sequence, l.id)):
            if not line.active:
                continue
            if line.operation == "margin":
                continue
            result = line.apply(result)
        return result

    def _sw_apply_cost_rule(self, base_cost):
        self.ensure_one()
        rule = self.env["sw.product.cost.rule"].get_rule_for_product(self)
        if rule:
            return rule, self._sw_calculate_cost_without_margin_rule(base_cost, rule)
        return False, base_cost

    def _sw_recompute_prices(self):
        for product in self:
            base_cost, _supplier_data = product._sw_get_base_cost_data()
            rule, calculated_cost = product._sw_apply_cost_rule(base_cost)
            margin = (product.sw_sale_margin_percent or 0.0) / 100.0
            suggested_price = calculated_cost * (1.0 + margin)

            # always write computed values in recompute path to avoid stale values
            # after create/onchange chains and ensure rule formulas are persisted.
            vals_to_write = {
                "sw_base_cost": base_cost,
                "sw_cost_rule_id": rule.id if rule else False,
                "sw_final_cost": calculated_cost,
                "sw_suggested_price": suggested_price,
                "standard_price": calculated_cost,
                "list_price": suggested_price,
            }
            super(ProductTemplate, product).write(vals_to_write)

    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)
        products._sw_recompute_prices()
        return products

    def write(self, vals):
        res = super().write(vals)
        watched = {
            "seller_ids",
            "categ_id",
            "brand_id",
            "company_id",
            "sw_sale_margin_percent",
        }
        if watched.intersection(vals.keys()):
            self._sw_recompute_prices()
        return res