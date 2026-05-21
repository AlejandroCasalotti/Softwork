# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    # Campo para activar costo automático desde proveedor
    use_supplier_cost = fields.Boolean(
        string='Costo proveedor',
        default=False,
        help='Al guardar, actualiza standard_price con el precio neto del primer proveedor'
    )
    
    # Margen de venta en porcentaje
    sale_margin = fields.Float(
        string='Margen de venta (%)',
        default=0.0,
        help='Porcentaje de margen sobre el costo para calcular el precio de venta'
    )
    
    # Campo para mostrar el costo del proveedor (solo lectura)
    supplier_cost_display = fields.Float(
        string='Costo Proveedor',
        compute='_compute_supplier_cost_display',
        digits='Product Price'
    )

    @api.depends('use_supplier_cost')
    def _compute_supplier_cost_display(self):
        for product in self:
            if not product.use_supplier_cost:
                product.supplier_cost_display = 0.0
                continue
            
            # Obtener el primer proveedor del producto
            supplier_info = self.env['product.supplierinfo'].search([
                ('product_id', '=', product.id),
            ], order='sequence,id', limit=1)
            
            if supplier_info:
                # Convertir el precio neto a la moneda de la empresa
                currency_company = self.env.company.currency_id
                currency_supplier = supplier_info.currency_id
                
                if currency_supplier and currency_supplier != currency_company:
                    # Convertir el precio neto a la moneda de la empresa
                    amount_company = supplier_info.net_price
                    if supplier_info.net_price:
                        amount_company = currency_supplier._convert(
                            supplier_info.net_price,
                            currency_company,
                            self.env.company,
                            fields.Date.today()
                        )
                    product.supplier_cost_display = amount_company
                else:
                    product.supplier_cost_display = supplier_info.net_price or supplier_info.price
            else:
                product.supplier_cost_display = 0.0

    def write(self, vals):
        """Al guardar, actualizar standard_price si está marcado"""
        if 'use_supplier_cost' in vals and vals['use_supplier_cost']:
            # Obtener el primer proveedor
            supplier_info = self.env['product.supplierinfo'].search([
                ('product_id', '=', self.id),
            ], order='sequence,id', limit=1)
            
            if supplier_info:
                # Convertir el precio a la moneda de la empresa
                currency_company = self.env.company.currency_id
                currency_supplier = supplier_info.currency_id
                
                # Usar net_price si existe, sino el price
                price = supplier_info.net_price if supplier_info.net_price else supplier_info.price
                
                if currency_supplier and currency_supplier != currency_company and price:
                    # Convertir el precio a la moneda de la empresa
                    new_cost = currency_supplier._convert(
                        price,
                        currency_company,
                        self.env.company,
                        fields.Date.today()
                    )
                else:
                    new_cost = price
                
                vals['standard_price'] = new_cost
                _logger.info(f'Actualizando standard_price a {new_cost} para {self.name}')
        
        return super().write(vals)

    @api.depends('standard_price', 'sale_margin')
    def _compute_product_margin(self):
        """Calcula el list_price basado en standard_price + margen"""
        for product in self:
            if product.sale_margin and product.standard_price:
                # list_price = standard_price + (standard_price * margen / 100)
                product.list_price = product.standard_price * (1 + product.sale_margin / 100)
            # Si no hay margen, no modificamos list_price

    # Sobreescribir list_price para que sea calculado
    list_price = fields.Float(
        string='Ventas',
        compute='_compute_product_margin',
        inverse='_inverse_list_price',
        store=True,
        digits='Product Price'
    )

    def _inverse_list_price(self):
        """Si el usuario modifica list_price manualmente, calcular el margen"""
        for product in self:
            if product.standard_price and product.list_price:
                product.sale_margin = ((product.list_price / product.standard_price) - 1) * 100
            else:
                product.sale_margin = 0.0