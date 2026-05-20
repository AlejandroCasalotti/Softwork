# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class CosteNetRule(models.Model):
    _name = 'coste_net_rule'
    _description = 'Regla de Costo Neto'
    _order = 'sequence'

    name = fields.Char(string='Nombre', required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True, string='Activa')
    
    line_ids = fields.One2many(
        'coste_net_rule_line', 'rule_id',
        string='Lineas', copy=True
    )
    
    total_discount = fields.Float(
        string='Total Descuento (%)',
        compute='_compute_totals',
        store=True
    )
    total_surcharge = fields.Float(
        string='Total Recargo (%)',
        compute='_compute_totals',
        store=True
    )
    total_fixed = fields.Float(
        string='Total Fijo',
        compute='_compute_totals',
        store=True
    )

    @api.depends('line_ids.value', 'line_ids.line_type')
    def _compute_totals(self):
        for rule in self:
            discount = surcharge = fixed = 0.0
            for line in rule.line_ids:
                if line.line_type == 'discount':
                    discount += line.value
                elif line.line_type == 'surcharge':
                    surcharge += line.value
                elif line.line_type == 'fixed':
                    fixed += line.value
            rule.total_discount = discount
            rule.total_surcharge = surcharge
            rule.total_fixed = fixed


class CosteNetRuleLine(models.Model):
    _name = 'coste_net_rule_line'
    _description = 'Linea de Regla de Costo'
    _order = 'sequence'

    rule_id = fields.Many2one(
        'coste_net_rule',
        string='Regla',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Descripcion', required=True)
    
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