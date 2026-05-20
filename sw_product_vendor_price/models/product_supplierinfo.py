# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ProductSupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    # === CAMPOS NUEVOS ===
    
    # Margen de venta
    sale_margin = fields.Float(
        string='Margen de Venta (%)',
        digits='Product Price',
        default=0.0,
        help='Porcentaje de margen sobre el costo para calcular el precio de venta'
    )
    
    # Reglas de costo aplicadas
    rule_ids = fields.Many2many(
        'cost.rule',
        'cost_rule_supplierinfo_rel',
        'supplierinfo_id',
        'rule_id',
        string='Reglas de Costo',
        help='Reglas que se aplicarán al precio del proveedor'
    )
    
    # Campos calculados
    calculated_discount = fields.Float(
        string='Descuentos Aplicados',
        digits='Product Price',
        compute='_compute_calculated_prices',
        store=True,
        help='Total de descuentos aplicados'
    )
    
    calculated_extra = fields.Float(
        string='Tarifas Aplicadas',
        digits='Product Price',
        compute='_compute_calculated_prices',
        store=True,
        help='Total de tarifas extras aplicadas'
    )
    
    final_cost = fields.Float(
        string='Costo Final',
        digits='Product Price',
        compute='_compute_calculated_prices',
        store=True,
        help='Precio del proveedor menos descuentos más tarifas extras'
    )
    
    # Flag para evitar bucles infinitos
    _internal_update = False

    # === COMPUTED FIELDS ===

    @api.depends('price', 'rule_ids', 'rule_ids.rule_type', 
                 'rule_ids.rule_mode', 'rule_ids.rule_value', 'sale_margin')
    def _compute_calculated_prices(self):
        """
        Calcula los valores de descuento, tarifas extras y costo final
        """
        for record in self:
            discount_total = 0.0
            extra_total = 0.0
            base_price = record.price or 0.0
            
            # Aplicar cada regla activa
            for rule in record.rule_ids.filtered('active'):
                if rule.rule_type == 'discount':
                    if rule.rule_mode == 'percentage':
                        discount_total += base_price * (rule.rule_value / 100.0)
                    else:
                        discount_total += rule.rule_value
                else:  # extra
                    if rule.rule_mode == 'percentage':
                        extra_total += base_price * (rule.rule_value / 100.0)
                    else:
                        extra_total += rule.rule_value
            
            record.calculated_discount = discount_total
            record.calculated_extra = extra_total
            record.final_cost = base_price - discount_total + extra_total

    # === ONCHANGE METHODS ===

    @api.onchange('price')
    def _onchange_price(self):
        """Cuando cambia el precio base del proveedor"""
        self._apply_margin_to_product()

    @api.onchange('final_cost')
    def _onchange_final_cost(self):
        """Cuando cambia el costo final (por las reglas)"""
        self._update_product_standard_price()

    @api.onchange('sale_margin')
    def _onchange_sale_margin(self):
        """Cuando cambia el margen de venta"""
        self._apply_margin_to_product()

    @api.onchange('rule_ids')
    def _onchange_rule_ids(self):
        """Cuando cambian las reglas de costo"""
        self._update_product_standard_price()
        self._apply_margin_to_product()

    # === METODOS PRINCIPALES ===

    def _update_product_standard_price(self):
        """
        Actualiza el standard_price del producto con el costo final
        """
        if self._internal_update:
            return
            
        for record in self:
            if record.product_id and record.final_cost:
                try:
                    self._internal_update = True
                    record.product_id.standard_price = record.final_cost
                    _logger.info(f'Actualizado standard_price a {record.final_cost} para producto {record.product_id.name}')
                finally:
                    self._internal_update = False

    def _apply_margin_to_product(self):
        """
        Aplica el margen de venta al list_price del producto
        list_price = standard_price * (1 + margen/100)
        """
        if self._internal_update:
            return
            
        for record in self:
            if record.product_id and record.sale_margin > 0:
                # Usar el standard_price actual del producto
                cost = record.product_id.standard_price or record.final_cost or record.price or 0.0
                if cost > 0:
                    new_list_price = cost * (1 + record.sale_margin / 100.0)
                    try:
                        self._internal_update = True
                        record.product_id.list_price = new_list_price
                        _logger.info(f'Actualizado list_price a {new_list_price} con margen {record.sale_margin}%')
                    finally:
                        self._internal_update = False

    # === METODO WRITE ===
    
    def write(self, vals):
        """
        Override para manejar actualizaciones
        """
        result = super(ProductSupplierInfo, self).write(vals)
        
        # Si cambia el precio base, el margen o las reglas
        if any(field in vals for field in ['price', 'sale_margin', 'rule_ids']):
            for record in self:
                record._update_product_standard_price()
                record._apply_margin_to_product()
        
        return result

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override al crear nuevos registros
        """
        records = super(ProductSupplierInfo, self).create(vals_list)
        
        for record in records:
            record._update_product_standard_price()
            record._apply_margin_to_product()
        
        return records


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def write(self, vals):
        """
        Override para sincronizar hacia la lista de precios del proveedor
        """
        result = super(ProductProduct, self).write(vals)
        
        # Si cambia el standard_price, actualizar el precio del proveedor
        if 'standard_price' in vals:
            for record in self:
                # Buscar la lista de precio del proveedor principal
                supplierinfo = self.env['product.supplierinfo'].search([
                    ('product_id', '=', record.id),
                ], order='sequence, min_qty asc', limit=1)
                
                if supplierinfo:
                    # No actualizar si el precio ya es el mismo
                    if supplierinfo.price != record.standard_price:
                        supplierinfo.price = record.standard_price
        
        return result