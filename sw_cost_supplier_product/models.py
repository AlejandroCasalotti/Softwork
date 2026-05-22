# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError

# Heredar product.product directamente
class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    # Campo para activar costo automático desde proveedor
    use_supplier_cost = fields.Boolean(
        string='Costo proveedor',
        default=False,
        copy=False,
    )
    
    # Margen de venta en porcentaje
    sale_margin = fields.Float(
        string='Margen de venta (%)',
        default=0.0,
        copy=False,
    )
    
    # Campo para mostrar el costo del proveedor (solo lectura)
    supplier_cost_display = fields.Float(
        string='Costo Proveedor',
        compute='_compute_supplier_cost_display',
        digits='Product Price',
        store=False,
    )

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
                currency_company = self.env.company.currency_id
                currency_supplier = supplier_info.currency_id
                
                # Usar net_price si existe, sino price
                amount = supplier_info.net_price or supplier_info.price
                
                if currency_supplier and currency_supplier != currency_company and amount:
                    try:
                        amount_company = currency_supplier._convert(
                            amount,
                            currency_company,
                            self.env.company,
                            fields.Date.today()
                        )
                        product.supplier_cost_display = amount_company
                    except:
                        product.supplier_cost_display = amount
                else:
                    product.supplier_cost_display = amount
            else:
                product.supplier_cost_display = 0.0

    def write(self, vals):
        """Al guardar, actualizar standard_price si está marcado"""
        if vals.get('use_supplier_cost'):
            # Buscar proveedor
            supplier_info = self.env['product.supplierinfo'].search([
                ('product_id', '=', self.id),
            ], order='sequence,id', limit=1)
            
            if supplier_info:
                currency_company = self.env.company.currency_id
                currency_supplier = supplier_info.currency_id
                price = supplier_info.net_price or supplier_info.price
                
                if currency_supplier and currency_supplier != currency_company and price:
                    try:
                        new_cost = currency_supplier._convert(
                            price,
                            currency_company,
                            self.env.company,
                            fields.Date.today()
                        )
                    except:
                        new_cost = price
                else:
                    new_cost = price
                
                vals['standard_price'] = new_cost
        
        return super().write(vals)

    # Sobrescribir list_price para calcular desde sale_margin
    @api.depends('standard_price', 'sale_margin')
    def _compute_list_price(self):
        for product in self:
            if product.sale_margin and product.standard_price:
                product.list_price = product.standard_price * (1 + product.sale_margin / 100)
            elif not product.list_price:
                # Si no tiene precio, usar el estándar
                pass

    # Mantener list_price原有的
    def _inverse_list_price(self):
        pass