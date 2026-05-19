# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductSupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'
    
    rule_id = fields.Many2one(
        'coste.net.rule',
        string='Regla de Costo Neto',
    )
    
    price_net = fields.Float(
        string='Costo Neto',
        compute='_compute_price_net',
        digits='Product Price',
    )
    
    has_rule = fields.Boolean(
        string='Tiene Regla',
        compute='_compute_has_rule',
        store=True,
    )

    @api.depends('rule_id')
    def _compute_has_rule(self):
        for record in self:
            record.has_rule = bool(record.rule_id)

    @api.depends('price', 'rule_id', 'rule_id.line_ids.line_type', 'rule_id.line_ids.value')
    def _compute_price_net(self):
        for record in self:
            if not record.rule_id or not record.rule_id.line_ids:
                record.price_net = record.price
                continue
            
            current_price = record.price
            lines = record.rule_id.line_ids.sorted(key=lambda x: x.sequence)
            
            for line in lines:
                if line.line_type == 'discount':
                    current_price -= current_price * (line.value / 100)
                elif line.line_type == 'surcharge':
                    current_price += current_price * (line.value / 100)
                elif line.line_type == 'fixed':
                    current_price += line.value
            
            record.price_net = max(round(current_price, 2), 0.0)