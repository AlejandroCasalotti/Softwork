# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    payment_method_id = fields.Many2one(
        "sale.payment.method",
        string="Método de pago",
        copy=False,
    )

    def write(self, vals):
        changing_method = "payment_method_id" in vals
        if changing_method:
            for order in self:
                if order.state != "draft":
                    raise UserError(_("No se puede modificar el método de pago si el pedido no está en borrador."))

        res = super().write(vals)

        # También aplicar en backend (no solo onchange de UI), para evitar acumulación
        # y garantizar reversión al precio original al quitar método.
        if changing_method:
            self._apply_price_increase_on_lines()

        return res

    def action_confirm(self):
        res = super().action_confirm()
        return res

    @api.onchange("payment_method_id")
    def _onchange_payment_method_id(self):
        # Evitamos recalcular aquí para no duplicar efecto con write() al guardar.
        # El recálculo definitivo se aplica en backend en write().
        return

    def _apply_price_increase_on_lines(self):
        for order in self:
            method = order.payment_method_id
            pct = method.percentage_increase if method else 0.0

            for line in order.order_line:
                line._apply_percentage_on_price(pct)

