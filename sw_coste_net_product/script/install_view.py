# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class InstallViewScript(models.TransientModel):
    _name = 'install.view.script'
    _description = 'Script para instalar vista'

    def action_install_view(self):
        """Instala la vista heredada para product.supplierinfo"""
        
        # Buscar la vista original
        original_view = self.env['ir.ui.view'].search([
            ('model', '=', 'product.supplierinfo'),
            ('type', '=', 'form'),
            ('inherit_id', '=', False),
        ], limit=1)
        
        if not original_view:
            _logger.warning('No se encontró vista original de product.supplierinfo')
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Advertencia',
                    'message': 'No se encontró la vista original para heredar',
                    'type': 'warning',
                }
            }
        
        # Crear la vista heredada
        view_values = {
            'name': 'product.supplierinfo.form.costenet',
            'model': 'product.supplierinfo',
            'inherit_id': original_view.id,
            'arch': '''
                <xpath expr="//field[@name='price']" position="after">
                    <field name="rule_id"/>
                    <field name="price_net" readonly="1" 
                           attrs="{'invisible': [('rule_id', '=', False)]}"/>
                </xpath>
            ''',
            'active': True,
        }
        
        # Verificar si ya existe
        existing = self.env['ir.ui.view'].search([
            ('name', '=', 'product.supplierinfo.form.costenet'),
            ('model', '=', 'product.supplierinfo'),
        ])
        
        if existing:
            existing.write(view_values)
            _logger.info('Vista actualizada')
        else:
            self.env['ir.ui.view'].create(view_values)
            _logger.info('Vista creada')
        
        # Invalidar caché
        self.env['ir.ui.view'].clear_caches()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Éxito',
                'message': 'Vista heredada instalada correctamente',
                'type': 'success',
            }
        }