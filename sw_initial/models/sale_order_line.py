# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    sw_margin = fields.Float(
        string="Marg %",
        digits=(16, 2),
        help="Margen porcentual sobre costo. Al modificarlo, recalcula automáticamente el precio unitario de venta.",
    )

    def _get_cost_in_line_uom(self):
        self.ensure_one()
        if not self.product_id:
            return 0.0
        cost = self.product_id.standard_price or 0.0
        product_uom = self.product_id.uom_id
        line_uom = self.product_uom_id or product_uom
        if product_uom and line_uom and product_uom.category_id == line_uom.category_id:
            return product_uom._compute_price(cost, line_uom)
        return cost

    @api.onchange("sw_margin", "product_id", "product_uom_id")
    def _onchange_sw_margin(self):
        for line in self:
            if not line.product_id:
                continue
            cost_in_uom = line._get_cost_in_line_uom()
            line.price_unit = cost_in_uom * (1.0 + (line.sw_margin or 0.0) / 100.0)

    @api.onchange("price_unit", "product_id", "product_uom_id")
    def _onchange_price_unit_compute_sw_margin(self):
        for line in self:
            if not line.product_id:
                continue
            cost_in_uom = line._get_cost_in_line_uom()
            if cost_in_uom:
                line.sw_margin = ((line.price_unit - cost_in_uom) / cost_in_uom) * 100.0
            else:
                line.sw_margin = 0.0

    @api.onchange("product_uom_id", "product_id")
    def _onchange_product_uom_recompute_price_margin(self):
        for line in self:
            if not line.product_id or not line.product_uom_id:
                continue
            cost_in_uom = line._get_cost_in_line_uom()
            line.price_unit = cost_in_uom * (1.0 + (line.sw_margin or 0.0) / 100.0)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for line in records:
            if line.product_id:
                cost_in_uom = line._get_cost_in_line_uom()
                if cost_in_uom:
                    line.sw_margin = ((line.price_unit - cost_in_uom) / cost_in_uom) * 100.0
        return records

    def write(self, vals):
        res = super().write(vals)
        tracked = {"price_unit", "product_id", "product_uom_id"}
        if tracked.intersection(vals.keys()):
            for line in self:
                if not line.product_id:
                    continue
                cost_in_uom = line._get_cost_in_line_uom()
                if cost_in_uom:
                    line.sw_margin = ((line.price_unit - cost_in_uom) / cost_in_uom) * 100.0
                else:
                    line.sw_margin = 0.0
        return res