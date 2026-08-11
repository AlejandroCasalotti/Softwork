# -*- coding: utf-8 -*-
from odoo import fields, models


class MlCategorySearchResult(models.TransientModel):
    _name = "ml.category.search.result"
    _description = "Resultados temporales búsqueda de categorías MercadoLibre"

    wizard_id = fields.Many2one(
        "ml.category.search.wizard", required=True, ondelete="cascade"
    )
    category_id = fields.Char(string="ID categoría", required=True)
    category_name = fields.Char(string="Categoría", required=True)
    selected_category_id = fields.Boolean(string="Seleccionar", default=False)