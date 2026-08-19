# -*- coding: utf-8 -*-
from odoo import models
from odoo.exceptions import UserError


class MarketplacePublication(models.Model):
    _inherit = "marketplace.publication"

    def action_open_ml_publish_assistant(self):
        self.ensure_one()
        if self.provider_type != "mercadolibre":
            raise UserError("Este asistente aplica solo a publicaciones de MercadoLibre.")
        return {
            "type": "ir.actions.act_window",
            "res_model": "ml.publish.assistant.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_product_tmpl_id": self.product_tmpl_id.id,
                "default_publication_id": self.id,
                "default_step": "base",
            },
        }