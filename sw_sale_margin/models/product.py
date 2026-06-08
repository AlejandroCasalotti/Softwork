# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # ============================================================
    # CAMPOS
    # ============================================================
    
    sale_margin = fields.Float(
        string='Margen de Venta (%)',
        default=0.0,
        help='Porcentaje de margen sobre el costo estándar'
    )
    
    list_price_auto = fields.Float(
        string='Precio de Venta Calculado',
        compute='_compute_list_price_auto',
        digits='Product Price',
        help='Precio de venta automático: standard_price + margen'
    )
    
    auto_update_list_price = fields.Boolean(
        string='Actualizar Precio Automáticamente',
        default=True,
        help='Al guardar, actualiza el list_price con el margen de venta'
    )

    # ============================================================
    # COMPUTE
    # ============================================================
    
    @api.depends('standard_price', 'sale_margin')
    def _compute_list_price_auto(self):
        """Calcula el precio de venta automático"""
        for product in self:
            if product.standard_price and product.sale_margin:
                margin_amount = product.standard_price * (product.sale_margin / 100)
                product.list_price_auto = product.standard_price + margin_amount
            elif product.standard_price:
                product.list_price_auto = product.standard_price
            else:
                product.list_price_auto = 0.0

    # ============================================================
    # OVERRIDE WRITE
    # ============================================================
    
    def write(self, vals):
        """Override write para actualizar list_price"""
        result = super(ProductTemplate, self).write(vals)
        
        # Actualizar list_price si está habilitado
        if ('sale_margin' in vals or 'standard_price' in vals) and self:
            self._update_list_price()
        
        return result

    # ============================================================
    # MÉTODO PARA ACTUALIZAR LIST_PRICE
    # ============================================================
    
    def _update_list_price(self):
        """
        Actualiza el list_price con el margen de venta
        
        Fórmula: list_price = standard_price + (standard_price * sale_margin / 100)
        """
        for product in self:
            # Verificar si está habilitado
            if not product.auto_update_list_price:
                continue
            
            # Calcular nuevo precio
            if product.standard_price and product.sale_margin:
                margin_amount = product.standard_price * (product.sale_margin / 100)
                new_price = product.standard_price + margin_amount
            elif product.standard_price:
                new_price = product.standard_price
            else:
                continue
            
            # Actualizar list_price
            if new_price > 0:
                try:
                    product.write({'list_price': new_price})
                    _logger.info(f'list_price actualizado: {new_price}')
                except Exception as e:
                    _logger.warning(f'Error actualizando list_price: {e}')


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # ============================================================
    # COMPUTE PARA VARIANTES
    # ============================================================
    
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
        """Calcula el precio de venta automático"""
        for product in self:
            if product.standard_price and product.sale_margin:
                margin_amount = product.standard_price * (product.sale_margin / 100)
                product.list_price_auto = product.standard_price + margin_amount
            elif product.standard_price:
                product.list_price_auto = product.standard_price
            else:
                product.list_price_auto = 0.0

    def write(self, vals):
        """Override write para actualizar list_price"""
        result = super(ProductProduct, self).write(vals)
        
        # Actualizar list_price si está habilitado
        if 'sale_margin' in vals or 'standard_price' in vals:
            self._update_list_price()
        
        return result

    def _update_list_price(self):
        """Actualiza el list_price"""
        for product in self:
            if not product.auto_update_list_price:
                continue
            
            if product.standard_price and product.sale_margin:
                margin_amount = product.standard_price * (product.sale_margin / 100)
                new_price = product.standard_price + margin_amount
            elif product.standard_price:
                new_price = product.standard_price
            else:
                continue
            
            if new_price > 0:
                try:
                    product.write({'list_price': new_price})
                except Exception as e:
                    _logger.warning(f'Error: {e}')