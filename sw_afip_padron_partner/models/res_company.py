# -*- coding: utf-8 -*-
from odoo import models, fields

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