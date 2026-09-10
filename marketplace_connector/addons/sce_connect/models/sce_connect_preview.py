from odoo import api, fields, models
from odoo.exceptions import UserError


class SceConnectPreviewWizard(models.TransientModel):
    _name = "sce.connect.preview.wizard"
    _description = "SCE Connect Commercial Preview"

    account_id = fields.Many2one("sce.account", required=True, readonly=True)
    mapping_id = fields.Many2one(
        "sce.connect.marketplace.mapping",
        required=True,
        domain="[('marketplace_account_id', '=', account_id), ('active', '=', True)]",
    )
    preview_type = fields.Selection(
        [("stock", "Stock"), ("price", "Precio")], required=True, default="stock"
    )
    source_value = fields.Char(string="Valor Odoo", readonly=True)
    reserve_value = fields.Char(string="Reserva", readonly=True)
    calculated_value = fields.Char(string="Resultado", readonly=True)
    base_price = fields.Char(string="Precio base", readonly=True)
    adjustment_value = fields.Char(string="Ajustes", readonly=True)
    final_price = fields.Char(string="Precio final", readonly=True)
    status = fields.Selection(
        [("ready", "Listo"), ("blocked", "Bloqueado"), ("error", "Error")], readonly=True
    )
    message = fields.Text(readonly=True)

    @api.onchange("mapping_id")
    def _onchange_mapping_id(self):
        if self.mapping_id:
            self.account_id = self.mapping_id.marketplace_account_id

    def action_preview(self):
        self.ensure_one()
        if self.account_id.connect_ownership_state != "ready":
            raise UserError("Complete la configuración de ownership de la cuenta antes de previsualizar.")
        if self.preview_type == "stock":
            result = self.env["sce.connect.stock.service"].preview_mapping(self.mapping_id)
            self.write({
                "source_value": str(result["source_stock"]),
                "reserve_value": result["reserve"],
                "calculated_value": str(result["available_quantity"]),
                "status": "ready",
                "message": False,
            })
        else:
            result = self.env["sce.connect.price.service"].preview_mapping(self.mapping_id)
            self.write({
                "base_price": result["base_price"],
                "adjustment_value": result["adjustments"],
                "final_price": result.get("price") or False,
                "status": "blocked" if result.get("blocked") else "ready",
                "message": result.get("message") or False,
            })
        return {"type": "ir.actions.act_window", "res_model": self._name, "view_mode": "form", "res_id": self.id, "target": "new"}