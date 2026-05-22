# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    use_supplier_cost = fields.Boolean(
        string='Costo proveedor',
        default=False,
        help='Al guardar, actualiza standard_price con el precio neto del primer proveedor'
    )
    
    sale_margin = fields.Float(
        string='Margen de venta (%)',
        default=0.0,
        help='Porcentaje de margen sobre el costo para calcular el precio de venta'
    )
    
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
            
            supplier_info = self.env['product.supplierinfo'].search([
                ('product_id', '=', product.id),
            ], order='sequence,id', limit=1)
            
            if supplier_info:
                currency_company = self.env.company.currency_id
                currency_supplier = supplier_info.currency_id
                
                if currency_supplier and currency_supplier != currency_company:
                    amount = supplier_info.net_price or supplier_info.price
                    if amount:
                        amount_company = currency_supplier._convert(
                            amount,
                            currency_company,
                            self.env.company,
                            fields.Date.today()
                        )
                    product.supplier_cost_display = amount_company
                else:
                    product.supplier_cost_display = supplier_info.net_price or supplier_info.price
            else:
                product.supplier_cost_display = 0.0

    def crear_vista(self):
        """Crear vista heredada - ejecutar desde Python Console"""
        self.ensure_one()
        
        view = self.env['ir.ui.view'].search([
            ('name', '=', 'product.product.form.cost.supplier'),
        ])
        if view:
            _logger.info('Vista ya existe')
            return True
        
        original = self.env['ir.ui.view'].search([
            ('model', '=', 'product.product'),
            ('type', '=', 'form'),
            ('inherit_id', '=', False),
        ], limit=1)
        
        if not original:
            _logger.warning('Vista original no encontrada')
            return False
        
        self.env['ir.ui.view'].create({
            'name': 'product.product.form.cost.supplier',
            'model': 'product.product',
            'inherit_id': original.id,
            'arch': '''
                <xpath expr="//field[@name='standard_price']" position="after">
                    <field name="use_supplier_cost"/>
                    <field name="supplier_cost_display" string="Costo Proveedor" readonly="1"/>
                    <field name="sale_margin"/>
                </xpath>
                <xpath expr="//field[@name='list_price']" position="attributes">
                    <attribute name="readonly">1</attribute>
                </xpath>
            ''',
            'active': True,
        })
        _logger.info('Vista heredada creada')
        
        # Invalidar caché
        self.env['ir.ui.view'].clear_caches()
        
        return True

    def write(self, vals):
        if 'use_supplier_cost' in vals and vals['use_supplier_cost']:
            supplier_info = self.env['product.supplierinfo'].search([
                ('product_id', '=', self.id),
            ], order='sequence,id', limit=1)
            
            if supplier_info:
                currency_company = self.env.company.currency_id
                currency_supplier = supplier_info.currency_id
                price = supplier_info.net_price or supplier_info.price
                
                if currency_supplier and currency_supplier != currency_company and price:
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
    def _compute_list_price(self):
        for product in self:
            if product.sale_margin and product.standard_price:
                product.list_price = product.standard_price * (1 + product.sale_margin / 100)

    list_price = fields.Float(
        string='Ventas',
        compute='_compute_list_price',
        inverse='_inverse_list_price',
        store=True,
        digits='Product Price'
    )

    def _inverse_list_price(self):
        for product in self:
            if product.standard_price and product.list_price:
                product.sale_margin = ((product.list_price / product.standard_price) - 1) * 100
            else:
                product.sale_margin = 0.0