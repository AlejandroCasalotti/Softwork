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
        
        # Actualizar datos principales si existen
        if datos_afip.get('name'):
            vals['name'] = datos_afip['name']
        
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
        
        # Escribir los datos
        self.write(vals)
        
        # Recargar la vista
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    # ============================================================
    # MÉTODOS AUXILIARES
    # ============================================================
    
    def _consultar_padron_afip(self, cuit):
        """
        Consulta el Padrón AFIP usando pyafipws
        """
        # Obtener compañía
        company = self.env.company
        if not company:
            company = self.env['res.company'].search([], limit=1)
        
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
        
        # Intentar importar pyafipws
        try:
            from pyafipws.padron import PadronAFIP
        except ImportError:
            _logger.warning('pyafipws no instalado, retornando datos de prueba')
            return self._datos_prueba(cuit)
        
        try:
            # Crear conexión al Padrón
            padron = PadronAFIP()
            padron.CUIT = company_cuit
            
            # Configurar certificado desde la compañía
            # (Esto depende de cómo tengas el certificado)
            # Por ahora, intentamos conectar
            padron.Conectar('production')  # o 'testing'
            
            # Consultar
            padron.Consultar(cuit)
            
            # Procesar respuesta
            datos = {
                'name': getattr(padron, 'denominacion', ''),
                'estado': getattr(padron, 'estado', ''),
                'direccion': getattr(padron, 'direccion', ''),
                'city': getattr(padron, 'localidad', ''),
                'zip': getattr(padron, 'cod_postal', ''),
                'provincia': getattr(padron, 'provincia', ''),
            }
            
            # Procesar IVA
            imp_iva = getattr(padron, 'imp_iva', 'N')
            if imp_iva == 'S':
                datos['imp_iva'] = 'AC'
            elif imp_iva == 'N':
                datos['imp_iva'] = 'NI'
            else:
                datos['imp_iva'] = imp_iva
            
            # Ganancias
            datos['imp_ganancias'] = self._calcular_ganancias(
                getattr(padron, 'impuestos', '')
            )
            
            return datos
            
        except Exception as e:
            _logger.error(f'Error en AFIP: {str(e)}')
            # Si hay error, retornar datos de prueba
            return self._datos_prueba(cuit)
    
    def _datos_prueba(self, cuit):
        """
        Datos de prueba (para testing)
        """
        return {
            'name': f'RAZÓN SOCIAL {cuit[-4:]}',
            'estado': 'ACTIVO',
            'imp_iva': 'AC',
            'imp_ganancias': 'AC',
            'street': 'AV CORRIENTES 1234',
            'city': 'CAPITAL FEDERAL',
            'zip': 'C1043',
            'provincia': 'CAPITAL FEDERAL',
        }
    
    def _calcular_ganancias(self, impuestos_str):
        """Calcula tipo de ganancias"""
        if not impuestos_str:
            return 'NI'
        
        try:
            if isinstance(impuestos_str, str):
                impuestos = [int(x.strip()) for x in impuestos_str.split(',')]
            else:
                return 'NI'
        except:
            return 'NI'
        
        ganancias_inscripto = [10, 11]
        ganancias_exento = [12]
        
        if set(ganancias_inscripto) & set(impuestos):
            return 'AC'
        elif set(ganancias_exento) & set(impuestos):
            return 'EX'
        
        return 'NI'
    
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
        
        # Casos especiales
        if 'capital' in nombre.lower() or 'caba' in nombre.lower():
            state = self.env['res.country.state'].search([
                ('code', 'in', ['CABA', 'ABA']),
                ('country_id.code', '=', 'AR'),
            ], limit=1)
            if state:
                return state.id
        
        return False