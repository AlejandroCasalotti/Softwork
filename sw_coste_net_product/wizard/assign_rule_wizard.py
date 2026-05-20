# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import _


class AssignRuleWizard(models.TransientModel):
    _name = 'assign.rule.wizard'
    _description = 'Wizard para asignar regla de costo'

    rule_id = fields.Many2one(
        'coste.net.rule', 
        string='Regla de Costo',
        required=True
    )

    def action_assign(self):
        active_ids = self.env.context.get('active_ids', [])
        if not active_ids:
            return {'type': 'ir.actions.act_window_close'}
        
        supplier_infos = self.env['product.supplierinfo'].browse(active_ids)
        supplier_infos.write({'rule_id': self.rule_id.id})
        
        return {'type': 'ir.actions.act_window_close'}