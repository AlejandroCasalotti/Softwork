# -*- coding: utf-8 -*-
from odoo import api, fields, models


class MlPublishAssistantSaleTermLine(models.TransientModel):
    _name = "ml.publish.assistant.saleterm.line"
    _description = "Línea de condición de venta (sale_terms) en asistente ML"

    wizard_id = fields.Many2one("ml.publish.assistant.wizard", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    term_id = fields.Char(string="ID condición", required=True)
    term_name = fields.Char(string="Condición")
    required = fields.Boolean(string="Requerido", default=False)
    has_options = fields.Boolean(string="Tiene opciones", default=False, readonly=True)
    term_option_id = fields.Many2one(
        "ml.attribute.option",
        string="Opción sugerida",
        domain="[('account_id','=', parent.account_id), ('attribute_id','=', term_id)]",
    )
    value_id = fields.Char(string="ID valor")
    value_name = fields.Char(string="Valor")

    @api.onchange("term_option_id")
    def _onchange_term_option_id(self):
        for line in self:
            if line.term_option_id:
                line.value_id = line.term_option_id.value_id or ""
                line.value_name = line.term_option_id.value_name or ""
