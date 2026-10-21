# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class SalePaymentMethod(models.Model):
    _name = "sale.payment.method"
    _description = "Método de pago (recargo % en Orden de venta)"
    _order = "sequence, id"

    name = fields.Char(string="Nombre", required=True, translate=True)
    description = fields.Text(string="Descripción")
    percentage_increase = fields.Float(string="% a aumentar", required=True, default=0.0)
    sequence = fields.Integer(string="Secuencia", default=10)

    @api.constrains("percentage_increase")
    def _check_percentage_increase(self):
        for rec in self:
            if rec.percentage_increase < 0:
                raise ValidationError(_("El porcentaje debe ser >= 0."))