# -*- coding: utf-8 -*-
from odoo import fields, models


class MarketplaceProductMapping(models.Model):
    _name = "marketplace.product.mapping"
    _description = "Mapping de producto entre Odoo y un marketplace"
    _order = "create_date desc"

    publication_id = fields.Many2one(
        "marketplace.publication", required=True, ondelete="cascade", index=True
    )
    account_id = fields.Many2one(
        "sce.account", related="publication_id.account_id", store=True, index=True
    )
    product_tmpl_id = fields.Many2one(
        "product.template", required=True, ondelete="cascade", index=True
    )
    product_id = fields.Many2one("product.product", ondelete="cascade", index=True)
    external_id = fields.Char(string="ID externo", required=True, index=True)
    external_variant_id = fields.Char(string="ID variante externo", index=True)
    sku = fields.Char(string="SKU", index=True)
    active = fields.Boolean(default=True)

    _mapping_external_unique = models.Constraint(
        "UNIQUE(account_id, external_id, external_variant_id)",
        "El ID externo ya está mapeado para esta cuenta.",
    )
    _mapping_product_unique = models.Constraint(
        "UNIQUE(publication_id, product_id, external_variant_id)",
        "El producto ya tiene un mapping para esta publicación y variante.",
    )

    def name_get(self):
        result = []
        for mapping in self:
            product_name = mapping.product_id.display_name if mapping.product_id else mapping.product_tmpl_id.display_name
            result.append((mapping.id, "%s [%s]" % (product_name, mapping.external_id)))
        return result