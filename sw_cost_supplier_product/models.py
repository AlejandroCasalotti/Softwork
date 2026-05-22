# -*- coding: utf-8 -*-
from odoo import models, fields

class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    # Solo agregar campos, nada de lógica
    use_supplier_cost = fields.Boolean(string='Costo proveedor', default=False)
    sale_margin = fields.Float(string='Margen de venta (%)', default=0.0)