# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.exceptions import UserError


class SceMarketplaceJob(models.Model):
    _inherit = "sce.job"

    job_type = fields.Selection(
        selection_add=[
            ("publish_product", "Publish Product"),
            ("update_product", "Update Product"),
            ("sync_publication_stock", "Sync Publication Stock"),
            ("sync_publication_price", "Sync Publication Price"),
            ("sync_publication", "Sync Publication From Marketplace"),
            ("import_order", "Import Order"),
            ("delete_product", "Remove Product"),
        ],
        ondelete={
            "publish_product": "set default",
            "update_product": "set default",
            "sync_publication_stock": "set default",
            "sync_publication_price": "set default",
            "sync_publication": "set default",
            "import_order": "set default",
            "delete_product": "set default",
        },
    )
    publication_id = fields.Many2one(
        "marketplace.publication", string="Publication", ondelete="cascade", index=True
    )
    external_id = fields.Char(string="External ID", index=True)

    def action_open_publication(self):
        self.ensure_one()
        if not self.publication_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": "marketplace.publication",
            "view_mode": "form",
            "res_id": self.publication_id.id,
            "target": "current",
        }

    def _execute_provider_operation(self, provider, payload):
        if self.job_type not in {
            "publish_product",
            "update_product",
            "sync_publication_stock",
            "sync_publication_price",
            "sync_publication",
            "import_order",
            "delete_product",
        }:
            return super()._execute_provider_operation(provider, payload)
        service = self.env["marketplace.publication.service"]
        if not self.publication_id:
            if self.job_type == "import_order":
                return service.import_order(self.account_id, self.external_id)
            raise UserError("El job de marketplace necesita una publicación asociada.")

        operations = {
            "publish_product": service.publish,
            "update_product": service.update,
            "sync_publication_stock": service.update_stock,
            "sync_publication_price": service.update_price,
            "sync_publication": service.sync_from_marketplace,
            "delete_product": service.delete,
        }
        return operations[self.job_type](self.publication_id)

    def _on_execution_failed(self, error):
        super()._on_execution_failed(error)
        for job in self:
            if job.publication_id and job.job_type in {
                "publish_product",
                "update_product",
                "sync_publication_stock",
                "sync_publication_price",
                "sync_publication",
                "delete_product",
            }:
                job.publication_id.write({"state": "failed", "error_message": str(error)})