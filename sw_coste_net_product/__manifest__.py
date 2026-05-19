# -*- coding: utf-8 -*-

{
    'name': 'Costo Neto del Producto',
    'version': '19.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Calcula costo neto con reglas de descuento y recargo',
    'description': '''
        Módulo para calcular el precio neto de productos de proveedores
        aplicando descuentos, recargos y tarifas extras en cascada.
    ''',
    'author': 'SW Sistemas',
    'depends': ['product', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/assign_rule_wizard_views.xml',
        'views/coste_net_rule_views.xml',
    ],
    'installable': True,
    'application': False,
}