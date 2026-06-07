# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo import _

class AfipPadronWizard(models.TransientModel):
    _name = 'afip.padron.wizard'
    _description = 'Wizard Padrón AFIP'

    partner_id = fields.Many2one('res.partner', string='Contacto', readonly=True)
    cuit = fields.Char(string='CUIT/CUIL', required=True)
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('confirm', 'Confirmar'),
        ('done', 'Completado'),
    ], default='draft')
    
    denominacion = fields.Char(string='Denominación', readonly=True)
    estado = fields.Char(string='Estado', readonly=True)
    imp_iva = fields.Char(string='IVA', readonly=True)
    imp_ganancias = fields.Char(string='Ganancias', readonly=True)
    direccion = fields.Char(string='Dirección', readonly=True)
    localidad = fields.Char(string='Localidad', readonly=True)
    cod_postal = fields.Char(string='Código Postal', readonly=True)

    def action_search(self):
        self.ensure_one()
        if not self.cuit:
            raise UserError(_('Ingrese el CUIT'))
        
        # Por ahora, datos de prueba
        self.write({
            'denominacion': 'RAZÓN SOCIAL PRUEBA',
            'estado': 'ACTIVO',
            'imp_iva': 'AC',
            'imp_ganancias': 'AC',
            'direccion': 'AV CORRIENTES 1234',
            'localidad': 'CAPITAL FEDERAL',
            'cod_postal': 'C1043',
            'state': 'confirm',
        })
        return True

    def action_confirm(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_('No hay contacto'))
        
        vals = {
            'name': self.denominacion,
            'street': self.direccion,
            'city': self.localidad,
            'zip': self.cod_postal,
            'x_estado_padron': self.estado,
            'x_imp_iva_padron': self.imp_iva,
            'x_imp_ganancias_padron': self.imp_ganancias,
            'x_last_update_padron': fields.Date.today(),
        }
        
        self.partner_id.write(vals)
        self.state = 'done'
        
        return {'type': 'ir.actions.act_window_close'}