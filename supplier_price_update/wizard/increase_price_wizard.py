# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class IncreasePriceWizard(models.TransientModel):
    _name = 'increase.price.wizard'
    _description = 'Wizard para aumentar precio de proveedores'
    _table = "increase_price_wizard"  # Necesario para los permisos

    percentage = fields.Float(
        string='Porcentaje de aumento (%)',
        required=True,
        default=10.0,
    )
    
    supplier_info_ids = fields.Many2many(
        'product.supplierinfo',
        string='Productos seleccionados',
        readonly=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super(IncreasePriceWizard, self).default_get(fields_list)
        active_ids = self.env.context.get('active_ids', [])
        if active_ids:
            res['supplier_info_ids'] = [(6, 0, active_ids)]
        _logger.info('Wizard iniciado con IDs: %s', active_ids)
        return res

    def action_apply_increase(self):
        self.ensure_one()
        
        if not self.supplier_info_ids:
            raise UserError('No hay productos seleccionados.')
        
        if self.percentage < 0:
            raise UserError('El porcentaje no puede ser negativo.')
        
        # Aplicar el aumento
        count = 0
        for supplier_info in self.supplier_info_ids:
            current_price = supplier_info.price
            new_price = current_price * (1 + self.percentage / 100)
            supplier_info.price = new_price
            count += 1
            _logger.info('Precio actualizado: %s -> %s', current_price, new_price)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Éxito',
                'message': f'Precios aumentados en {self.percentage}% para {count} proveedor(es).',
                'type': 'success',
            }
        }