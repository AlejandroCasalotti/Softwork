# -*- coding: utf-8 -*-
from odoo import fields, models


class MlPublishAssistantPictureLine(models.TransientModel):
    _name = "ml.publish.assistant.picture.line"
    _description = "Línea de imagen en asistente ML"

    wizard_id = fields.Many2one("ml.publish.assistant.wizard", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    source = fields.Char(string="URL imagen", required=True)