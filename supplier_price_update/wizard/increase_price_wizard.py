# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError


class IncreasePriceWizard(models.TransientModel):
    _name = 'increase.price.wizard'
    _description = 'Wizard para aumentar precio de proveedores'
    _auto_join = True
    
    percentage = fields.Float(
        string='Porcentaje de aumento (%)',
        required=True,
        default=10.0,
    )

    @api.model
    def default_get(self, fields_list):
        res = super(IncreasePriceWizard, self).default_get(fields_list)
        # Obtener IDs de otra forma
        res['supplier_info_ids'] = self.env.context.get('active_ids', [])
        return res

    def action_apply_increase(self):
        active_ids = self.env.context.get('active_ids', [])
        
        if not active_ids:
            return {'type': 'ir.actions.act_window_close'}
        
        supplier_infos = self.env['product.supplierinfo'].browse(active_ids)
        
        for supplier_info in supplier_infos:
            new_price = supplier_info.price * (1 + self.percentage / 100)
            supplier_info.price = new_price
        
        return {
            'type': 'ir.actions.act_window_close',
            'info': f'Precios aumentados en {self.percentage}%',
        }
        