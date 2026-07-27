# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
import math

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

    def _apply_rounding_by_type(self, qty):
        self.ensure_one()
        qty = float(qty or 0.0)
        if self.quantity_type != 'integer':
            return qty
        packaging = float(self.packaging_equivalent or 0.0)
        if packaging > 0:
            return float(math.ceil(qty / packaging) * packaging)
        return float(math.ceil(qty))

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
    quantity_type = fields.Selection([
        ('integer', 'Entero'),
        ('fractional', 'Fracción'),
    ], string='Tipo cantidad', default='fractional')
    packaging_equivalent = fields.Float(
        string='Equivalente a embalaje',
        default=0.0,
        help='Si Tipo cantidad es Entero y este valor > 0, redondea al múltiplo superior de este embalaje.',
    )
    
    uom_id = fields.Many2one(
        'uom.uom',
        string='Unidad',
        compute='_compute_uom',
        store=True,
        readonly=True
    )
    
    @api.depends('product_id')
    def _compute_uom(self):
        for rec in self:
            rec.uom_id = rec.product_id.uom_id.id if rec.product_id else False


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    website_selected_packaging_id = fields.Many2one(
        'product.template.attribute.value',
        string='Embalaje visible en web',
        domain="[('attribute_id.name', 'ilike', 'embalaje'), ('product_tmpl_id', '=', id)]",
        help='Si se define, este valor de atributo (Embalaje) será el usado/mostrado para la venta web de este producto.',
    )
    website_packaging_qty = fields.Float(
        string='Cantidad del embalaje web',
        compute='_compute_website_packaging_qty',
        store=False,
        readonly=True,
    )

    website_enable_calculator = fields.Boolean(
        string='Habilitar cálculo en sitio web',
        default=False,
        help='Si está activo, este producto mostrará el bloque de cálculo automático en la web.',
    )
    website_calculation_method_id = fields.Many2one(
        'calculation.method',
        string='Método de cálculo web',
        domain="[('active', '=', True)]",
        help='Método fijo para cálculo en la vista del producto del sitio web.',
    )
    website_calculation_method_ids = fields.Many2many(
        'calculation.method',
        'product_template_calculation_method_rel',
        'product_tmpl_id',
        'method_id',
        string='Métodos de cálculo web (selección cliente)',
        domain="[('active', '=', True)]",
        help='Métodos disponibles para que el cliente elija en el sitio web.',
    )
    website_m2_factor = fields.Float(
        string='Equivalencia m² (unidades por m²)',
        default=1.0,
        help='Cantidad de unidades del producto por cada 1 m² en el cálculo web.',
    )
    website_m3_factor = fields.Float(
        string='Equivalencia m³ (unidades por m³)',
        default=1.0,
        help='Cantidad de unidades del producto por cada 1 m³ en el cálculo web.',
    )
    website_featured_qty_type = fields.Selection([
        ('integer', 'Entero'),
        ('fractional', 'Fracción'),
    ], string='Tipo cantidad producto destacado', default='fractional')
    website_packaging_equivalent = fields.Float(
        string='Equivalente a embalaje',
        default=0.0,
        help='Para producto destacado web: si Tipo cantidad = Entero y este valor > 0, redondea al múltiplo superior de este embalaje.',
    )

    @api.depends('website_selected_packaging_id', 'website_selected_packaging_id.name')
    def _compute_website_packaging_qty(self):
        for rec in self:
            qty = 0.0
            if rec.website_selected_packaging_id and rec.website_selected_packaging_id.name:
                token = ''.join(ch if (ch.isdigit() or ch in ',.') else ' ' for ch in rec.website_selected_packaging_id.name).strip().split()
                if token:
                    try:
                        qty = float(token[0].replace(',', '.'))
                    except Exception:
                        qty = 0.0
            rec.website_packaging_qty = qty

    @api.onchange('website_selected_packaging_id')
    def _onchange_website_selected_packaging_id(self):
        for rec in self:
            if rec.website_packaging_qty > 0:
                rec.website_packaging_equivalent = rec.website_packaging_qty

    @api.onchange('website_enable_calculator')
    def _onchange_website_enable_calculator_packaging_default(self):
        for rec in self:
            if rec.website_enable_calculator and not rec.website_selected_packaging_id:
                candidates = rec.attribute_line_ids.mapped('value_ids').filtered(
                    lambda v: v.attribute_id and v.attribute_id.name and 'embalaje' in v.attribute_id.name.lower()
                )
                first_packaging = candidates[:1]
                if first_packaging:
                    rec.website_selected_packaging_id = first_packaging.id
                    if rec.website_packaging_qty > 0:
                        rec.website_packaging_equivalent = rec.website_packaging_qty

    def _apply_featured_rounding(self, qty):
        self.ensure_one()
        qty = float(qty or 0.0)
        if self.website_featured_qty_type != 'integer':
            return qty
        packaging = float(self.website_packaging_equivalent or 0.0)
        if packaging > 0:
            return float(math.ceil(qty / packaging) * packaging)
        return float(math.ceil(qty))


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
            self.length = 0.0
            self.width = 0.0
            self.height = 0.0

    def action_calculate_and_add(self):
        """Calcula y agrega los productos"""
        self.ensure_one()
        
        if not self.order_id:
            return {'type': 'ir.actions.act_window_close'}
        
        if self.total_surface <= 0:
            return {'type': 'ir.actions.act_window_close'}
        
        # Agregar productos del método
        for line in self.method_id.line_ids:
            qty = line.quantity_per_unit * self.total_surface
            qty = line._apply_rounding_by_type(qty)
            
            self.env['sale.order.line'].create({
                'order_id': self.order_id.id,
                'product_id': line.product_id.id,
                'product_uom_qty': qty,
                'price_unit': line.product_id.list_price or 0,
            })
        
        # Agregar producto destacado
        if self.featured_product_id and self.featured_quantity > 0:
            self.env['sale.order.line'].create({
                'order_id': self.order_id.id,
                'product_id': self.featured_product_id.id,
                'product_uom_qty': self.featured_quantity,
                'price_unit': self.featured_product_id.list_price or 0,
            })
        
        return {'type': 'ir.actions.act_window_close'}