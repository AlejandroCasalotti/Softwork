# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError


class MlPublishAssistantAttributeLine(models.TransientModel):
    _name = "ml.publish.assistant.attribute.line"
    _description = "Línea de atributo en asistente ML"

    wizard_id = fields.Many2one("ml.publish.assistant.wizard", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    attribute_id = fields.Char(string="ID atributo", required=True)
    attribute_name = fields.Char(string="Atributo")
    required = fields.Boolean(string="Requerido", default=False)
    attribute_option_id = fields.Many2one(
        "ml.attribute.option",
        string="Opción sugerida",
        domain="[('account_id','=', parent.account_id), ('category_id','=', parent.ml_category_ref_id.category_id), ('attribute_id','=', attribute_id)]",
    )
    value_id = fields.Char(string="ID valor")
    value_name = fields.Char(string="Valor")
    has_options = fields.Boolean(string="Tiene opciones", default=False, readonly=True)

    def action_open_attribute_option_picker(self):
        self.ensure_one()
        wizard = self.wizard_id
        if not wizard:
            raise UserError("La línea no tiene wizard asociado.")
        if not wizard.ml_category_ref_id:
            raise UserError("Primero define categoría ML en el Paso 1.")
        picker = self.env["ml.attribute.option.picker.wizard"].create(
            {
                "wizard_id": wizard.id,
                "line_id": self.id,
                "category_id": wizard.ml_category_ref_id.category_id or "",
                "attribute_id": self.attribute_id or "",
                "attribute_name": self.attribute_name or "",
            }
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "ml.attribute.option.picker.wizard",
            "view_mode": "form",
            "res_id": picker.id,
            "target": "new",
        }

    @api.onchange("attribute_option_id")
    def _onchange_attribute_option_id(self):
        for line in self:
            if line.attribute_option_id:
                line.value_id = line.attribute_option_id.value_id or ""
                line.value_name = line.attribute_option_id.value_name or ""