# -*- coding: utf-8 -*-
from odoo import fields, models


class MlCategory(models.Model):
    _name = "ml.category"
    _description = "Categorías MercadoLibre"
    _order = "category_name"

    account_id = fields.Many2one("sce.account", required=True, ondelete="cascade", index=True)
    category_id = fields.Char(required=True, index=True)
    category_name = fields.Char(required=True, index=True)

    _ml_category_unique = models.Constraint(
        "unique(account_id, category_id)",
        "La categoría ML ya existe para esta cuenta.",
    )

    def name_get(self):
        result = []
        for rec in self:
            label = rec.category_name or rec.category_id
            result.append((rec.id, label))
        return result