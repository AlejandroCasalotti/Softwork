# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    origen_precio_proveedor = fields.Char(
        'Origen Precio',
        compute='_compute_origen_precio',
        store=True,
        help='Indica si el precio viene de proveedor con reglas activas'
    )
    
    standard_price = fields.Float(
        compute='_compute_standard_price_proveedor',
        store=True,
        inverse='_inverse_standard_price'
    )
    
    @api.depends('product_variant_ids.supplierinfo_ids.usar_costo_proveedor',
                 'product_variant_ids.supplierinfo_ids.regla_costo_id')
    def _compute_origen_precio(self):
        """Verifica que el proveedor tenga AMBOS: Usar Costo + Regla activa"""
        for record in self:
            proveedor_activo = False
            for variant in record.product_variant_ids:
                proveedor_con_regla = variant.supplierinfo_ids.filtered(
                    lambda p: p.usar_costo_proveedor and p.regla_costo_id
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
            # Obtener primera variante disponible
            variant = record.product_variant_ids[:1]
            if not variant:
                record.standard_price = 0
                continue
            
            # Filtrar proveedores válidos (con AMBOS requisitos)
            proveedor_valido = variant.supplierinfo_ids.filtered(
                lambda p: p.usar_costo_proveedor and p.regla_costo_id
            )
            
            if proveedor_valido:
                precio = proveedor_valido[0].price_discounted or 0
                record.standard_price = max(precio, 0)  # Evitar precios negativos
            else:
                record.standard_price = variant.standard_price or 0
    
    def _inverse_standard_price(self):
        """Permite editar standard_price manualmente cuando no hay proveedor activo"""
        for record in self:
            # Validar que existan variantes
            if not record.product_variant_ids:
                continue
            
            # Verificar si hay proveedor activo con reglas
            proveedor_activo = any(
                variant.supplierinfo_ids.filtered(
                    lambda p: p.usar_costo_proveedor and p.regla_costo_id
                )
                for variant in record.product_variant_ids
            )
            
            # Solo permitir edición manual si NO hay proveedor con reglas
            if not proveedor_activo:
                # Validar que el precio sea positivo
                nuevo_precio = max(record.standard_price, 0)
                # Actualizar todas las variantes
                for variant in record.product_variant_ids:
                    variant.standard_price = nuevo_precio
