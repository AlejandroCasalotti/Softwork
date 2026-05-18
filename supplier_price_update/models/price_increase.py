# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.osv import expression


class ProductSupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    def action_increase_price(self):
        """
        Abre un wizard para aumentar el precio de los proveedores seleccionados.
        Esta méthode se llama desde la acción de servidor.
        """
        # Obtener los IDs de los registros seleccionados
        active_ids = self.env.context.get('active_ids', [])
        active_model = self.env.context.get('active_model', 'product.supplierinfo')
        
        # Verificar que estamos en el modelo correcto
        if active_model != 'product.supplierinfo':
            return False
            
        # Abrir el wizard
        return {
            'name': 'Aumentar Precio',
            'type': 'ir.actions.act_window',
            'res_model': 'increase.price.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_supplier_info_ids': [(6, 0, active_ids)],
            },
        }