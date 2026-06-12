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
        required=True,
        domain="[('type', '=', 'consu')]"
    )
    quantity_per_unit = fields.Float(
        string='Cantidad por m²/m³',
        required=True,
        default=1.0
    )
    quantity_type = fields.Selection([
        ('integer', 'Entero'),
        ('fractional', 'Fracción'),
    ], string='Tipo cantidad', default='fractional')
    
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unidad',
        compute='_compute_uom',
        store=True
    )
    
    @api.depends('product_id')
    def _compute_uom(self):
        for rec in self:
            if rec.product_id:
                rec.uom_id = rec.product_id.uom_id.id
            else:
                rec.uom_id = False


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    calculation_method_id = fields.Many2one(
        'calculation.method',
        string='Método de cálculo'
    )
    
    calc_length = fields.Float(string='Largo (mt)', default=0.0)
    calc_width = fields.Float(string='Ancho (mt)', default=0.0)
    calc_height = fields.Float(string='Alto (mt)', default=0.0)
    calc_total = fields.Float(
        string='Total m²/m³',
        compute='_compute_calc_total',
        store=True
    )
    
    @api.depends('calculation_method_id', 'calc_length', 'calc_width', 'calc_height')
    def _compute_calc_total(self):
        for rec in self:
            if rec.calculation_method_id and rec.calculation_method_id.method_type == 'm3':
                rec.calc_total = rec.calc_length * rec.calc_width * rec.calc_height
            elif rec.calculation_method_id:
                rec.calc_total = rec.calc_length * rec.calc_width
            else:
                rec.calc_total = 0.0

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
    
    def action_calc_add_products(self):
        """Agrega los productos calculados"""
        self.ensure_one()
        
        if not self.calculation_method_id or self.calc_total <= 0:
            return True
        
        method = self.calculation_method_id
        
        for line in method.line_ids:
            qty = line.quantity_per_unit * self.calc_total
            
            if line.quantity_type == 'integer':
                qty = int(qty)
            
            self.env['sale.order.line'].create({
                'order_id': self.id,
                'product_id': line.product_id.id,
                'product_uom_qty': qty,
                'price_unit': line.product_id.list_price or 0,
            })
        
        return True


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
        string='Producto destacado',
        domain="[('type', '=', 'consu')]"
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