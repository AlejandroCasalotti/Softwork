# -*- coding: utf-8 -*-

{
    'name': 'Costo Neto del Producto',
    'version': '1.0',
    'category': 'Inventory',
    'summary': 'Calcula costo neto con reglas de descuento y recargo',
    'description': '''
        Módulo para calcular el precio neto de productos de proveedores
        aplicando descuentos, recargos y tarifas extras en cascada.
    ''',
    'author': 'Tu Nombre',
    'depends': ['product', 'stock'],
    'data': [
        'views/coste_net_rule_views.xml',
    ],
    'installable': True,
    'application': False,
}