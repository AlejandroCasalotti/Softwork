from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    origen_precio_proveedor = fields.Char(
        'Origen Precio',
        compute='_compute_origen_precio',
        store=True,
        help='Indica si el precio viene de proveedor con reglas activas'  # ✅ Restaurado
    )
    
    standard_price = fields.Float(
        compute='_compute_standard_price_proveedor',
        store=True,
        inverse='_inverse_standard_price'
    )
    
    @api.depends('product_variant_ids.supplierinfo_ids.usar_costo_proveedor',
                 'product_variant_ids.supplierinfo_ids.regla_costo_id')  # ✅ Sincronizado
    def _compute_origen_precio(self):
        """Verifica que el proveedor tenga AMBOS: Usar Costo + Regla activa"""
        for record in self:
            proveedor_activo = False
            for variant in record.product_variant_ids:
                proveedor_con_regla = variant.supplierinfo_ids.filtered(
                    lambda p: p.usar_costo_proveedor and p.regla_costo_id  # ✅ AMBOS requisitos
                )
                if proveedor_con_regla:
                    proveedor_activo = True
                    break
            record.origen_precio_proveedor = 'Proveedor (Reglas)' if proveedor_activo else 'Manual'
    
    @api.depends('product_variant_ids.supplierinfo_ids.usar_costo_proveedor',
                 'product_variant_ids.supplierinfo_ids.regla_costo_id',
                 'product_variant_ids.supplierinfo_ids.price_discounted')
    def _compute_standard_price_proveedor(self):
        """Actualiza standard_price SOLO si proveedor tiene ambos requisitos"""
        for record in self:
            variant = record.product_variant_ids[:1]
            if not variant:
                record.standard_price = 0
                continue
            
            proveedor_valido = variant.supplierinfo_ids.filtered(
                lambda p: p.usar_costo_proveedor and p.regla_costo_id
            )
            if proveedor_valido:
                record.standard_price = proveedor_valido[0].price_discounted
            else:
                record.standard_price = variant.standard_price or 0
    
    def _inverse_standard_price(self):  # ✅ Ahora implementado
        """Permite editar standard_price manualmente cuando no hay proveedor activo"""
        for record in self:
            proveedor_activo = any(
                variant.supplierinfo_ids.filtered(
                    lambda p: p.usar_costo_proveedor and p.regla_costo_id
                )
                for variant in record.product_variant_ids
            )
            if not proveedor_activo:
                if record.product_variant_ids:
                    record.product_variant_ids[0].standard_price = record.standard_price