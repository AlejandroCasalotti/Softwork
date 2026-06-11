# -*- coding: utf-8 -*-

{
    'name': 'Cálculos Automáticos',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Calculo de materiales en orden de venta',
    'description': 'Módulo para calcular productos por m2 o m3',
    'author': 'SW Sistemas',
    'company': 'SW Sistemas',
    'website': 'https://www.swsistemas.com',
    'depends': ['sale', 'product', 'uom'],
    'data': [
        'security/ir.model.access.csv',
        'views/calculation_view.xml',
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}