# -*- coding: utf-8 -*-

from odoo import models, fields

class MassPricePreview(models.TransientModel):
    _name = 'mass.price.preview'
    _description = 'Preview Actualización Precios'

    name = fields.Char('Producto')
    old_price = fields.Monetary('Precio Anterior')
    new_price = fields.Monetary('Nuevo Precio')
    difference = fields.Monetary('Diferencia')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)