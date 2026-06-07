# -*- coding: utf-8 -*-
from odoo import models, fields

class ResPartner(models.Model):
    _inherit = "res.partner"

    x_estado_padron = fields.Char(string='Estado AFIP', readonly=True, copy=False)
    x_imp_iva_padron = fields.Char(string='IVA AFIP', readonly=True, copy=False)
    x_imp_ganancias_padron = fields.Char(string='Ganancias AFIP', readonly=True, copy=False)
    x_last_update_padron = fields.Date(string='Última Actualización AFIP', readonly=True, copy=False)

    def action_update_from_padron_afip(self):
        self.ensure_one()
        if not self.vat:
            from odoo.exceptions import UserError
            raise UserError('Debe completar el CUIT/CUIL primero')
        
        return {
            'name': 'Actualizar desde Padrón AFIP',
            'type': 'ir.actions.act_window',
            'res_model': 'afip.padron.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
                'default_cuit': self.vat,
            },
        }