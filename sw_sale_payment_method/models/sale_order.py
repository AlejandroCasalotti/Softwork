# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = "sale.order"

    payment_method_id = fields.Many2one(
        "sale.payment.method",
        string="Método de pago",
        copy=False,
    )

    def action_confirm(self):
        res = super().action_confirm()
        return res

    @api.onchange("payment_method_id")
    def _onchange_payment_method_id(self):
        # Se recalculan líneas existentes en el formulario (también aplica a nuevas líneas
        # vía onchange en line).
        self._apply_price_increase_on_lines()

    def _apply_price_increase_on_lines(self):
        for order in self:
            method = order.payment_method_id
            pct = method.percentage_increase if method else 0.0

            for line in order.order_line:
                line._apply_percentage_on_price(pct)

