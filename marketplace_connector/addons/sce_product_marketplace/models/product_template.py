# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    publication_ids = fields.One2many(
        "marketplace.publication", "product_tmpl_id", string="Publicaciones en marketplaces"
    )
    publication_count = fields.Integer(compute="_compute_publication_count")

    @api.depends("publication_ids")
    def _compute_publication_count(self):
        for product in self:
            product.publication_count = len(product.publication_ids)

    def action_open_marketplace_new_publication(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "marketplace.publication",
            "view_mode": "form",
            "target": "current",
            "context": {"default_product_tmpl_id": self.id},
        }

    def action_view_marketplace_publications(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "marketplace.publication",
            "view_mode": "list,form",
            "domain": [("product_tmpl_id", "=", self.id)],
            "context": {"default_product_tmpl_id": self.id},
        }
