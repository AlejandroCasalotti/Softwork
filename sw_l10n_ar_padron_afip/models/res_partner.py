# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo import _
import logging
import subprocess
import sys

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
        
        # Limpiar CUIT
        try:
            uit = ''.join(filter(str.isdigit, str(self.x_afip_cuit)))
        except:
            raise UserError(_('CUIT inválido'))
        
        if len(uit) != 11:
            raise UserError(_('El CUIT debe tener 11 dígitos sin guiones'))
        
        # Consultar AFIP
        try:
            datos_afip = self._consultar_afip(uit)
        except Exception as e:
            raise UserError(_(f'Error al consultar AFIP: {e}'))
        
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
    
    # CONSULTAR AFIP
    def _consultar_afip(self, cuit):
        """Consulta AFIP con instalación automática de pyafipws"""
        
        # Intentar importar pyafipws
        try:
            from pyafipws.padron import PadronAFIP
        except ImportError:
            # Intentar instalar
            _logger.info('Instalando pyafipws...')
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyafipws', 'cryptography'])
                from pyafipws.padron import PadronAFIP
            except Exception as e:
                raise UserError(_(
                    'No se pudo instalar pyafipws automaticamente.\n'
                    'Error: ' + str(e) + '\n\n'
                    'Contacte al administrador del servidor.'
                ))
        
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
        
        try:
            PadronAFIP = __import__('pyafipws.padron', fromlist=['PadronAFIP']).PadronAFIP
            Padron = PadronAFIP()
            Padron.CUIT = company_cuit
            
            # Usar certificados de l10n_ar
            try:
                if hasattr(company, 'l10n_ar_afip_ws_crt') and company.l10n_ar_afip_ws_crt:
                    import tempfile
                    import os
                    import base64
                    
                    cert_data = base64.b64decode(company.l10n_ar_afip_ws_crt)
                    key_data = None
                    
                    if hasattr(company, 'l10n_ar_afip_ws_key') and company.l10n_ar_afip_ws_key:
                        key_data = base64.b64decode(company.l10n_ar_afip_ws_key)
                    
                    with tempfile.NamedTemporaryFile(suffix='.crt', delete=False) as cf:
                        cf.write(cert_data)
                        cert_path = cf.name
                    
                    with open(cert_path, 'r') as f:
                        Padron.SetCertificate(f.read())
                    
                    if key_data:
                        with tempfile.NamedTemporaryFile(suffix='.key', delete=False) as kf:
                            kf.write(key_data)
                            key_path = kf.name
                        with open(key_path, 'r') as f:
                            Padron.SetPrivateKey(f.read())
                        try:
                            os.unlink(key_path)
                        except:
                            pass
                    
                    try:
                        os.unlink(cert_path)
                    except:
                        pass
            except Exception as e:
                _logger.warning(f'Error con certificado: {e}')
            
            # Conectar
            try:
                env = getattr(company, 'l10n_ar_afip_ws_environment', 'production') or 'production'
                Padron.Conectar(env)
            except:
                Padron.Conectar('testing')
            
            # Consultar
            Padron.Consultar(cuit)
            
            # Extraer datos
            datos = {
                'name': getattr(Padron, 'denominacion', ''),
                'estado': getattr(Padron, 'estado', ''),
                'street': getattr(Padron, 'direccion', ''),
                'city': getattr(Padron, 'localidad', ''),
                'zip': getattr(Padron, 'cod_postal', ''),
                'provincia': getattr(Padron, 'provincia', ''),
            }
            
            # IVA
            imp_iva = getattr(Padron, 'imp_iva', 'N')
            if imp_iva == 'S':
                datos['imp_iva'] = 'Responsable Inscripto'
            elif imp_iva == 'N':
                datos['imp_iva'] = 'No Inscripto'
            else:
                datos['imp_iva'] = imp_iva
            
            # Ganancias
            imp_gan = getattr(Padron, 'imp_ganancias', 'NI')
            if imp_gan == 'AC':
                datos['imp_ganancias'] = 'Activo'
            elif imp_gan == 'EX':
                datos['imp_ganancias'] = 'Exento'
            else:
                datos['imp_ganancias'] = imp_gan
            
            return datos
            
        except Exception as e:
            _logger.error(f'Error AFIP: {e}')
            raise UserError(_(f'Error al consultar: {e}'))
    
    def _buscar_provincia(self, nombre):
        """Busca provincia"""
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