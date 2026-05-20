# -*- coding: utf-8 -*-

# models/product_supplierinfo.py
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ProductSupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    # Margen de venta
    sale_margin = fields.Float(
        string='Margen de Venta (%)',
        digits='Product Price',
        default=0.0,
    )
    
    # Reglas de costo
    rule_ids = fields.Many2many(
        'cost.rule',
        'cost_rule_supplierinfo_rel',
        'supplierinfo_id',
        'rule_id',
        string='Reglas de Costo',
    )
    
    # Campos calculados
    calculated_discount = fields.Float(
        string='Descuentos',
        digits='Product Price',
        compute='_compute_calculated_prices',
        store=True,
    )
    
    calculated_extra = fields.Float(
        string='Tarifas',
        digits='Product Price',
        compute='_compute_calculated_prices',
        store=True,
    )
    
    final_cost = fields.Float(
        string='Costo Final',
        digits='Product Price',
        compute='_compute_calculated_prices',
        store=True,
    )
    
    _internal_update = False

    @api.depends('price', 'rule_ids', 'rule_ids.rule_type', 
                 'rule_ids.rule_mode', 'rule_ids.rule_value')
    def _compute_calculated_prices(self):
        for record in self:
            discount = 0.0
            extra = 0.0
            base_price = record.price or 0.0
            
            for rule in record.rule_ids.filtered('active'):
                if rule.rule_type == 'discount':
                    if rule.rule_mode == 'percentage':
                        discount += base_price * (rule.rule_value / 100.0)
                    else:
                        discount += rule.rule_value
                else:
                    if rule.rule_mode == 'percentage':
                        extra += base_price * (rule.rule_value / 100.0)
                    else:
                        extra += rule.rule_value
            
            record.calculated_discount = discount
            record.calculated_extra = extra
            record.final_cost = base_price - discount + extra

    def _update_product_prices(self):
        """Actualiza el standard_price y list_price del producto"""
        if self._internal_update:
            return
            
        for record in self:
            if not record.product_id:
                continue
                
            product = record.product_id
            
            try:
                self._internal_update = True
                
                # Actualizar standard_price con el costo final
                if record.final_cost:
                    product.standard_price = record.final_cost
                    _logger.info(f'Updated standard_price to {record.final_cost}')
                
                # Actualizar list_price con el margen
                if record.sale_margin > 0:
                    cost = product.standard_price or record.final_cost or record.price or 0.0
                    new_list_price = cost * (1 + record.sale_margin / 100.0)
                    product.list_price = new_list_price
                    _logger.info(f'Updated list_price to {new_list_price} with margin {record.sale_margin}%')
                    
            finally:
                self._internal_update = False

    @api.onchange('price', 'rule_ids', 'sale_margin')
    def _onchange_update_prices(self):
        self._update_product_prices()

    def write(self, vals):
        result = super(ProductSupplierInfo, self).write(vals)
        if any(field in vals for field in ['price', 'sale_margin', 'rule_ids']):
            for record in self:
                record._update_product_prices()
        return result

    @api.model_create_multi
    def create(self, vals_list):
        records = super(ProductSupplierInfo, self).create(vals_list)
        for record in records:
            record._update_product_prices()
        return records