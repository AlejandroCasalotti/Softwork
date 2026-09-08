# -*- coding: utf-8 -*-
import base64
import importlib.util
import logging

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ResCompany(models.Model):
    _inherit = "res.company"

    # Campos para certificado AFIP
    afip_crt = fields.Binary(
        string='Certificado AFIP (.crt)',
        help='Certificado de firma digital de AFIP',
    )
    
    afip_key = fields.Binary(
        string='Clave Privada AFIP (.key)',
        help='Clave privada del certificado',
    )
    
    afip_environment = fields.Selection([
        ('production', 'Producción'),
        ('testing', 'Homologación'),
    ],
        string='Ambiente AFIP',
        default='production',
    )

    def _normalize_cuit(self, cuit_value):
        normalized = ''.join(filter(str.isdigit, str(cuit_value or '')))
        return normalized if len(normalized) == 11 else ''

    def _is_pyafipws_available(self):
        return importlib.util.find_spec('pyafipws.padron') is not None

    def _decode_pem_binary(self, binary_value, label):
        try:
            decoded = base64.b64decode(binary_value).decode('utf-8')
        except Exception as exc:
            _logger.exception("Error decodificando %s AFIP", label)
            raise UserError(
                _('No se pudo leer %s AFIP. Vuelva a cargar el archivo en Configuración de compañía.') % label
            ) from exc
        return decoded

    def _get_afip_prerequisite_errors(self):
        self.ensure_one()
        errors = []
        if not self._is_pyafipws_available():
            errors.append(_('Falta la dependencia Python "pyafipws" en el servidor de Odoo.'))
        if not self._normalize_cuit(self.vat):
            errors.append(_('La compañía debe tener CUIT válido (11 dígitos) en "Información fiscal".'))
        if not self.afip_crt:
            errors.append(_('Falta cargar el certificado AFIP (.crt).'))
        if not self.afip_key:
            errors.append(_('Falta cargar la clave privada AFIP (.key).'))
        return errors

    def _get_afip_padron_client(self):
        self.ensure_one()
        errors = self._get_afip_prerequisite_errors()
        if errors:
            raise UserError(_('Configuración AFIP incompleta:\n- %s') % '\n- '.join(errors))

        try:
            from pyafipws.padron import PadronAFIP
        except ImportError as exc:
            raise UserError(_('No se pudo importar pyafipws en el entorno actual de Odoo.')) from exc

        padron = PadronAFIP()
        padron.CUIT = self._normalize_cuit(self.vat)
        padron.SetCertificate(self._decode_pem_binary(self.afip_crt, 'el certificado'))
        padron.SetPrivateKey(self._decode_pem_binary(self.afip_key, 'la clave privada'))
        return padron

    def action_test_afip_connection(self):
        self.ensure_one()
        padron = self._get_afip_padron_client()
        try:
            padron.Conectar(self.afip_environment or 'production')
        except Exception as exc:
            raise UserError(
                _('No se pudo conectar con AFIP (%s). Revise certificados, red y ambiente configurado.') %
                (self.afip_environment or 'production')
            ) from exc

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'sticky': False,
                'title': _('AFIP'),
                'message': _('Conexión exitosa al ambiente %s.') % (
                    'Producción' if (self.afip_environment or 'production') == 'production' else 'Homologación'
                ),
            },
        }