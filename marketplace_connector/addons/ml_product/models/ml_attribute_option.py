# -*- coding: utf-8 -*-
from odoo import fields, models


class MlAttributeOption(models.Model):
    _name = "ml.attribute.option"
    _description = "Cache de opciones de atributos ML"
    _order = "attribute_name, value_name"

    category_id = fields.Char(required=True, index=True)
    attribute_id = fields.Char(required=True, index=True)
    attribute_name = fields.Char(required=True)
    value_id = fields.Char(index=True)
    value_name = fields.Char(required=True)

    _sql_constraints = [
        (
            "ml_attr_option_unique",
            "unique(category_id, attribute_id, value_id, value_name)",
            "La opción de atributo ya existe para esta categoría.",
        )
    ]