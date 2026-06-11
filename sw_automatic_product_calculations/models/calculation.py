# -*- coding: utf-8 -*-

from odoo import models, fields, api
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
    _order = 'sequence'

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
        string='Cantidad por unidad',
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
        """Abre el wizard de cálculo"""
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
        required=True
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
        string='Total',
        compute='_compute_total',
        store=True
    )
    
    result_ids = fields.One2many(
        'calculation.wizard.result',
        'wizard_id',
        string='Resultados',
        readonly=True
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

    def compute_results(self):
        self.ensure_one()
        
        self.result_ids.unlink()
        
        if not self.method_id or self.total_surface <= 0:
            return
        
        results = []
        
        for line in self.method_id.line_ids:
            qty = line.quantity_per_unit * self.total_surface
            
            if line.quantity_type == 'integer':
                qty = int(qty)
            
            results.append((0, 0, {
                'product_id': line.product_id.id,
                'quantity': qty,
                'uom_id': line.uom_id.id,
            }))
        
        if self.featured_product_id and self.featured_quantity > 0:
            results.append((0, 0, {
                'product_id': self.featured_product_id.id,
                'quantity': self.featured_quantity,
                'uom_id': self.featured_product_id.uom_id.id if self.featured_product_id.uom_id else False,
            }))
        
        self.result_ids = results
        return True

    def add_products(self):
        self.ensure_one()
        
        if not self.order_id or not self.result_ids:
            return
        
        order_lines = []
        for result in self.result_ids:
            if result.product_id:
                order_lines.append((0, 0, {
                    'order_id': self.order_id.id,
                    'product_id': result.product_id.id,
                    'product_uom_qty': result.quantity,
                    'product_uom': result.uom_id.id if result.uom_id else result.product_id.uom_id.id,
                    'price_unit': result.product_id.list_price,
                    'name': result.product_id.name,
                }))
        
        self.order_id.order_line = order_lines
        
        return {'type': 'ir.actions.act_window_close'}


class CalculationWizardResult(models.TransientModel):
    _name = 'calculation.wizard.result'
    _description = 'Resultado de Cálculo'

    wizard_id = fields.Many2one('calculation.wizard', string='Wizard')
    product_id = fields.Many2one('product.product', string='Producto')
    quantity = fields.Float(string='Cantidad')
    uom_id = fields.Many2one('uom.uom', string='UoM')