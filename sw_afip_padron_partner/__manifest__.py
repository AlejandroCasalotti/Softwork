# -*- coding: utf-8 -*-
{
    'name': 'AFIP Padrón Partner',
    'version': '19.0.1.0.0',
    'category': 'Localization/Argentina',
    'depends': ['base'],
    'data': [
        'views/res_partner_view.xml',
        'views/wizard_view.xml',
        'security/ir.model_access.csv',
    ],
    'installable': True,
    'application': False,
}