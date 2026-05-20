# -*- coding: utf-8 -*-

{
    'name': 'Costo Neto del Producto',
    'version': '1.0',
    'category': 'Purchase',
    'summary': 'Calcula costo neto con reglas de descuento y recargo',
    'description': '''
        Módulo para calcular el precio neto de productos de proveedores
        aplicando descuento, recargo y tarifas en cascada.
    ''',
    'author': 'SW sistemas',
    'depends': ['purchase'],
    'data': [
        'security/ir.model.access.csv',
        'views/coste_net_rule_views.xml',
    ],
    'installable': True,
    'application': False,
}