# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    # Margen de venta en porcentaje
    sale_margin = fields.Float(
        string='Margen de venta (%)',
        default=0.0,
    )
    
    # Campo para mostrar el costo del proveedor
    cost_from_supplier = fields.Float(
        string='Costo Proveedor',
        digits='Product Price',
    )

    @api.model_create_single
    def create(self, vals):
        """Al crear, tomar el precio del primer proveedor"""
        # Buscar proveedor
        if 'cost_from_supplier' not in vals or not vals.get('cost_from_supplier'):
            supplier_info = self.env['product.supplierinfo'].search([
                ('product_id.product_tmpl_id', '=', vals.get('product_tmpl_id', 0)),
            ], order='sequence,id', limit=1)
            
            if supplier_info:
                # Usar net_price si existe, sinon price
                vals['cost_from_supplier'] = supplier_info.net_price or supplier_info.price
                vals['standard_price'] = vals['cost_from_supplier']
                _logger.info(f'Standard price establecido: {vals["standard_price"]}')
        
        return super().create(vals)

    def write(self, vals):
        """Al guardar, actualizar standard_price si no hay valor"""
        product = self
        
        # Si no tiene cost_from_supplier, buscar proveedor
        if not product.cost_from_supplier:
            supplier_info = self.env['product.supplierinfo'].search([
                ('product_id', '=', product.id),
            ], order='sequence,id', limit=1)
            
            if supplier_info:
                cost = supplier_info.net_price or supplier_info.price
                vals['cost_from_supplier'] = cost
                vals['standard_price'] = cost
                _logger.info(f'Standard price actualizado: {cost}')
        
        return super().write(vals)

    @api.depends('standard_price', 'sale_margin')
    def _compute_product_margin(self):
        """Calcula list_price desde standard_price + margen"""
        for product in self:
            if product.sale_margin and product.standard_price:
                # list_price = standard_price + (standard_price * margen / 100)
                product.list_price = product.standard_price * (1 + product.sale_margin / 100)
                _logger.info(f'List price calculado: {product.list_price}')

    # Modificar list_price para que sea calculado
    list_price = fields.Float(
        string='Ventas',
        compute='_compute_product_margin',
        store=True,
    )