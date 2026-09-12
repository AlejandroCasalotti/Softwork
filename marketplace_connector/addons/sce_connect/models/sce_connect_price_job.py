from odoo import fields, models
from odoo.exceptions import UserError


class SceConnectPriceJob(models.Model):
    _inherit = "sce.job"

    job_type = fields.Selection(
        selection_add=[("sync_connect_price", "Sync Connect Price")],
        ondelete={"sync_connect_price": "set default"},
    )

    def _execute_provider_operation(self, provider, payload):
        if self.job_type != "sync_connect_price":
            return super()._execute_provider_operation(provider, payload)
        if not self.connect_marketplace_mapping_id:
            raise UserError("El job Connect de precio necesita un mapping marketplace.")
        return self.env["sce.connect.price.service"].sync_mapping(self.connect_marketplace_mapping_id)