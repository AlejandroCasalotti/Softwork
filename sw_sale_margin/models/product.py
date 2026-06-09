# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    sale_margin = fields.Float(
        string='Margen de venta %',
        default=0.0,
        help='0 = usar precio manual, >0 = calcular automáticamente'
    )

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
        result = super(ProductTemplate, self).write(vals)
        
        if 'standard_price' in vals or 'sale_margin' in vals:
            self._update_list_price()
        
        return result

    def _update_list_price(self):
        for rec in self:
            if rec.sale_price > 0:
                rec.list_price = rec.sale_price


class ProductProduct(models.Model):
    _inherit = 'product.product'

    sale_margin = fields.Float(
        string='Margen de venta %',
        default=0.0,
        help='0 = usar precio manual, >0 = calcular automáticamente'
    )

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