# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    sw_margin = fields.Float(
        string="Marg %",
        digits=(16, 2),
        help="Margen porcentual sobre costo. Al modificarlo, recalcula automáticamente el precio unitario de venta.",
    )

    @api.onchange("sw_margin", "product_id")
    def _onchange_sw_margin(self):
        for line in self:
            if not line.product_id:
                continue
            cost = line.product_id.standard_price or 0.0
            line.price_unit = cost * (1.0 + (line.sw_margin or 0.0) / 100.0)

    @api.onchange("price_unit", "product_id")
    def _onchange_price_unit_compute_sw_margin(self):
        for line in self:
            if not line.product_id:
                continue
            cost = line.product_id.standard_price or 0.0
            if cost:
                line.sw_margin = ((line.price_unit - cost) / cost) * 100.0
            else:
                line.sw_margin = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for line in records:
            if line.product_id:
                cost = line.product_id.standard_price or 0.0
                if cost:
                    line.sw_margin = ((line.price_unit - cost) / cost) * 100.0
        return records

    def write(self, vals):
        res = super().write(vals)
        tracked = {"price_unit", "product_id"}
        if tracked.intersection(vals.keys()):
            for line in self:
                if not line.product_id:
                    continue
                cost = line.product_id.standard_price or 0.0
                if cost:
                    line.sw_margin = ((line.price_unit - cost) / cost) * 100.0
                else:
                    line.sw_margin = 0.0
        return res