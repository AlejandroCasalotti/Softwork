# -*- coding: utf-8 -*-
from odoo import fields, models


class MlFamily(models.Model):
    _name = "ml.family"
    _description = "Familia/Línea de producto MercadoLibre"
    _order = "name"

    name = fields.Char(required=True, index=True)

    _sql_constraints = [
        ("name_uniq", "unique(name)", "Ya existe una familia/línea de producto con ese nombre."),
    ]
