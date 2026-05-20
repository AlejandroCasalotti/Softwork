# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CosteNetRule(models.Model):
    _name = 'coste.net.rule'
    _description = 'Regla de Costo Neto'
    _order = 'sequence'
    _rec_name = 'name'

    name = fields.Char(string='Nombre de la Regla', required=True)
    sequence = fields.Integer(string='Secuencia', default=10)
    active = fields.Boolean(string='Activa', default=True)
    
    line_ids = fields.One2many(
        'coste.net.rule.line', 'rule_id', 
        string='Líneas de Regla', copy=True
    )
    
    supplierinfo_id = fields.Many2one(
        'product.supplierinfo', string='Proveedor de Producto'
    )
    
    total_discount = fields.Float(
        string='Total Descuento (%)', compute='_compute_totals', store=True
    )
    total_surcharge = fields.Float(
        string='Total Recargo (%)', compute='_compute_totals', store=True
    )
    total_fixed = fields.Float(
        string='Total Tarifas Fijas', compute='_compute_totals', store=True
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