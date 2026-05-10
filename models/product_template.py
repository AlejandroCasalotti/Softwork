from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    @api.depends('product_variant_ids.supplierinfo_ids.price_discounted')
    def _compute_standard_price_proveedor(self):
        for record in self:
            # Buscar proveedor principal activo con costo proveedor
            proveedor = record.product_variant_ids[:1].supplierinfo_ids.filtered(
                lambda p: p.usar_costo_proveedor
            )
            if proveedor:
                record.standard_price = proveedor[0].price_discounted
            else:
                # Costo normal si no hay proveedor con reglas
                record.standard_price = record.product_variant_ids[:1].standard_price or 0