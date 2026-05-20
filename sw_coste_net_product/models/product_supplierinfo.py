# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ProductSupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'
    
    rule_id = fields.Many2one(
        'coste_net_rule',
        string='Regla de Costo'
    )
    
    price_net = fields.Float(
        string='Costo Neto',
        compute='_compute_price_net',
        digits='Product Price'
    )

    @api.depends('price', 'rule_id')
    def _compute_price_net(self):
        for record in self:
            if not record.rule_id or not record.rule_id.line_ids:
                record.price_net = record.price
                continue
            
            current_price = record.price
            lines = record.rule_id.line_ids.sorted(key=lambda x: x.sequence)
            
            for line in lines:
                if line.line_type == 'discount':
                    current_price -= current_price * (line.value / 100)
                elif line.line_type == 'surcharge':
                    current_price += current_price * (line.value / 100)
                elif line.line_type == 'fixed':
                    current_price += line.value
            
            record.price_net = max(round(current_price, 2), 0.0)


class CosteNetRule(models.Model):
    _name = 'coste_net_rule'
    _description = 'Regla de Costo Neto'
    _order = 'sequence'

    name = fields.Char(string='Nombre', required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True, string='Activa')
    
    line_ids = fields.One2many(
        'coste_net_rule_line', 'rule_id',
        string='Lineas', copy=True
    )
    
    total_discount = fields.Float(
        string='Total Descuento (%)',
        compute='_compute_totals',
        store=True
    )
    total_surcharge = fields.Float(
        string='Total Recargo (%)',
        compute='_compute_totals',
        store=True
    )
    total_fixed = fields.Float(
        string='Total Fijo',
        compute='_compute_totals',
        store=True
    )

    @api.depends('line_ids.value', 'line_ids.line_type')
    def _compute_totals(self):
        for rule in self:
            discount = surcharge = fixed = 0.0
            for line in rule.line_ids:
                if line.line_type == 'discount':
                    discount += line.value
                elif line.line_type == 'surcharge':
                    surcharge += line.value
                elif line.line_type == 'fixed':
                    fixed += line.value
            rule.total_discount = discount
            rule.total_surcharge = surcharge
            rule.total_fixed = fixed

    def _register_hook(self):
        """Crea la vista heredada automáticamente al instalar"""
        super()._register_hook()
        self._create_inherited_view()

    def _create_inherited_view(self):
        """Crea la vista heredada para product.supplierinfo"""
        # Verificar si ya existe
        existing = self.env['ir.ui.view'].search([
            ('name', '=', 'product.supplierinfo.form.costenet'),
            ('model', '=', 'product.supplierinfo'),
        ])
        if existing:
            return True
        
        # Buscar la vista original
        original_view = self.env['ir.ui.view'].search([
            ('model', '=', 'product.supplierinfo'),
            ('type', '=', 'form'),
            ('inherit_id', '=', False),
        ], limit=1)
        
        if not original_view:
            _logger.warning('Vista original no encontrada')
            return False
        
        # Crear vista heredada
        view_data = {
            'name': 'product.supplierinfo.form.costenet',
            'model': 'product.supplierinfo',
            'inherit_id': original_view.id,
            'arch': '''
                <xpath expr="//field[@name='price']" position="after">
                    <field name="rule_id"/>
                    <field name="price_net" readonly="1" 
                           attrs="{'invisible': [('rule_id', '=', False)]}"/>
                </xpath>
            ''',
            'active': True,
        }
        
        self.env['ir.ui.view'].create(view_data)
        _logger.info('Vista heredada creada correctamente')
        return True


class CosteNetRuleLine(models.Model):
    _name = 'coste_net_rule_line'
    _description = 'Linea de Regla de Costo'
    _order = 'sequence'

    rule_id = fields.Many2one(
        'coste_net_rule',
        string='Regla',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Descripcion', required=True)
    
    line_type = fields.Selection([
        ('discount', 'Descuento (%)'),
        ('surcharge', 'Recargo (%)'),
        ('fixed', 'Tarifa Fija'),
    ], string='Tipo', required=True, default='discount')
    
    value = fields.Float(string='Valor', required=True)

    @api.constrains('value')
    def _check_value(self):
        for line in self:
            if line.value < 0:
                raise UserError(f'El valor no puede ser negativo: {line.name}')