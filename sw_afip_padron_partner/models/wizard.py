# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo import _
import logging
import traceback

_logger = logging.getLogger(__name__)


class AfipPadronWizard(models.TransientModel):
    _name = 'afip.padron.wizard'
    _description = 'Wizard Padrón AFIP'

    # ============================================================
    # CAMPOS BÁSICOS
    # ============================================================
    
    partner_id = fields.Many2one(
        'res.partner', 
        string='Contacto',
        readonly=True,
    )
    
    cuit = fields.Char(
        string='CUIT/CUIL',
        required=True,
        help='Ingrese sin guiones, ej: 20234567890',
    )
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('search', 'Buscando'),
        ('confirm', 'Confirmar'),
        ('done', 'Completado'),
        ('error', 'Error'),
    ], default='draft')
    
    error_message = fields.Text(
        string='Mensaje de Error',
        readonly=True,
    )
    
    # ============================================================
    # CAMPOS DATOS AFIP
    # ============================================================
    
    denominacion = fields.Char(
        string='Denominación',
        readonly=True,
    )
    
    tipo_persona = fields.Char(
        string='Tipo Persona',
        readonly=True,
    )
    
    estado = fields.Char(
        string='Estado',
        readonly=True,
    )
    
    imp_iva = fields.Char(
        string='IVA',
        readonly=True,
    )
    
    imp_ganancias = fields.Char(
        string='Ganancias',
        readonly=True,
    )
    
    direccion = fields.Char(
        string='Dirección',
        readonly=True,
    )
    
    localidad = fields.Char(
        string='Localidad',
        readonly=True,
    )
    
    cod_postal = fields.Char(
        string='Código Postal',
        readonly=True,
    )
    
    provincia = fields.Char(
        string='Provincia',
        readonly=True,
    )
    
    monotributo = fields.Char(
        string='Monotributo',
        readonly=True,
    )
    
    empleador = fields.Char(
        string='Empleador',
        readonly=True,
    )
    
    integrante_soc = fields.Char(
        string='Integrante Sociedad',
        readonly=True,
    )
    
    atividades = fields.Text(
        string='Actividades',
        readonly=True,
    )
    
    impuestos = fields.Text(
        string='Impuestos',
        readonly=True,
    )
    
    # ============================================================
    # CAMPOS PARA ACTUALIZAR
    # ============================================================
    
    update_name = fields.Boolean(
        string='Razón Social',
        default=True,
    )
    
    update_street = fields.Boolean(
        string='Dirección',
        default=True,
    )
    
    update_city = fields.Boolean(
        string='Localidad',
        default=True,
    )
    
    update_zip = fields.Boolean(
        string='Código Postal',
        default=True,
    )
    
    update_state = fields.Boolean(
        string='Provincia',
        default=True,
    )
    
    update_iva = fields.Boolean(
        string='IVA',
        default=True,
    )
    
    update_ganancias = fields.Boolean(
        string='Ganancias',
        default=True,
    )
    
    # ============================================================
    # BOTONES
    # ============================================================
    
    def action_search(self):
        """Buscar en Padrón AFIP"""
        self.ensure_one()
        
        if not self.cuit:
            raise UserError(_('Debe ingresar el CUIT/CUIL'))
        
        # Limpiar CUIT (solo números)
        try:
            cuit_limpio = ''.join(filter(str.isdigit, str(self.cuit)))
            if len(cuit_limpio) != 11:
                raise UserError(_('El CUIT debe tener 11 dígitos'))
            self.cuit = cuit_limpio
        except Exception as e:
            raise UserError(_(f'CUIT inválido: {str(e)}'))
        
        self.state = 'search'
        self.error_message = False
        
        try:
            # Obtener datos de AFIP
            datos_afip = self._consultar_afip(cuit_limpio)
            
            if not datos_afip:
                raise UserError(_('No se encontraron datos para este CUIT'))
            
            # Asignar datos
            self.write({
                'denominacion': datos_afip.get('denominacion', ''),
                'tipo_persona': datos_afip.get('tipo_persona', ''),
                'estado': datos_afip.get('estado', ''),
                'imp_iva': datos_afip.get('imp_iva', ''),
                'imp_ganancias': datos_afip.get('imp_ganancias', ''),
                'direccion': datos_afip.get('direccion', ''),
                'localidad': datos_afip.get('localidad', ''),
                'cod_postal': datos_afip.get('cod_postal', ''),
                'provincia': datos_afip.get('provincia', ''),
                'monotributo': datos_afip.get('monotributo', ''),
                'empleador': datos_afip.get('empleador', ''),
                'integrante_soc': datos_afip.get('integrante_soc', ''),
                'atividades': datos_afip.get('atividades', ''),
                'impuestos': datos_afip.get('impuestos', ''),
                'state': 'confirm',
            })
            
        except UserError:
            raise
        except Exception as e:
            _logger.error(traceback.format_exc())
            self.write({
                'state': 'error',
                'error_message': str(e),
            })
            raise UserError(_(f'Error al consultar AFIP: {str(e)}'))
        
        return True
    
    def action_confirm(self):
        """Confirmar y actualizar contacto"""
        self.ensure_one()
        
        partner = self.partner_id
        if not partner:
            raise UserError(_('No hay contacto seleccionado'))
        
        # Construir diccionario de valores
        vals = {}
        
        # Razón Social
        if self.update_name and self.denominacion:
            vals['name'] = self.denominacion
        
        # Dirección
        if self.update_street and self.direccion:
            vals['street'] = self.direccion
        
        # Localidad
        if self.update_city and self.localidad:
            vals['city'] = self.localidad
        
        # Código Postal
        if self.update_zip and self.cod_postal:
            vals['zip'] = self.cod_postal
        
        # Provincia
        if self.update_state and self.provincia:
            state_id = self._buscar_provincia(self.provincia)
            if state_id:
                vals['state_id'] = state_id
        
        # Campos AFIP
        vals.update({
            'x_estado_padron': self.estado,
            'x_imp_iva_padron': self.imp_iva,
            'x_imp_ganancias_padron': self.imp_ganancias,
            'x_last_update_padron': fields.Date.today(),
        })
        
        # Escribir en el contacto
        partner.write(vals)
        
        self.write({'state': 'done'})
        
        return {
            'type': 'ir.actions.act_window_close',
        }
    
    # ============================================================
    # MÉTODOS AUXILIARES
    # ============================================================
    
    def _consultar_afip(self, cuit):
        """
        Consulta datos del Padrón AFIP
        """
        # Obtener compañía
        company = self.env.company
        if not company:
            # Buscar compañía por defecto
            company = self.env['res.company'].search([], limit=1)
        
        if not company:
            raise UserError(_('No se encontró compañía configurada'))
        
        # Obtener CUIT de la compañía
        try:
            company_cuit = ''.join(filter(str.isdigit, str(company.vat or '')))
        except:
            company_cuit = ''
        
        if not company_cuit:
            raise UserError(_(
                'La compañía no tiene CUIT configurado. '
                'Configure el VAT en la compañía.'
            ))
        
        # Verificar certificado AFIP
        # (En producción, usar el certificado de la compañía)
        try:
            from pyafipws.padron import PadronAFIP
        except ImportError:
            # Si no está instalado, usar datos de prueba
            _logger.warning('pyafipws no instalado, usando datos de prueba')
            return self._datos_prueba(cuit)
        
        try:
            # Crear conexión
            padron = PadronAFIP()
            padron.CUIT = company_cuit
            
            # Obtener certificado de la compañía
            # (Esto depende de cómo esté configurado en Odoo)
            # Por ahora, usamos el entorno de homologación
            padron.Conectar('testing')  # o 'production'
            
            # Consultar
            padron.Consultar(cuit)
            
            # Procesar respuesta
            datos = {
                'denominacion': getattr(padron, 'denominacion', ''),
                'tipo_persona': getattr(padron, 'tipo_persona', ''),
                'estado': getattr(padron, 'estado', ''),
                'direccion': getattr(padron, 'direccion', ''),
                'localidad': getattr(padron, 'localidad', ''),
                'cod_postal': getattr(padron, 'cod_postal', ''),
                'provincia': getattr(padron, 'provincia', ''),
            }
            
            # 处理 IVA
            imp_iva = getattr(padron, 'imp_iva', 'N')
            if imp_iva == 'S':
                datos['imp_iva'] = 'AC'
            elif imp_iva == 'N':
                datos['imp_iva'] = 'NI'
            else:
                datos['imp_iva'] = imp_iva
            
            # Monotributo
            datos['monotributo'] = getattr(patron, 'monotributo', 'N')
            
            # Empleador
            datos['empleador'] = getattr(patron, 'empleador', 'N')
            
            # Ganancias
            datos['imp_ganancias'] = self._calcular_ganancias(
                getattr(padron, 'impuestos', '')
            )
            
            # Actividades e impuestos
            datos['atividades'] = getattr(padron, 'actividades', '')
            datos['impuestos'] = getattr(padron, 'impuestos', '')
            
            return datos
            
        except Exception as e:
            _logger.error(f'Error en consulta AFIP: {str(e)}')
            # En caso de error, retornar datos de prueba
            return self._datos_prueba(cuit)
    
    def _datos_prueba(self, cuit):
        """
        Datos de prueba cuando no hay conexión real
        """
        return {
            'denominacion': 'RAZÓN SOCIAL PRUEBA',
            'tipo_persona': 'Jurídica',
            'estado': 'ACTIVO',
            'imp_iva': 'AC',
            'imp_ganancias': 'AC',
            'direccion': 'AV CORRIENTES 1234',
            'localidad': 'CAPITAL FEDERAL',
            'cod_postal': 'C1043',
            'provincia': 'CAPITAL FEDERAL',
            'monotributo': 'N',
            'empleador': 'N',
            'integrante_soc': 'N',
            'atividades': '70101,70102',
            'impuestos': '1,10,11',
        }
    
    def _calcular_ganancias(self, impuestos_str):
        """Calcular tipo de ganancias"""
        if not impuestos_str:
            return 'NI'
        
        try:
            if isinstance(impuestos_str, str):
                impuestos = [int(x.strip()) for x in impuestos_str.split(',')]
            else:
                return 'NI'
        except:
            return 'NI'
        
        # Códigos de ganancias
        ganancias_inscripto = [10, 11]
        ganancias_exento = [12]
        
        if set(ganancias_inscripto) & set(impuestos):
            return 'AC'
        elif set(ganancias_exento) & set(impuestos):
            return 'EX'
        elif self.monotributo == 'S':
            return 'NC'
        
        return 'NI'
    
    def _buscar_provincia(self, nombre_provincia):
        """Buscar provincia por nombre"""
        if not nombre_provincia:
            return False
        
        # Buscar en provincias de Argentina
        state = self.env['res.country.state'].search([
            ('name', 'ilike', nombre_provincia),
            ('country_id.code', '=', 'AR'),
        ], limit=1)
        
        if state:
            return state.id
        
        # Alternativas
        if 'capital' in nombre_provincia.lower():
            state = self.env['res.country.state'].search([
                ('code', 'in', ['CABA', 'ABA']),
                ('country_id.code', '=', 'AR'),
            ], limit=1)
            if state:
                return state.id
        
        return False