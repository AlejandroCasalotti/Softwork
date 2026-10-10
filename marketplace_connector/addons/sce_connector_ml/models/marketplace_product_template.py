# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    publication_ids = fields.One2many(
        "marketplace.publication", "product_tmpl_id", string="Publicaciones en marketplaces"
    )
    publication_count = fields.Integer(compute="_compute_publication_count")
    marketplace_publication_id = fields.Many2one(
        "marketplace.publication",
        string="Publicación marketplace principal",
        compute="_compute_marketplace_publication",
    )

    @api.depends("publication_ids")
    def _compute_publication_count(self):
        for product in self:
            product.publication_count = len(product.publication_ids)

    @api.depends("publication_ids", "publication_ids.external_id", "publication_ids.create_date")
    def _compute_marketplace_publication(self):
        for product in self:
            product.marketplace_publication_id = product.publication_ids.sorted(
                key=lambda publication: (bool(publication.external_id), publication.create_date or ""),
                reverse=True,
            )[:1]

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
