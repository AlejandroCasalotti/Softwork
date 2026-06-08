# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo import _
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    # CAMPOS AFIP
    x_afip_cuit = fields.Char(string='AFIP CUIT', help='CUIT sin guiones')
    x_estado_padron = fields.Char(string='Estado AFIP', readonly=True)
    x_imp_iva_padron = fields.Char(string='IVA AFIP', readonly=True)
    x_imp_ganancias_padron = fields.Char(string='Ganancias AFIP', readonly=True)
    x_last_update_padron = fields.Date(string='Última Actualización AFIP', readonly=True)
    
    # BOTÓN PRINCIPAL
    def action_update_from_padron_afip(self):
        """Consulta y actualiza desde Padrón AFIP"""
        self.ensure_one()
        
        if not self.x_afip_cuit:
            raise UserError(_('Debe ingresar el CUIT primero'))
        
        # Limpiar CUIT - CORREGIDO (era 'uit' ahora 'cuit')
        try:
            cuit = ''.join(filter(str.isdigit, str(self.x_afip_cuit)))
        except:
            raise UserError(_('CUIT inválido'))
        
        if len(cuit) != 11:
            raise UserError(_('El CUIT debe tener 11 dígitos sin guiones'))
        
        # Consultar AFIP
        datos_afip = self._consultar_ws_afip(cuit)
        
        if not datos_afip:
            raise UserError(_('No se pudieron obtener datos de AFIP'))
        
        # Buscar país Argentina
        pais_argentina = self.env.ref('base.ar')
        
        # Buscar provincia
        state_id = False
        if datos_afip.get('provincia'):
            state_id = self._buscar_provincia(datos_afip['provincia'])
        
        # Actualizar datos
        vals = {
            'name': datos_afip.get('name', '') or self.name,
            'street': datos_afip.get('street', '') or self.street,
            'city': datos_afip.get('city', '') or self.city,
            'zip': datos_afip.get('zip', '') or self.zip,
            'state_id': state_id or self.state_id,
            'country_id': pais_argentina.id if pais_argentina else self.country_id.id,
            'x_estado_padron': datos_afip.get('estado', ''),
            'x_imp_iva_padron': datos_afip.get('imp_iva', ''),
            'x_imp_ganancias_padron': datos_afip.get('imp_ganancias', ''),
            'x_last_update_padron': fields.Date.today(),
        }
        
        self.write(vals)
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    # WEB SERVICE OFICIAL AFIP
    def _consultar_ws_afip(self, cuit):
        """Consulta usando Web Service oficial de AFIP"""
        # Obtener compañía
        company = self.env.company
        if not company:
            company = self.env['res.company'].search([], limit=1)
        
        if not company:
            raise UserError(_('No hay compañía configurada'))
        
        # Obtener CUIT de la compañía
        try:
            company_cuit = ''.join(filter(str.isdigit, str(company.vat or '')))
        except:
            company_cuit = ''
        
        if not company_cuit:
            raise UserError(_('La compañía no tiene CUIT configurado'))
        
        # Intentar importar pyafipws
        try:
            from pyafipws.padron import PadronAFIP
        except ImportError:
            raise UserError(_('Instale pyafipws: pip install pyafipws'))
        
        try:
            padron = PadronAFIP()
            padron.CUIT = company_cuit
            
            # Intentar certificado desde compañía
            try:
                if company.afip_crt and company.afip_key:
                    import tempfile
                    import os
                    import base64
                    
                    cert_data = base64.b64decode(company.afip_crt)
                    key_data = base64.b64decode(company.afip_key)
                    
                    with tempfile.NamedTemporaryFile(suffix='.crt', delete=False) as cf:
                        cf.write(cert_data)
                        cert_path = cf.name
                    
                    with tempfile.NamedTemporaryFile(suffix='.key', delete=False) as kf:
                        kf.write(key_data)
                        key_path = kf.name
                    
                    with open(cert_path, 'r') as f:
                        padron.SetCertificate(f.read())
                    with open(key_path, 'r') as f:
                        padron.SetPrivateKey(f.read())
                    
                    try:
                        os.unlink(cert_path)
                        os.unlink(key_path)
                    except:
                        pass
            except:
                pass
            
            # Conectar
            try:
                padron.Conectar('production')
            except:
                padron.Conectar('testing')
            
            # Consultar CUIT
            padron.Consultar(cuit)
            
            # Extraer datos
            datos = {
                'name': getattr(padron, 'denominacion', ''),
                'estado': getattr(padron, 'estado', ''),
                'street': getattr(padron, 'direccion', ''),
                'city': getattr(padron, 'localidad', ''),
                'zip': getattr(padron, 'cod_postal', ''),
                'provincia': getattr(padron, 'provincia', ''),
            }
            
            # Procesar IVA
            imp_iva = getattr(padron, 'imp_iva', 'N')
            if imp_iva == 'S':
                datos['imp_iva'] = 'Responsable Inscripto'
            elif imp_iva == 'N':
                datos['imp_iva'] = 'No Inscripto'
            elif imp_iva == 'EX':
                datos['imp_iva'] = 'Exento'
            else:
                datos['imp_iva'] = imp_iva
            
            # Ganancias
            imp_gan = getattr(padron, 'imp_ganancias', 'NI')
            if imp_gan == 'AC':
                datos['imp_ganancias'] = 'Activo'
            elif imp_gan == 'EX':
                datos['imp_ganancias'] = 'Exento'
            else:
                datos['imp_ganancias'] = 'No Inscripto'
            
            return datos
            
        except Exception as e:
            _logger.error(f'Error WS AFIP: {e}')
            raise UserError(_(f'Error al consultar AFIP: {e}'))
    
    def _buscar_provincia(self, nombre):
        """Busca provincia por nombre"""
        if not nombre:
            return False
        
        state = self.env['res.country.state'].search([
            ('name', 'ilike', nombre),
            ('country_id.code', '=', 'AR'),
        ], limit=1)
        
        if state:
            return state.id
        
        mapas = {
            'santa fe': 'S', 'buenos aires': 'B', 'capital federal': 'CABA',
            'caba': 'CABA', 'mendoza': 'M', 'tucuman': 'T',
            'cordoba': 'X', 'entre rios': 'E', 'corrientes': 'W',
            'misiones': 'N', 'chaco': 'H', 'jujuy': 'Y',
            'salta': 'A', 'catamarca': 'K', 'la rioja': 'F',
            'san juan': 'J', 'san luis': 'D', 'la pampa': 'L',
            'neuquen': 'Q', 'rio negro': 'R', 'chubut': 'U',
            'santa cruz': 'Z', 'tierra del fuego': 'V',
        }
        
        nombre_lower = nombre.lower().strip()
        if nombre_lower in mapas:
            state = self.env['res.country.state'].search([
                ('code', '=', mapas[nombre_lower]),
                ('country_id.code', '=', 'AR'),
            ], limit=1)
            if state:
                return state.id
        
        return False