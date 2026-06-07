# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo import _

class ResPartner(models.Model):
    _inherit = "res.partner"

    # Campo AFIP
    x_afip_cuit = fields.Char(
        string='AFIP CUIT',
        help='CUIT para consultar Padrón AFIP',
    )
    
    x_estado_padron = fields.Char(
        string='Estado AFIP',
        readonly=True,
    )
    
    x_last_update_padron = fields.Date(
        string='Última Actualización',
        readonly=True,
    )

    @api.onchange('x_afip_cuit')
    def _onchange_afip_cuit(self):
        """Se ejecuta cuando cambia el CUIT"""
        if self.x_afip_cuit and len(self.x_afip_cuit) >= 11:
            # Habilitar botón automáticamente
            pass
    
    def action_update_from_padron_afip(self):
        """Actualizar desde Padrón AFIP"""
        self.ensure_one()
        
        if not self.x_afip_cuit:
            raise UserError(_('Debe ingresar el CUIT'))
        
        # Limpiar CUIT
        try:
            cuit = ''.join(filter(str.isdigit, str(self.x_afip_cuit)))
        except:
            raise UserError(_('CUIT inválido'))
        
        if len(cuit) != 11:
            raise UserError(_('El CUIT debe tener 11 dígitos'))
        
        # Por ahora, datos de prueba
        # En producción, aquí iría la conexión a AFIP
        self.write({
            'name': 'RAZÓN SOCIAL ACTUALIZADA',
            'street': 'AV CORRIENTES 1234',
            'city': 'CAPITAL FEDERAL',
            'zip': 'C1043',
            'x_estado_padron': 'ACTIVO',
            'x_last_update_padron': fields.Date.today(),
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }