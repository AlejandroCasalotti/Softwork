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
        copy=False,
        index=True,
    )

    # ---------------------------------------------------------
    # Base cost
    # ---------------------------------------------------------

    sw_base_cost = fields.Float(
        string="Base Cost",
        copy=False,
        help="Initial cost before applying rules.",
    )

    # ---------------------------------------------------------
    # Final calculated cost
    # ---------------------------------------------------------

    sw_final_cost = fields.Float(
        string="Calculated Cost",
        copy=False,
        help="Final cost after cascade rules.",
    )

    # ---------------------------------------------------------
    # Suggested sale price
    # ---------------------------------------------------------

    sw_suggested_price = fields.Float(
        string="Suggested Sale Price",
        copy=False,
    )

    sw_sale_margin_percent = fields.Float(
        string="Sales Margin (%)",
        default=0.0,
        help="Margin percentage to calculate sales price from calculated cost.",
    )

    # ---------------------------------------------------------
    # Compute engine
    # ---------------------------------------------------------

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

            vals_to_write = {
                "sw_base_cost": base_cost,
                "sw_cost_rule_id": rule.id if (rule and rule.exists()) else False,
                "sw_final_cost": calculated_cost,
                "sw_suggested_price": suggested_price,
                "standard_price": calculated_cost,
                "list_price": suggested_price,
            }
            super(ProductTemplate, product.with_context(sw_skip_recompute=True)).write(vals_to_write)

    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)
        products._sw_recompute_prices()
        return products

    def write(self, vals):
        if self.env.context.get("sw_skip_recompute"):
            return super().write(vals)

        old_values = {p.id: p.standard_price for p in self}
        res = super().write(vals)

        watched = {"seller_ids", "categ_id", "brand_id", "company_id", "sw_sale_margin_percent", "standard_price"}
        should_recompute = bool(watched.intersection(vals.keys()))

        # Si cambia standard_price manualmente, recalcular aunque venga por otra ruta
        if not should_recompute and "standard_price" in vals:
            should_recompute = True

        if should_recompute:
            products_to_recompute = self
            # Evita bucle cuando standard_price fue escrito por nuestro propio recompute
            if "standard_price" in vals and len(vals.keys()) == 1:
                # Solo recomputar si realmente fue un cambio manual relevante
                manual_changed = self.filtered(lambda p: old_values.get(p.id) != p.standard_price)
                products_to_recompute = manual_changed or self
            products_to_recompute._sw_recompute_prices()

        return res