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