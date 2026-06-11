# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class CalculationMethod(models.Model):
    _name = 'calculation.method'
    _description = 'Método de Cálculo'
    _order = 'name'

    name = fields.Char(string='Nombre del método', required=True)
    method_type = fields.Selection([
        ('m2', 'Metros Cuadrados (m²)'),
        ('m3', 'Metros Cúbicos (m³)'),
    ], string='Tipo de método', required=True)
    active = fields.Boolean(string='Activo', default=True)
    line_ids = fields.One2many(
        'calculation.method.line', 'method_id',
        string='Productos', copy=True
    )


class CalculationMethodLine(models.Model):
    _name = 'calculation.method.line'
    _description = 'Línea de Método de Cálculo'

    method_id = fields.Many2one(
        'calculation.method',
        string='Método',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(string='#', default=10)
    product_id = fields.Many2one(
        'product.product',
        string='Producto',
        required=True
    )
    quantity_per_unit = fields.Float(
        string='Cantidad por m²/m³',
        required=True,
        default=1.0
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unidad de medida',
        required=True
    )
    quantity_type = fields.Selection([
        ('integer', 'Entero'),
        ('fractional', 'Fracción'),
    ], string='Tipo cantidad', default='fractional')


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_open_calculation_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cálculo Automático',
            'res_model': 'calculation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.id,
            },
        }


class CalculationWizard(models.TransientModel):
    _name = 'calculation.wizard'
    _description = 'Wizard Cálculo Automático'

    order_id = fields.Many2one('sale.order', string='Orden de Venta')
    method_id = fields.Many2one(
        'calculation.method',
        string='Método de cálculo',
        required=True,
        domain="[('active', '=', True)]"
    )
    method_type = fields.Selection([
        ('m2', 'Metros Cuadrados (m²)'),
        ('m3', 'Metros Cúbicos (m³)'),
    ])
    
    length = fields.Float(string='Largo (mt)', default=0.0)
    width = fields.Float(string='Ancho (mt)', default=0.0)
    height = fields.Float(string='Alto (mt)', default=0.0)
    
    featured_product_id = fields.Many2one(
        'product.product',
        string='Producto destacado'
    )
    featured_quantity = fields.Float(
        string='Cantidad destacada',
        default=0.0
    )
    
    total_surface = fields.Float(
        string='Total m²/m³',
        compute='_compute_total',
        store=True
    )

    @api.depends('method_id', 'length', 'width', 'height')
    def _compute_total(self):
        for rec in self:
            if rec.method_type == 'm3':
                rec.total_surface = rec.length * rec.width * rec.height
            else:
                rec.total_surface = rec.length * rec.width

    @api.onchange('method_id')
    def _onchange_method_id(self):
        if self.method_id:
            self.method_type = self.method_id.method_type

    def add_products(self):
        self.ensure_one()
        
        if not self.order_id:
            return {'type': 'ir.actions.act_window_close'}
        
        if self.total_surface <= 0:
            return {'type': 'ir.actions.act_window_close'}
        
        for line in self.method_id.line_ids:
            qty = line.quantity_per_unit * self.total_surface
            
            if line.quantity_type == 'integer':
                qty = int(qty)
            
            self.env['sale.order.line'].create({
                'order_id': self.order_id.id,
                'product_id': line.product_id.id,
                'product_uom_qty': qty,
                'price_unit': line.product_id.list_price or 0,
            })
        
        if self.featured_product_id and self.featured_quantity > 0:
            self.env['sale.order.line'].create({
                'order_id': self.order_id.id,
                'product_id': self.featured_product_id.id,
                'product_uom_qty': self.featured_quantity,
                'price_unit': self.featured_product_id.list_price or 0,
            })
        
        return {'type': 'ir.actions.act_window_close'}