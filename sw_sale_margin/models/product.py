# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Campo margen en template
    sale_margin = fields.Float(
        string='Margen de venta',
        default=0.0,
        help='0 = usar precio manual, >0 = calcular automáticamente'
    )

    # Precio calculado (solo lectura)
    sale_price = fields.Float(
        string='Precio calculado',
        compute='_compute_sale_price',
        store=True,
        help='Precio de venta calculado'
    )

    @api.depends('standard_price', 'sale_margin')
    def _compute_sale_price(self):
        for rec in self:
            if rec.standard_price and rec.sale_margin > 0:
                rec.sale_price = rec.standard_price + (rec.standard_price * rec.sale_margin / 100)
            elif rec.standard_price:
                rec.sale_price = rec.standard_price
            else:
                rec.sale_price = 0.0

    def write(self, vals):
        result = super(ProductTemplate, self).write(vals)
        
        # Actualizar list_price si cambia standard_price o sale_margin
        if 'standard_price' in vals or 'sale_margin' in vals:
            self._update_list_price()
        
        return result

    def _update_list_price(self):
        for rec in self:
            if rec.sale_price > 0:
                rec.list_price = rec.sale_price
                _logger.info(f'list_price actualizado a: {rec.sale_price}')


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # Campo margen en variante
    sale_margin = fields.Float(
        string='Margen de venta',
        default=0.0,
        help='0 = usar precio manual, >0 = calcular automáticamente'
    )

    # Precio calculado
    sale_price = fields.Float(
        string='Precio calculado',
        compute='_compute_sale_price',
        store=True
    )

    @api.depends('standard_price', 'sale_margin')
    def _compute_sale_price(self):
        for rec in self:
            if rec.standard_price and rec.sale_margin > 0:
                rec.sale_price = rec.standard_price + (rec.standard_price * rec.sale_margin / 100)
            elif rec.standard_price:
                rec.sale_price = rec.standard_price
            else:
                rec.sale_price = 0.0

    def write(self, vals):
        result = super(ProductProduct, self).write(vals)
        
        if 'standard_price' in vals or 'sale_margin' in vals:
            self._update_list_price()
        
        return result

    def _update_list_price(self):
        for rec in self:
            if rec.sale_price > 0:
                rec.list_price = rec.sale_price