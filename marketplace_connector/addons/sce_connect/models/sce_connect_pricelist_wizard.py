from odoo import api, fields, models
from odoo.exceptions import UserError

from ..services.connection_service import ConnectionService


class SceConnectPricelistWizard(models.TransientModel):
    _name = "sce.connect.pricelist.wizard"
    _description = "Select Remote Odoo Pricelist"

    account_id = fields.Many2one("sce.account", required=True, readonly=True)
    policy_id = fields.Many2one("sce.connect.price.policy", required=True, readonly=True)
    line_ids = fields.One2many("sce.connect.pricelist.line", "wizard_id", string="Listas")

    def action_load(self):
        self.ensure_one()
        if self.account_id.connect_ownership_state != "ready":
            raise UserError("Complete el ownership de la cuenta antes de consultar listas de precios.")
        context = ConnectionService(
            self.account_id.external_connection_id, env=self.env
        ).remote_product_context()
        rows = ConnectionService(
            self.account_id.external_connection_id, env=self.env
        ).remote_pricelists(context=context)
        self.line_ids.unlink()
        values = []
        for row in rows or []:
            if not isinstance(row, dict) or not row.get("id"):
                continue
            currency = row.get("currency_id")
            values.append({
                "wizard_id": self.id,
                "remote_pricelist_id": row["id"],
                "name": row.get("name") or str(row["id"]),
                "currency_name": currency[1] if isinstance(currency, (list, tuple)) else "",
            })
        if values:
            self.env["sce.connect.pricelist.line"].create(values)
        return {"type": "ir.actions.act_window", "res_model": self._name, "view_mode": "form", "res_id": self.id, "target": "new"}

    def action_apply(self):
        self.ensure_one()
        selected = self.line_ids.filtered("selected")
        if len(selected) != 1:
            raise UserError("Seleccione exactamente una lista de precios Odoo.")
        self.policy_id.write({
            "remote_pricelist_id": selected.remote_pricelist_id,
            "remote_pricelist_name": selected.name,
        })
        return {"type": "ir.actions.act_window_close"}


class SceConnectPricelistLine(models.TransientModel):
    _name = "sce.connect.pricelist.line"
    _description = "Remote Odoo Pricelist Option"
    _order = "name"

    wizard_id = fields.Many2one("sce.connect.pricelist.wizard", required=True, ondelete="cascade")
    selected = fields.Boolean(string="Seleccionar")
    remote_pricelist_id = fields.Integer(readonly=True)
    name = fields.Char(readonly=True)
    currency_name = fields.Char(readonly=True)