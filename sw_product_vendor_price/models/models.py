# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ProductSupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    # Campo margen de venta en porcentaje
    sale_margin = fields.Float(
        string='Margen de Venta (%)',
        digits='Product Price',
        default=0.0,
        help='Porcentaje de margen a добавить al standard_price para calcular el list_price'
    )
    
    # Precio almacenable del proveedor (para edición manual)
    vendor_price = fields.Float(
        string='Precio Proveedor',
        digits='Product Price',
        default=0.0,
        help='Precio del proveedor. Se copia a standard_price del producto.'
    )
    
    # Flag para habilitar sincronización
    sync_enabled = fields.Boolean(
        string='Sincronizar con Producto',
        default=True,
        help='Si está activo, sincroniza el precio con el producto'
    )

    @api.onchange('price')
    def _onchange_price(self):
        """Cuando cambia el precio del proveedor, actualizar vendor_price"""
        for record in self:
            if record.sync_enabled:
                record.vendor_price = record.price

    @api.onchange('vendor_price')
    def _onchange_vendor_price(self):
        """Cuando cambia vendor_price, actualizar el precio del proveedor y standard_price"""
        for record in self:
            if record.sync_enabled:
                record.price = record.vendor_price
                record._sync_to_product()

    def _sync_to_product(self):
        """Sincroniza el precio al standard_price del producto"""
        self.ensure_one()
        if self.product_id and self.sync_enabled:
            # Actualizar el standard_price del producto
            self.product_id.standard_price = self.vendor_price
            
            # Calcular y actualizar el list_price con el margen
            self._update_list_price_with_margin()

    def _update_list_price_with_margin(self):
        """Calcula el list_price basándose en el margen de venta"""
        self.ensure_one()
        if self.product_id and self.sale_margin > 0:
            # Fórmula: list_price = standard_price * (1 + margen/100)
            cost = self.vendor_price
            margin_percent = self.sale_margin
            new_list_price = cost * (1 + margin_percent / 100.0)
            self.product_id.list_price = new_list_price


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # Campo para indicar si el precio fue modificado manualmente
    manual_standard_price = fields.Boolean(
        string='Precio Manual',
        default=False,
        help='Indica si el standard_price fue modificado manualmente'
    )

    @api.onchange('standard_price')
    def _onchange_standard_price(self):
        """Marca como manual cuando se modifica el standard_price"""
        for record in self:
            record.manual_standard_price = True

    def write(self, vals):
        """Override del método write para actualizar precios de proveedor"""
        result = super(ProductProduct, self).write(vals)
        
        if 'standard_price' in vals:
            # Buscar lista de precios de proveedor activa
            supplierinfos = self.env['product.supplierinfo'].search([
                ('product_id', '=', self.id),
                ('sync_enabled', '=', True)
            ], order='sequence, min_qty desc', limit=1)
            
            if supplierinfos:
                for supplierinfo in supplierinfos:
                    # Actualizar vendor_price y price en supplierinfo
                    supplierinfo.vendor_price = self.standard_price
                    supplierinfo.price = self.standard_price
                    
                    # Recalcular list_price si hay margen
                    if supplierinfo.sale_margin > 0:
                        new_list_price = self.standard_price * (1 + supplierinfo.sale_margin / 100.0)
                        self.list_price = new_list_price
        
        return result


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # Campo para forzar actualización de precios
    force_price_sync = fields.Boolean(
        string='Forzar Sincronización',
        default=False,
        help='Al marcar, sincroniza los precios desde el proveedor'
    )

    @api.onchange('force_price_sync')
    def _onchange_force_price_sync(self):
        """Fuerza la sincronización de precios"""
        if self.force_price_sync and self.product_variant_id:
            supplierinfos = self.env['product.supplierinfo'].search([
                ('product_tmpl_id', '=', self.id),
                ('sync_enabled', '=', True)
            ], order='sequence, min_qty desc', limit=1)
            
            if supplierinfos:
                # Sincronizar standard_price
                self.product_variant_id.standard_price = supplierinfos.vendor_price
                # Aplicar margen
                if supplierinfos.sale_margin > 0:
                    new_list_price = supplierinfos.vendor_price * (1 + supplierinfos.sale_margin / 100.0)
                    self.list_price = new_list_price
            
            # Resetear el flag
            self.force_price_sync = False