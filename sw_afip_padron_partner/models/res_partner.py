# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo import _
import logging
import requests

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    # CAMPOS AFIP
    estado_padron = fields.Char('Estado AFIP')
    imp_ganancias_padron = fields.Selection([
        ('NI', 'No Inscripto'),
        ('AC', 'Activo'),
        ('EX', 'Exento'),
        ('NC', 'No corresponde'),
    ], 'Ganancias')
    imp_iva_padron = fields.Selection([
        ('NI', 'No Inscripto'),
        ('AC', 'Activo'),
        ('EX', 'Exento'),
        ('NA', 'No alcanzado'),
    ], 'IVA')
    monotributo_padron = fields.Selection([('N', 'No'), ('S', 'Si')], 'Monotributo')
    empleador_padron = fields.Boolean('Empleador')
    last_update_padron = fields.Date('Last Update Padron')
    activities_padron = fields.Char('Actividades')

    def update_constancia_from_padron_afip(self):
        """Actualiza desde Padrón AFIP usando API"""
        self.ensure_one()
        
        # Obtener CUIT del partner
        cuit = self.vat
        if not cuit:
            raise UserError(_('Debe tener un CUIT configurado en el campo VAT'))
        
        # Limpiar CUIT
        try:
            cuit = ''.join(filter(str.isdigit, str(cuit)))
        except:
            raise UserError(_('CUIT inválido'))
        
        if len(cuit) != 11:
            raise UserError(_('El CUIT debe tener 11 dígitos sin guiones'))
        
        # Consultar usando API
        datos = self._consultar_afip_api(cuit)
        
        if not datos:
            raise UserError(_(
                '⚠️ No se pudo obtener datos de AFIP\n\n'
                'Verifique el CUIT o intente más tarde.'
            ))
        
        # Buscar provincia
        state_id = False
        if datos.get('provincia'):
            state = self.env['res.country.state'].search([
                ('name', 'ilike', datos['provincia']),
                ('country_id.code', '=', 'AR'),
            ], limit=1)
            if state:
                state_id = state.id
            else:
                # Buscar por código comunes
                mapas = {'santa fe': 'S', 'buenos aires': 'B', 'capital federal': 'CABA'}
                nombre_lower = datos['provincia'].lower().strip()
                if nombre_lower in mapas:
                    state = self.env['res.country.state'].search([
                        ('code', '=', mapas[nombre_lower]),
                        ('country_id.code', '=', 'AR'),
                    ], limit=1)
                    if state:
                        state_id = state.id
        
        # Actualizar datos
        vals = {
            'name': datos.get('name', '') or self.name,
            'street': datos.get('direccion', '') or self.street,
            'city': datos.get('localidad', '') or self.city,
            'zip': datos.get('cod_postal', '') or self.zip,
            'state_id': state_id or self.state_id,
            'estado_padron': datos.get('estado', ''),
            'imp_iva_padron': datos.get('imp_iva', 'NI'),
            'imp_ganancias_padron': datos.get('imp_ganancias', 'NI'),
            'monotributo_padron': datos.get('monotributo', 'N'),
            'empleador_padron': datos.get('empleador', False),
            'last_update_padron': fields.Date.today(),
            'activities_padron': datos.get('actividades', ''),
        }
        
        self.write(vals)
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def _consultar_afip_api(self, cuit):
        """Consulta AFIP usando API REST"""
        
        # Intentar diferentes APIs públicas
        apis = [
            f"https://afipapi.com.ar/api/cuit/{cuit}",
            f"https://api.factorial.com.ar/afip/cuit/{cuit}",
            f"https://argencedata.com/api/v1/cuit/{cuit}",
        ]
        
        for url in apis:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success') or data.get('data'):
                        return self._procesar_datos_api(data)
            except:
                continue
        
        # Si no hay APIs disponibles, abrir página de AFIP
        return None
    
    def _procesar_datos_api(self, data):
        """Procesa la respuesta de la API"""
        if data.get('data'):
            data = data['data']
        
        return {
            'name': data.get('denominacion') or data.get('nombre') or '',
            'estado': data.get('estado') or 'Activo',
            'direccion': data.get('direccion') or '',
            'localidad': data.get('localidad') or '',
            'cod_postal': data.get('cod_postal') or data.get('cp') or '',
            'provincia': data.get('provincia') or '',
            'imp_iva': data.get('imp_iva') or 'NI',
            'imp_ganancias': data.get('imp_ganancias') or 'NI',
            'monotributo': data.get('monotributo') or 'N',
            'empleador': data.get('empleador') == 'S',
            'actividades': data.get('actividades') or '',
        }