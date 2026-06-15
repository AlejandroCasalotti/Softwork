# -*- coding: utf-8 -*-

from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    price_unit_base = fields.Monetary(
        string="Precio unitario base",
        help="Guarda el price_unit previo al recargo del método de pago. Se usa para revertir cuando el método se elimina.",
        copy=False,
    )

    price_unit_currency_id = fields.Many2one(
        "res.currency",
        related="order_id.currency_id",
        store=True,
        readonly=True,
    )

    # Ajuste para que price_unit_base use la currency del order.
    @api.model
    def _register_hook(self):
        # noop: placeholder para mantener compatibilidad
        return super()._register_hook()

    def _get_base_price_if_needed(self):
        for line in self:
            if not line.price_unit_base:
                line.price_unit_base = line.price_unit

    def _apply_percentage_on_price(self, pct):
        """Aplica pct sobre el precio base sin acumulación.

        Precio aumentado = price_unit_base * (1 + pct/100)
        Cuando pct = 0, vuelve al base.
        """
        self.ensure_one() if len(self) == 1 else None

        for line in self:
            # Si no hay método, volver siempre al precio base original
            # y limpiar base para que el próximo método tome el precio actual como nuevo base.
            if not pct:
                if line.price_unit_base:
                    line.price_unit = line.price_unit_base
                    line.price_unit_base = 0.0
                continue

            # Con método: fijar base solo una vez y aplicar sobre base (no acumulable).
            line._get_base_price_if_needed()
            base = line.price_unit_base
            factor = 1.0 + (pct or 0.0) / 100.0
            line.price_unit = base * factor

    @api.onchange("order_id.payment_method_id")
    def _onchange_order_payment_method_id(self):
        for line in self:
            if not line.order_id:
                continue
            pct = line.order_id.payment_method_id.percentage_increase if line.order_id.payment_method_id else 0.0
            line._apply_percentage_on_price(pct)

    def write(self, vals):
        # Si el usuario edita price_unit manualmente cuando no hay método,
        # refrescamos base.
        res = super().write(vals)

        # Recalcular/ajustar base cuando cambia el price_unit por el usuario.
        # (En escenarios normales, el recálculo usa la base y setea price_unit.)
        if "price_unit" in vals and "order_id" not in vals:
            for line in self:
                if not line.order_id.payment_method_id:
                    line.price_unit_base = line.price_unit

        return res

