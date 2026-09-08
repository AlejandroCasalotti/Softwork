# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError
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
    x_afip_last_result = fields.Char(string='Resultado última consulta AFIP', readonly=True)
    x_afip_can_update = fields.Boolean(
        string='Puede actualizar AFIP',
        compute='_compute_afip_update_status',
    )
    x_afip_update_block_reason = fields.Char(
        string='Motivo de bloqueo AFIP',
        compute='_compute_afip_update_status',
    )

    @api.depends('x_afip_cuit', 'company_id', 'company_id.vat', 'company_id.afip_crt', 'company_id.afip_key')
    def _compute_afip_update_status(self):
        for partner in self:
            reason = partner._get_afip_update_block_reason()
            partner.x_afip_can_update = not reason
            partner.x_afip_update_block_reason = reason or False

    def _get_afip_company(self):
        self.ensure_one()
        return self.company_id or self.env.company or self.env['res.company'].search([], limit=1)

    def _normalize_cuit(self, value):
        normalized = ''.join(filter(str.isdigit, str(value or '')))
        return normalized if len(normalized) == 11 else ''

    def _get_afip_update_block_reason(self):
        self.ensure_one()
        if not self.x_afip_cuit:
            return _('Debe ingresar el CUIT para consultar AFIP.')
        if not self._normalize_cuit(self.x_afip_cuit):
            return _('El CUIT debe tener 11 dígitos numéricos.')

        company = self._get_afip_company()
        if not company:
            return _('No hay una compañía disponible para firmar la consulta AFIP.')

        errors = company._get_afip_prerequisite_errors()
        if errors:
            return _('Configuración AFIP incompleta en compañía:\n- %s') % '\n- '.join(errors)
        return False

    # BOTÓN PRINCIPAL
    def action_update_from_padron_afip(self):
        """Consulta y actualiza desde Padrón AFIP"""
        self.ensure_one()
        block_reason = self._get_afip_update_block_reason()
        if block_reason:
            raise UserError(block_reason)

        cuit = self._normalize_cuit(self.x_afip_cuit)
        try:
            datos_afip = self._consultar_ws_afip(cuit)
        except UserError as exc:
            self.write({'x_afip_last_result': str(exc)})
            raise
        except Exception as exc:
            self.write({'x_afip_last_result': str(exc)})
            raise UserError(_('No se pudo completar la consulta AFIP.')) from exc

        if not datos_afip:
            raise UserError(_('No se recibieron datos para el CUIT consultado.'))

        pais_argentina = self.env.ref('base.ar', raise_if_not_found=False)
        state_id = self._buscar_provincia(datos_afip.get('provincia'))

        vals = {
            # Para mejor UX: no sobreescribir datos manuales ya cargados
            'name': self.name or datos_afip.get('name', ''),
            'street': self.street or datos_afip.get('street', ''),
            'city': self.city or datos_afip.get('city', ''),
            'zip': self.zip or datos_afip.get('zip', ''),
            'state_id': self.state_id.id or state_id,
            'country_id': self.country_id.id or (pais_argentina.id if pais_argentina else False),
            'x_estado_padron': datos_afip.get('estado', ''),
            'x_imp_iva_padron': datos_afip.get('imp_iva', ''),
            'x_imp_ganancias_padron': datos_afip.get('imp_ganancias', ''),
            'x_last_update_padron': fields.Date.today(),
            'x_afip_last_result': _('Consulta AFIP exitosa'),
        }

        self.write(vals)
        return {'type': 'ir.actions.client', 'tag': 'reload'}
    
    # WEB SERVICE OFICIAL AFIP
    def _consultar_ws_afip(self, cuit):
        """Consulta usando Web Service oficial de AFIP"""
        company = self._get_afip_company()
        if not company:
            raise UserError(_('No hay compañía configurada'))

        try:
            padron = company._get_afip_padron_client()
            padron.Conectar(company.afip_environment or 'production')
            padron.Consultar(cuit)

            datos = {
                'name': getattr(padron, 'denominacion', ''),
                'estado': getattr(padron, 'estado', ''),
                'street': getattr(padron, 'direccion', ''),
                'city': getattr(padron, 'localidad', ''),
                'zip': getattr(padron, 'cod_postal', ''),
                'provincia': getattr(padron, 'provincia', ''),
            }
            imp_iva = getattr(padron, 'imp_iva', 'N')
            if imp_iva == 'S':
                datos['imp_iva'] = 'Responsable Inscripto'
            elif imp_iva == 'N':
                datos['imp_iva'] = 'No Inscripto'
            elif imp_iva == 'EX':
                datos['imp_iva'] = 'Exento'
            else:
                datos['imp_iva'] = imp_iva
            imp_gan = getattr(padron, 'imp_ganancias', 'NI')
            if imp_gan == 'AC':
                datos['imp_ganancias'] = 'Activo'
            elif imp_gan == 'EX':
                datos['imp_ganancias'] = 'Exento'
            else:
                datos['imp_ganancias'] = 'No Inscripto'
            return datos

        except Exception as e:
            _logger.exception('Error WS AFIP para CUIT %s', cuit)
            raise UserError(
                _('Error al consultar AFIP. Revise la configuración de compañía o intente nuevamente.\nDetalle: %s') %
                str(e)
            )
    
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