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
        "security/ir.model.access.csv",
        "data/payment_multi_sequence.xml",
        "views/payment_multi_views.xml",
        "views/account_payment_views.xml",
        "report/payment_multi_receipt_report.xml",
        "report/payment_multi_receipt_templates.xml",
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
