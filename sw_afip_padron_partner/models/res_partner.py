# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo import _
import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    # ============================================================
    # CAMPOS AFIP
    # ============================================================
    
    x_afip_cuit = fields.Char(
        string='AFIP CUIT',
        help='CUIT para consultar Padrón AFIP (sin guiones)',
    )
    
    x_estado_padron = fields.Char(
        string='Estado AFIP',
        readonly=True,
    )
    
    x_imp_iva_padron = fields.Char(
        string='IVA AFIP',
        readonly=True,
    )
    
    x_imp_ganancias_padron = fields.Char(
        string='Ganancias AFIP',
        readonly=True,
    )
    
    x_last_update_padron = fields.Date(
        string='Última Actualización AFIP',
        readonly=True,
    )
    
    # ============================================================
    # BOTÓN PRINCIPAL
    # ============================================================
    
    def action_update_from_padron_afip(self):
        """
        Consulta y actualiza desde Padrón AFIP
        """
        self.ensure_one()
        
        # Validar CUIT
        if not self.x_afip_cuit:
            raise UserError(_('Debe ingresar el CUIT primero'))
        
        try:
            # Limpiar CUIT (solo números)
            cuit = ''.join(filter(str.isdigit, str(self.x_afip_cuit)))
        except:
            raise UserError(_('CUIT inválido'))
        
        if len(cuit) != 11:
            raise UserError(_('El CUIT debe tener 11 dígitos sin guiones'))
        
        # Consultar AFIP
        try:
            datos_afip = self._consultar_padron_afip(cuit)
        except Exception as e:
            _logger.error(f'Error consultando AFIP: {str(e)}')
            raise UserError(_(f'Error al consultar AFIP: {str(e)}'))
        
        if not datos_afip:
            raise UserError(_('No se encontraron datos para este CUIT'))
        
        # Actualizar datos del contacto
        vals = {
            'x_estado_padron': datos_afip.get('estado', ''),
            'x_imp_iva_padron': datos_afip.get('imp_iva', ''),
            'x_imp_ganancias_padron': datos_afip.get('imp_ganancias', ''),
            'x_last_update_padron': fields.Date.today(),
        }
        
        # Si el nombre actual está vacío o esgenérico, usar el de AFIP
        if not self.name or self.name == '/':
            if datos_afip.get('name'):
                vals['name'] = datos_afip['name']
        
        # Actualizar dirección
        if datos_afip.get('street'):
            vals['street'] = datos_afip['street']
        
        if datos_afip.get('city'):
            vals['city'] = datos_afip['city']
        
        if datos_afip.get('zip'):
            vals['zip'] = datos_afip['zip']
        
        # Buscar provincia
        if datos_afip.get('provincia'):
            state_id = self._buscar_provincia(datos_afip['provincia'])
            if state_id:
                vals['state_id'] = state_id
        
        # Buscar país Argentina
        pais_argentina = self.env.ref('base.ar')
        if pais_argentina:
            vals['country_id'] = pais_argentina.id
        
        # Escribir los datos
        self.write(vals)
        
        # Mostrar mensaje de éxito
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    # ============================================================
    # MÉTODO DE CONSULTA A AFIP
    # ============================================================
    
    def _consultar_padron_afip(self, cuit):
        """
        Consulta el Padrón AFIP - ws_sr_padron_a4
        """
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
            raise UserError(_(
                'La compañía no tiene CUIT configurado. '
                'Configure el VAT en: Configuración > Compañías'
            ))
        
        try:
            from pyafipws.padron import PadronAFIP
        except ImportError:
            raise UserError(_(
                'No está instalado pyafipws. '
                'Instale con: pip install pyafipws'
            ))
        
        try:
            # Crear el objeto PadronAFIP
            padron = PadronAFIP()
            padron.CUIT = company_cuit
            
            # Conectar al ambiente de testing o production
            # (si no tiene certificado, usar testing)
            try:
                padron.Conectar('testing')  # o 'production'
            except:
                # Si falla, intentar sin certificado
                pass
            
            # Consultar el CUIT
            padron.Consultar(cuit)
            
            # Extraer TODOS los datos
            datos = {
                # Datos principales
                'name': getattr(padron, 'denominacion', ''),
                'estado': getattr(padron, 'estado', ''),
                
                # Dirección
                'street': getattr(padron, 'direccion', ''),
                'city': getattr(padron, 'localidad', ''),
                'zip': getattr(patron, 'cod_postal', ''),
                'provincia': getattr(padron, 'provincia', ''),
                
                # Datos fiscales
                'imp_iva': getattr(padron, 'imp_iva', 'N'),
                'imp_ganancias': getattr(padron, 'imp_ganancias', 'NI'),
                
                # Monotributo
                'monotributo': getattr(padron, 'monotributo', 'N'),
            }
            
            # Procesar tipo de persona
            tipo_persona = getattr(padron, 'tipo_persona', '')
            if tipo_persona == 'FISISCA':
                datos['tipo_persona'] = 'Física'
            elif tipo_persona == 'JURIDICA':
                datos['tipo_persona'] = 'Jurídica'
            
            return datos
            
        except Exception as e:
            _logger.error(f'Error en consulta AFIP: {str(e)}')
            # Si no puede conectar, buscar en datos locales de AFIP
            return self._consultar_sin_certificado(cuit)
    
    def _consultar_sin_certificado(self, cuit):
        """
        Intenta consultar de otra forma o retorna error
        """
        # Intentar另一种 forma
        try:
            import requests
            
            # URL de AFIP (puede variar)
            url = f"https://wsfe.afip.gov.ar/WS_PADRONA/GetPersona?cuit={cuit}"
            
            # Headers
            headers = {
                'Content-Type': 'application/json',
            }
            
            # Aunque esto probablemente no funcione sin certificación
            # Es solo para mostrar la idea
            
        except:
            pass
        
        # Si nada funciona, retornar datos de prueba
        # pero告知ando al usuario que necesita certificado
        raise UserError(_(
            'No se pudo conectar a AFIP. '
            'Necesita configurar el certificado AFIP en la compañía.'
        ))
    
    def _buscar_provincia(self, nombre):
        """Busca provincia por nombre"""
        if not nombre:
            return False
        
        # Buscar en provincias argentinas
        state = self.env['res.country.state'].search([
            ('name', 'ilike', nombre),
            ('country_id.code', '=', 'AR'),
        ], limit=1)
        
        if state:
            return state.id
        
        # Buscar por código
        state = self.env['res.country.state'].search([
            ('code', '=', nombre[:2].upper()),
            ('country_id.code', '=', 'AR'),
        ], limit=1)
        
        if state:
            return state.id
        
        return False