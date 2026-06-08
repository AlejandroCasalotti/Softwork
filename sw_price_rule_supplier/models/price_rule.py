# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class PriceRuleSupplier(models.Model):
    _name = 'price.rule.supplier'
    _description = 'Regla de Costo Proveedor'
    _order = 'name'

    name = fields.Char(string='Nombre de Regla', required=True)
    active = fields.Boolean(string='Activa', default=True)
    company_id = fields.Many2one(
        'res.company', 
        string='Compañía',
        default=lambda self: self.env.company
    )
    line_ids = fields.One2many(
        'price.rule.supplier.line', 'rule_id',
        string='Líneas', copy=True
    )

    total_discount = fields.Float(
        string='Total Descuento (%)',
        compute='_compute_total',
        store=True
    )
    total_tariff = fields.Float(
        string='Total Tarifa Extra',
        compute='_compute_total',
        store=True
    )

    @api.depends('line_ids.discount', 'line_ids.tariff_extra')
    def _compute_total(self):
        for rule in self:
            total_disc = total_tariff = 0.0
            for line in rule.line_ids:
                total_disc += line.discount or 0.0
                total_tariff += line.tariff_extra or 0.0
            rule.total_discount = total_disc
            rule.total_tariff = total_tariff


class PriceRuleSupplierLine(models.Model):
    _name = 'price.rule.supplier.line'
    _description = 'Línea de Regla de Costo'
    _order = 'sequence'

    rule_id = fields.Many2one(
        'price.rule.supplier',
        string='Regla',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(string='#', default=10)
    description = fields.Char(string='Descripción', required=True)
    discount = fields.Float(string='Descuento %', default=0.0)
    tariff_extra = fields.Float(string='Tarifa Extra', default=0.0)


class ProductSupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    price_rule_id = fields.Many2one(
        'price.rule.supplier',
        string='Regla de Costo'
    )

    auto_update_standard = fields.Boolean(
        string='Actualizar Costo Estándar',
        default=False,
        help='Actualiza automáticamente el costo estándar del producto'
    )

    net_price = fields.Float(
        string='Precio Neto',
        compute='_compute_net_price',
        digits='Product Price'
    )

    @api.depends('price', 'price_rule_id', 'price_rule_id.line_ids')
    def _compute_net_price(self):
        for record in self:
            if not record.price_rule_id or not record.price_rule_id.line_ids:
                record.net_price = record.price
                continue

            current_price = record.price
            lines = record.price_rule_id.line_ids.sorted(key='sequence')

            for line in lines:
                if line.discount:
                    current_price = current_price - (current_price * line.discount / 100)
                if line.tariff_extra:
                    current_price = current_price + line.tariff_extra

            record.net_price = round(current_price, 2)

    def write(self, vals):
        """Override write para actualizar standard_price"""
        result = super(ProductSupplierInfo, self).write(vals)
        
        # Actualizar standard_price si está habilitado
        if 'price_rule_id' in vals or 'price' in vals or 'auto_update_standard' in vals:
            self._update_standard_price()
        
        return result

    def _update_standard_price(self):
        """
        Actualiza el costo estándar del producto
        
        Lógica:
        - Si net_price > 0: usa net_price
        - Si net_price = 0: usa price (precio manual)
        """
        for record in self:
            # Verificar si está habilitado
            if not record.auto_update_standard:
                continue
            
            # Obtener el precio para standard_price
            standard_price = 0.0
            
            if record.net_price and record.net_price > 0:
                # Usar net_price calculado
                standard_price = record.net_price
            elif record.price and record.price > 0:
                # Usar price manual si net_price es 0
                standard_price = record.price
            
            if not standard_price:
                continue
            
            # Convertir moneda si es diferente
            currency_supplier = record.currency_id
            currency_company = record.company_id.currency_id if record.company_id else self.env.company.currency_id
            
            if currency_supplier and currency_company and currency_supplier != currency_company:
                try:
                    standard_price = currency_supplier._convert(
                        standard_price,
                        currency_company,
                        record.company_id or self.env.company,
                        fields.Date.today()
                    )
                except Exception as e:
                    _logger.warning(f'Error convirtiendo moneda: {e}')
            
            # Actualizar standard_price en el producto
            if record.product_tmpl_id:
                try:
                    record.product_tmpl_id.sudo().write({
                        'standard_price': standard_price
                    })
                    
                    # Actualizar cada variante
                    for variant in record.product_tmpl_id.product_variant_ids:
                        variant.sudo().write({
                            'standard_price': standard_price
                        })
                    
                    _logger.info(f'Standard price actualizado: {standard_price}')
                except Exception as e:
                    _logger.warning(f'Error actualizando standard_price: {e}')