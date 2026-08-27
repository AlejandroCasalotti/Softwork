from odoo import fields, models


class SceSecretSetWizard(models.TransientModel):
    _name = "sce.secret.set.wizard"
    _description = "Set SCE Connect Secret"

    secret_id = fields.Many2one("sce.secret", required=True, readonly=True)
    value = fields.Char(required=True)

    def action_set_secret(self):
        self.ensure_one()
        self.secret_id.with_context(sce_backend_secret_access=True).set_value(self.value)
        self.value = False
        return {"type": "ir.actions.act_window_close"}
