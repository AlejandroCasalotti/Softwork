# -*- coding: utf-8 -*-
from odoo import api, fields, models


class MlCategorySearchResult(models.TransientModel):
    _name = "ml.category.search.result"
    _description = "Resultados temporales búsqueda de categorías MercadoLibre"

    wizard_id = fields.Many2one(
        "ml.category.search.wizard", required=True, ondelete="cascade"
    )
    category_id = fields.Char(string="ID categoría", required=True)
    category_name = fields.Char(string="Categoría", required=True)
    selected = fields.Boolean(string="Seleccionar", default=False)

    @api.onchange("selected")
    def _onchange_selected(self):
        """Garantizar selección única por wizard sin JavaScript: si se marca
        esta línea, desmarcar las demás líneas seleccionadas del mismo wizard.
        """
        if not self.wizard_id:
            return
        if self.selected:
            other = (
                self.search(
                    [
                        ("wizard_id", "=", self.wizard_id.id),
                        ("id", "!=", self.id),
                        ("selected", "=", True),
                    ]
                )
                or None
            )
            if other:
                other.write({"selected": False})