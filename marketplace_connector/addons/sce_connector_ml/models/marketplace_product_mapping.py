# -*- coding: utf-8 -*-
from odoo import fields, models


class MarketplaceProductMapping(models.Model):
    _name = "marketplace.product.mapping"
    _description = "Mapping de producto entre Odoo y un marketplace"
    _order = "create_date desc"

    account_id = fields.Many2one(
        "sce.account", string="Cuenta", required=True, ondelete="cascade", index=True
    )
    publication_id = fields.Many2one(
        "marketplace.publication", string="Publicación", required=False, ondelete="set null", index=True
    )
    product_tmpl_id = fields.Many2one(
        "product.template", string="Plantilla de Producto", required=False, ondelete="cascade", index=True
    )
    product_id = fields.Many2one("product.product", string="Variante de Producto", required=False, ondelete="cascade", index=True)
    external_id = fields.Char(string="ID externo", required=True, index=True)
    external_variant_id = fields.Char(string="ID variante externo", index=True)
    sku = fields.Char(string="SKU", index=True)
    barcode = fields.Char(string="Código de Barras", index=True)
    # True cuando el producto solo existe en el Odoo remoto del cliente (sin módulo instalado)
    # y por lo tanto no hay product_id/product_tmpl_id local; se sincroniza vía XML-RPC directo.
    remote_only = fields.Boolean(string="Vinculado solo por Odoo remoto", default=False)
    last_synced_price = fields.Float(string="Último precio sincronizado a ML")
    active = fields.Boolean(default=True)

    _mapping_external_unique = models.Constraint(
        "UNIQUE(account_id, external_id, external_variant_id)",
        "El ID externo ya está mapeado para esta cuenta.",
    )

    def name_get(self):
        result = []
        for mapping in self:
            product_name = (
                (mapping.product_id.display_name if mapping.product_id else False)
                or (mapping.product_tmpl_id.display_name if mapping.product_tmpl_id else False)
                or mapping.sku
                or "Producto sin vincular"
            )
            result.append((mapping.id, "%s [%s]" % (product_name, mapping.external_id)))
        return result