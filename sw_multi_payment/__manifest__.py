# -*- coding: utf-8 -*-
{
    'name': 'Pagos Múltiples',
    'version': '19.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Crear pagos con distintos métodos',
    'description': 'Módulo para multiples métodos de pago juntos',
    'author': 'SW Sistemas',
    'company': 'SW Sistemas',
    'website': 'https://www.swsistemas.com',
    'depends': ['account'],
    'data': [
        'views/payment_view.xml',
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}