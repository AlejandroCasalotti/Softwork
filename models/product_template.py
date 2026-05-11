from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    # Añadir campo para mostrar origen del precio
    origen_precio_proveedor = fields.Char(
        'Origen Precio',
        compute='_compute_origen_precio',
        help='Indica si el precio viene de proveedor'
    )
    
    @api.depends('product_variant_ids', 'product_variant_ids.supplierinfo_ids')
    def _compute_origen_precio(self):
        for record in self:
            proveedor_activo = False
            for variant in record.product_variant_ids:
                proveedor = variant.supplierinfo_ids.filtered(
                    lambda p: p.usar_costo_proveedor
                )
                if proveedor:
                    proveedor_activo = True
                    break
            
            record.origen_precio_proveedor = 'Proveedor' if proveedor_activo else 'Manual'
    
    @api.depends('product_variant_ids.supplierinfo_ids.usar_costo_proveedor',
                 'product_variant_ids.supplierinfo_ids.regla_costo_id',
                 'product_variant_ids.supplierinfo_ids.price_discounted')
    def _compute_standard_price_proveedor(self):
        """Actualiza standard_price con precio proveedor si está activo"""
        for record in self:
            # Tomar primer variant
            variant = record.product_variant_ids[:1]
            if not variant:
                continue
                
            # Buscar proveedor activo con reglas
            proveedor = variant.supplierinfo_ids.filtered(
                lambda p: p.usar_costo_proveedor and p.regla_costo_id
            )
            
            if proveedor:
                # Usar precio descontado del proveedor principal
                record.standard_price = proveedor[0].price_discounted
            else:
                # Mantener precio original del variant
                record.standard_price = variant.standard_price or 0