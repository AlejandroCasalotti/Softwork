# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.exceptions import UserError


class MlAttributeOptionPickerWizard(models.TransientModel):
    _name = "ml.attribute.option.picker.wizard"
    _description = "Selector rápido de opción ML para atributo del asistente"

    wizard_id = fields.Many2one("ml.publish.assistant.wizard", required=True, readonly=True)
    line_id = fields.Many2one("ml.publish.assistant.attribute.line", required=True, readonly=True)
    account_id = fields.Many2one("sce.account", related="wizard_id.account_id", readonly=True)
    category_id = fields.Char(string="Categoría ML", readonly=True)
    attribute_id = fields.Char(string="Atributo", readonly=True)
    attribute_name = fields.Char(string="Nombre", readonly=True)

    option_id = fields.Many2one(
        "ml.attribute.option",
        string="Opción ML",
        domain="[('account_id', '=', account_id), ('category_id', '=', category_id), ('attribute_id', '=', attribute_id)]",
    )

    def action_apply(self):
        self.ensure_one()
        if not self.option_id:
            raise UserError("Selecciona una opción antes de aplicar.")
        if not self.line_id.exists():
            raise UserError("La línea de atributo ya no existe.")

        self.line_id.write(
            {
                "value_id": self.option_id.value_id or "",
                "value_name": self.option_id.value_name or "",
            }
        )

        return {
            "type": "ir.actions.act_window",
            "res_model": "ml.publish.assistant.wizard",
            "view_mode": "form",
            "res_id": self.wizard_id.id,
            "target": "new",
        }