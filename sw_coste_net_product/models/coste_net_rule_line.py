# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import decimal


class CosteNetRuleLine(models.Model):
    _name = 'coste.net.rule.line'
    _description = 'Línea de Regla de Costo'
    _order = 'sequence'

    rule_id = fields.Many2one(
        'coste.net.rule',
        string='Regla',
        required=True,
        ondelete='cascade',
    )
    
    sequence = fields.Integer(
        string='Secuencia',
        default=10,
        help='Orden de aplicación (se aplica en order ascendente)',
    )
    
    name = fields.Char(
        string='Descripción',
        required=True,
        help='Nombre descriptivo de esta línea',
    )
    
    line_type = fields.Selection([
        ('discount', 'Descuento (%)'),
        ('surcharge', 'Recargo (%)'),
        ('fixed', 'Tarifa Fija'),
    ],
        string='Tipo',
        required=True,
        default='discount',
    )
    
    value = fields.Float(
        string='Valor',
        required=True,
        help='Porcentaje o monto fijo según el tipo',
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Empresa',
        related='rule_id.supplierinfo_id.company_id',
        store=True,
    )

    @api.constrains('value')
    def _check_value(self):
        for line in self:
            if line.line_type in ('discount', 'surcharge') and line.value < 0:
                raise UserError(f'El valor no puede ser negativo en: {line.name}')
            if line.line_type == 'fixed' and line.value < 0:
                raise UserError(f'La tarifa fija no puede ser negativa en: {line.name}')

    @api.constrains('line_type')
    def _check_line_type(self):
        for line in self:
            if not line.line_type:
                raise UserError('Debe seleccionar un tipo de línea.')