from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    origen_precio_proveedor = fields.Char(
        'Origen Precio',
        compute='_compute_origen_precio',
        help='Indica si el precio viene de proveedor con reglas'
    )
    
    @api.depends('product_variant_ids.supplierinfo_ids.usar_costo_proveedor',
                 'product_variant_ids.supplierinfo_ids.regla_costo_id')
    def _compute_origen_precio(self):
        """Verifica que el proveedor tenga ✓ Usar Costo + Regla activa"""
        for record in self:
            usa_proveedor = False
            for variant in record.product_variant_ids:
                # Buscar proveedor con AMBOS: ✓ Usar Costo Y Regla definida
                proveedor_activo = variant.supplierinfo_ids.filtered(
                    lambda p: p.usar_costo_proveedor and p.regla_costo_id
                )
                if proveedor_activo:
                    usa_proveedor = True
                    break
            
            record.origen_precio_proveedor = 'Proveedor (Reglas)' if usa_proveedor else 'Manual'
    
    @api.depends('product_variant_ids.supplierinfo_ids.usar_costo_proveedor',
                 'product_variant_ids.supplierinfo_ids.regla_costo_id',
                 'product_variant_ids.supplierinfo_ids.price_discounted')
    def _compute_standard_price_proveedor(self):
        """Actualiza standard_price SOLO si proveedor tiene ✓ + Regla"""
        for record in self:
            variant = record.product_variant_ids[:1]
            if not variant:
                continue
                
            # Proveedor con AMBOS requisitos
            proveedor_valido = variant.supplierinfo_ids.filtered(
                lambda p: p.usar_costo_proveedor and p.regla_costo_id
            )
            
            if proveedor_valido:
                record.standard_price = proveedor_valido[0].price_discounted
                record.origen_precio_proveedor = 'Proveedor (Reglas)'
            else:
                # Precio manual/original
                record.standard_price = variant.standard_price or 0
                record.origen_precio_proveedor = 'Manual'