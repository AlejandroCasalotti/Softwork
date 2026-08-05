# -*- coding: utf-8 -*-
from odoo import fields, models


class MlPublishAssistantAttributeLine(models.TransientModel):
    _name = "ml.publish.assistant.attribute.line"
    _description = "Línea de atributo en asistente ML"

    wizard_id = fields.Many2one("ml.publish.assistant.wizard", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    attribute_id = fields.Char(string="ID atributo", required=True)
    attribute_name = fields.Char(string="Atributo")
    required = fields.Boolean(string="Requerido", default=False)

    value_id = fields.Char(string="ID valor")
    value_name = fields.Char(string="Valor")