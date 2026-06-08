# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Campo margen
    sale_margin = fields.Float(
        string='Margen (%)',
        default=0.0,
        help='Ejemplo: 50 = 50% de margen'
    )
    
    # Campo calculado
    sale_price = fields.Float(
        string='Precio Venta',
        compute='_compute_sale_price',
        store=True,
        help='standard_price + margen'
    )

    @api.depends('standard_price', 'sale_margin')
    def _compute_sale_price(self):
        for rec in self:
            if rec.standard_price and rec.sale_margin:
                rec.sale_price = rec.standard_price + (rec.standard_price * rec.sale_margin / 100)
            elif rec.standard_price:
                rec.sale_price = rec.standard_price
            else:
                rec.sale_price = 0.0

    def update_price(self):
        """Botón para actualizar list_price"""
        for rec in self:
            if rec.sale_price > 0:
                rec.list_price = rec.sale_price
        return True