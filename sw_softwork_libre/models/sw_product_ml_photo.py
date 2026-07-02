# -*- coding: utf-8 -*-
from odoo import fields, models


class SwProductMlPhoto(models.Model):
    _name = "sw.product.ml.photo"
    _description = "Fotos Publicación MercadoLibre"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    product_tmpl_id = fields.Many2one("product.template", required=True, ondelete="cascade")
    name = fields.Char(string="Nombre")
    image_1920 = fields.Image(string="Foto", required=True)
    is_main = fields.Boolean(string="Principal")