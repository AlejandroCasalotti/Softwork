# -*- coding: utf-8 -*-
{
    'name': 'AFIP Padrón Partner',
    'version': '19.0.1.0.0',
    'category': 'Localization/Argentina',
    'summary': 'Consulta y actualiza Padrón AFIP automáticamente',
    'description': '''
    - Consulta Padrón AFIP por CUIT
    - Auto-completa datos del contacto
    - Muestra estado fiscal
    
    Requiere:
    - pip install pyafipws cryptography
    - Certificado AFIP configurado
    ''',
    'author': 'SW Sistemas',
    'depends': ['base'],
    'data': [
        'views/res_partner_view.xml',
        'views/res_company_view.xml',
    ],
    'installable': True,
    'application': False,
}