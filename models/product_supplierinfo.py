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
        domain="[('id', '!=', False)]"
    )
    
    price_discounted = fields.Float(
        'Costo Neto',
        compute='_compute_price_discounted',
        store=True,
        help='Precio tras aplicar reglas'
    )
    
    @api.depends('price', 'regla_costo_id', 'regla_costo_id.descuento_total', 'regla_costo_id.tarifa_total')
    def _compute_price_discounted(self):
        for record in self:
            if record.usar_costo_proveedor and record.regla_costo_id:
                precio_base = record.price or 0
                descuento = record.regla_costo_id.descuento_total / 100
                tarifa = record.regla_costo_id.tarifa_total
                
                precio_descuento = precio_base * (1 - descuento)
                record.price_discounted = precio_descuento + tarifa
            else:
                record.price_discounted = record.price or 0
    
    @api.onchange('usar_costo_proveedor')
    def _onchange_usar_costo(self):
        if not self.usar_costo_proveedor:
            self.regla_costo_id = False