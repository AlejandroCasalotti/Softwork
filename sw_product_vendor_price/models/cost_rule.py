# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools import _


class CostRule(models.Model):
    _name = 'cost.rule'
    _description = 'Regla de Costo'
    _order = 'sequence, id'
    _sql_constraints = [
        ('unique_name', 'unique(name)', 'El nombre de la regla debe ser único'),
    ]

    name = fields.Char(
        string='Nombre de la Regla',
        required=True,
        help='Nombre identificador de la regla'
    )
    
    sequence = fields.Integer(
        string='Secuencia',
        default=10,
        help='Orden de aplicación de las reglas'
    )
    
    active = fields.Boolean(
        string='Activa',
        default=True,
        help='Si está desactivada, no se aplicará a los precios'
    )
    
    rule_type = fields.Selection([
        ('discount', 'Descuento'),
        ('extra', 'Tarifa Extra'),
    ], string='Tipo de Regla', required=True, default='extra')
    
    rule_mode = fields.Selection([
        ('percentage', 'Porcentaje'),
        ('fixed', 'Monto Fijo'),
    ], string='Modo', required=True, default='percentage')
    
    rule_value = fields.Float(
        string='Valor',
        required=True,
        default=0.0,
        digits='Product Price',
        help='Porcentaje o monto fijo según el modo seleccionado'
    )
    
    description = fields.Text(
        string='Descripción',
        help='Descripción adicional de la regla'
    )
    
    supplier_id = fields.Many2one(
        'res.partner',
        string='Proveedor Específico',
        domain=[('supplier_rank', '>', 0)],
        help='Si se deja vacío, la regla aplica a todos los proveedores'
    )
    
    # Vista tree de reglas aplicadas
    applied_line_ids = fields.One2many(
        'cost.rule.applied',
        'rule_id',
        string='Aplicaciones',
        readonly=True
    )

    def calculate_value(self, base_price):
        """
        Calcula el valor a aplicar según la regla
        Returns: float - Valor a restar (descuento) o sumar (tarifa extra)
        """
        self.ensure_one()
        
        if self.rule_mode == 'percentage':
            # Porcentaje del precio base
            calculated = base_price * (self.rule_value / 100.0)
        else:
            # Monto fijo
            calculated = self.rule_value
        
        if self.rule_type == 'discount':
            return -calculated  # Resta el descuento
        else:
            return calculated   # Suma la tarifa extra

    @api.constrains('rule_value')
    def _check_rule_value(self):
        for rule in self:
            if rule.rule_value < 0:
                raise UserError('El valor de la regla no puede ser negativo')


class CostRuleApplied(models.Model):
    """
    Registros de aplicación de reglas a proveedores específicos
    """
    _name = 'cost.rule.applied'
    _description = 'Regla de Costo Aplicada'
    _order = 'sequence, id'

    rule_id = fields.Many2one(
        'cost.rule',
        string='Regla de Costo',
        required=True,
        ondelete='cascade'
    )
    
    supplierinfo_id = fields.Many2one(
        'product.supplierinfo',
        string='Lista de Precio Proveedor',
        required=True,
        ondelete='cascade'
    )
    
    sequence = fields.Integer(
        string='Secuencia',
        related='rule_id.sequence',
        store=True
    )
    
    rule_type = fields.Selection(
        string='Tipo',
        related='rule_id.rule_type',
        store=True
    )
    
    rule_mode = fields.Selection(
        string='Modo',
        related='rule_id.rule_mode',
        store=True
    )
    
    rule_value = fields.Float(
        string='Valor',
        related='rule_id.rule_value',
        store=True
    )
    
    calculated_value = fields.Float(
        string='Valor Calculado',
        help='Valor monetario resultante de aplicar la regla al precio base'
    )
    
    @api.model
    def create_or_update(self, supplierinfo, rule):
        """
        Crea o actualiza el registro de aplicación de una regla
        """
        applied = self.search([
            ('rule_id', '=', rule.id),
            ('supplierinfo_id', '=', supplierinfo.id)
        ])
        
        base_price = supplierinfo.price
        calc_value = rule.calculate_value(base_price)
        
        if applied:
            applied.calculated_value = calc_value
        else:
            applied = self.create({
                'rule_id': rule.id,
                'supplierinfo_id': supplierinfo.id,
                'calculated_value': calc_value,
            })
        
        return applied