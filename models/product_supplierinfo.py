from odoo import models, fields, api

class ProductSupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'
    
    usar_costo_proveedor = fields.Boolean(
        'Usar Costo Proveedor',
        help='Activar para usar precio proveedor con reglas'
    )
    
    regla_costo_id = fields.Many2one(
        'coste.proveedor.regla',
        'Regla de Costo',
        domain="[('linea_ids', '!=', False)]",  # Solo reglas con líneas
        states="{'invisible': [('usar_costo_proveedor', '=', False)], 'required': [('usar_costo_proveedor', '=', True)]}"
    )
    
    price_discounted = fields.Float(
        'Costo Neto',
        compute='_compute_price_discounted',
        store=True,
        help='Precio tras aplicar reglas (solo si ✓ Usar Costo + Regla)'
    )
    
    @api.depends('price', 'usar_costo_proveedor', 'regla_costo_id.linea_ids')
    def _compute_price_discounted(self):
        for record in self:
            if (record.usar_costo_proveedor 
                and record.regla_costo_id 
                and record.regla_costo_id.linea_ids):
                
                precio_base = record.price or 0.0
                
                # Aplicar descuentos en cascada (multiplicativos)
                precio_con_descuento = precio_base
                for linea in record.regla_costo_id.linea_ids:
                    precio_con_descuento *= (1 - linea.porcentaje_descuento / 100)
                
                # Sumar tarifas extras
                tarifa_total = sum(record.regla_costo_id.linea_ids.mapped('tarifa_extra'))
                record.price_discounted = precio_con_descuento + tarifa_total
            else:
                record.price_discounted = record.price or 0.0
    
    @api.onchange('usar_costo_proveedor')
    def _onchange_usar_costo_proveedor(self):
        """Reset regla si desactiva usar costo"""
        if not self.usar_costo_proveedor:
            self.regla_costo_id = False
            self.price_discounted = self.price or 0.0
    
    @api.onchange('regla_costo_id')
    def _onchange_regla_costo(self):
        """Validar regla tiene líneas"""
        if self.regla_costo_id and not self.regla_costo_id.linea_ids:
            return {
                'warning': {
                    'title': 'Regla Inválida',
                    'message': 'La regla seleccionada no tiene líneas de descuento/tarifa.'
                }
            }
