# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # CAMPOS
    sale_margin = fields.Float(
        string='Margen de Venta (%)',
        default=0.0,
        help='Porcentaje de margen sobre el costo estándar'
    )
    
    list_price_auto = fields.Float(
        string='Precio de Venta Calculado',
        compute='_compute_list_price_auto',
        digits='Product Price'
    )
    
    auto_update_list_price = fields.Boolean(
        string='Actualizar Precio Automáticamente',
        default=True
    )

    @api.depends('standard_price', 'sale_margin')
    def _compute_list_price_auto(self):
        for product in self:
            if product.standard_price and product.sale_margin:
                margin_amount = product.standard_price * (product.sale_margin / 100)
                product.list_price_auto = product.standard_price + margin_amount
            elif product.standard_price:
                product.list_price_auto = product.standard_price
            else:
                product.list_price_auto = 0.0

    def write(self, vals):
        result = super(ProductTemplate, self).write(vals)
        
        if 'sale_margin' in vals or 'standard_price' in vals:
            for product in self:
                if product.auto_update_list_price:
                    product._update_list_price()
        
        return result

    def _update_list_price(self):
        if not self.auto_update_list_price:
            return
        
        if self.standard_price and self.sale_margin:
            margin_amount = self.standard_price * (self.sale_margin / 100)
            new_price = self.standard_price + margin_amount
        elif self.standard_price:
            new_price = self.standard_price
        else:
            return
        
        if new_price > 0:
            try:
                self.write({'list_price': new_price})
                _logger.info(f'list_price actualizado: {new_price}')
            except Exception as e:
                _logger.warning(f'Error: {e}')

    @api.model
    def create(self, vals):
        result = super(ProductTemplate, self).create(vals)
        
        if result.auto_update_list_price and result.sale_margin:
            result._update_list_price()
        
        return result