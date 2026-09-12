# -*- coding: utf-8 -*-
from odoo import api, fields, models


class MlCategorySearchResult(models.TransientModel):
    _name = "ml.category.search.result"
    _description = "Resultados temporales búsqueda de categorías MercadoLibre"

    wizard_id = fields.Many2one("ml.category.search.wizard", required=True, ondelete="cascade")
    category_id = fields.Char(string="ID categoría", required=True)
    category_name = fields.Char(string="Categoría", required=True)
    selected = fields.Boolean(string="Seleccionar", default=False)

    @api.onchange("selected")
    def _onchange_selected(self):
        for result in self:
            if result.selected and result.wizard_id:
                self.search(
                    [
                        ("wizard_id", "=", result.wizard_id.id),
                        ("id", "!=", result.id),
                        ("selected", "=", True),
                    ]
                ).write({"selected": False})