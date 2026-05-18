# -*- coding: utf-8 -*-

{
    'name': 'Aumentar Precio Proveedor',
    'version': '1.0',
    'category': 'Inventory',
    'summary': 'Permite aumentar precios de proveedores en lote',
    'description': 'Wizard para aumentar precios de productos de proveedores.',
    'author': 'Tu Nombre',
    'depends': ['product'],
    'data': [
        'wizard/increase_price_wizard.xml',
    ],
    'installable': True,
    'application': False,
}