# -*- coding: utf-8 -*-

from odoo import models, fields, api


class CostRule(models.Model):
    _name = 'cost.rule'
    _description = 'Regla de Costo'
    
    name = fields.Char(string='Nombre', required=True)
    active = fields.Boolean(string='Activa', default=True)
    rule_type = fields.Selection([
        ('discount', 'Descuento'),
        ('extra', 'Tarifa Extra'),
    ], string='Tipo', required=True, default='extra')
    rule_mode = fields.Selection([
        ('percentage', 'Porcentaje'),
        ('fixed', 'Monto Fijo'),
    ], string='Modo', required=True, default='percentage')
    rule_value = fields.Float(string='Valor', required=True, default=0.0)
    description = fields.Text(string='Descripción')
    supplier_id = fields.Many2one('res.partner', string='Proveedor',
        domain=[('supplier_rank', '>', 0)])


class ProductSupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    # Margen de venta
    sale_margin = fields.Float(
        string='Margen (%)',
        digits='Product Price',
        default=0.0,
    )
    
    # Reglas de costo
    rule_ids = fields.Many2many(
        'cost.rule',
        'cost_rule_supplier_rel',
        'supplierinfo_id',
        'rule_id',
        string='Reglas',
    )
    
    # Costo final calculado (sin almacenar para evitar problemas)
    final_cost = fields.Float(
        string='Costo Final',
        compute='_compute_final_cost',
        store=False,
    )

    @api.depends('price', 'rule_ids.rule_type', 'rule_ids.rule_mode', 'rule_ids.rule_value')
    def _compute_final_cost(self):
        for record in self:
            discount = 0.0
            extra = 0.0
            base = record.price or 0.0
            
            for rule in record.rule_ids.filtered('active'):
                if rule.rule_type == 'discount':
                    if rule.rule_mode == 'percentage':
                        discount += base * (rule.rule_value / 100.0)
                    else:
                        discount += rule.rule_value
                else:
                    if rule.rule_mode == 'percentage':
                        extra += base * (rule.rule_value / 100.0)
                    else:
                        extra += rule.rule_value
            
            record.final_cost = base - discount + extra

    def _sync_to_product(self):
        """Sincroniza el costo final al standard_price del producto"""
        for record in self:
            if record.product_id and record.final_cost:
                record.product_id.standard_price = record.final_cost
                
                # Aplicar margen al list_price
                if record.sale_margin > 0:
                    cost = record.product_id.standard_price
                    record.product_id.list_price = cost * (1 + record.sale_margin / 100.0)

    @api.onchange('price', 'rule_ids', 'sale_margin')
    def _onchange_sync(self):
        self._sync_to_product()