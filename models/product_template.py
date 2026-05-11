from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    origen_precio_proveedor = fields.Char(
        'Origen Precio',
        compute='_compute_origen_precio',
        store=True  # ✅ Agregado
    )
    
    standard_price = fields.Float(
        compute='_compute_standard_price_proveedor',
        store=True,
        inverse='_inverse_standard_price'
    )
    
    @api.depends('product_variant_ids.supplierinfo_ids.usar_costo_proveedor')
    def _compute_origen_precio(self):
        """Detecta si el precio viene de proveedor"""
        for record in self:
            proveedor_activo = False
            for variant in record.product_variant_ids:
                if variant.supplierinfo_ids.filtered(lambda p: p.usar_costo_proveedor):
                    proveedor_activo = True
                    break
            record.origen_precio_proveedor = 'Proveedor' if proveedor_activo else 'Manual'
    
    @api.depends('product_variant_ids.supplierinfo_ids.usar_costo_proveedor',
                 'product_variant_ids.supplierinfo_ids.regla_costo_id',
                 'product_variant_ids.supplierinfo_ids.price_discounted')
    def _compute_standard_price_proveedor(self):
        """Actualiza standard_price con precio proveedor si está activo"""
        for record in self:
            variant = record.product_variant_ids[:1]
            if not variant:
                record.standard_price = 0
                continue
            
            proveedor = variant.supplierinfo_ids.filtered(
                lambda p: p.usar_costo_proveedor and p.regla_costo_id
            )
            
            record.standard_price = proveedor[0].price_discounted if proveedor else variant.standard_price or 0
    
    def _inverse_standard_price(self):
        """Permite editar standard_price manualmente"""
        pass  # O implementar lógica si es editable