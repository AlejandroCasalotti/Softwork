# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class CosteNetRuleLine(models.Model):
    _name = 'coste.net.rule.line'
    _description = 'Línea de Regla de Costo'
    _order = 'sequence'

    rule_id = fields.Many2one('coste.net.rule', string='Regla', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Secuencia', default=10)
    name = fields.Char(string='Descripción', required=True)
    
    line_type = fields.Selection([
        ('discount', 'Descuento (%)'),
        ('surcharge', 'Recargo (%)'),
        ('fixed', 'Tarifa Fija'),
    ], string='Tipo', required=True, default='discount')
    
    value = fields.Float(string='Valor', required=True)

    @api.constrains('value')
    def _check_value(self):
        for line in self:
            if line.value < 0:
                raise UserError(f'El valor no puede ser negativo: {line.name}')