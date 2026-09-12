from odoo import fields, models
from odoo.exceptions import UserError


class SceConnectStockJob(models.Model):
    _inherit = "sce.job"

    job_type = fields.Selection(
        selection_add=[("sync_connect_stock", "Sync Connect Stock")],
        ondelete={"sync_connect_stock": "set default"},
    )
    connect_marketplace_mapping_id = fields.Many2one(
        "sce.connect.marketplace.mapping", string="Connect Marketplace Mapping", ondelete="cascade", index=True
    )

    def _execute_provider_operation(self, provider, payload):
        if self.job_type != "sync_connect_stock":
            return super()._execute_provider_operation(provider, payload)
        if not self.connect_marketplace_mapping_id:
            raise UserError("El job Connect de stock necesita un mapping marketplace.")
        return self.env["sce.connect.stock.service"].sync_mapping(self.connect_marketplace_mapping_id)