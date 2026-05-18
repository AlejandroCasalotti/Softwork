# -*- coding: utf-8 -*-

{
    'name': 'Aumentar Precio Proveedor',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Permite aumentar precios de proveedores en lote',
    'description': 'Wizard para aumentar precios de productos de proveedores.',
    'author': 'Tu Nombre',
    'depends': ['product'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/increase_price_wizard.xml',
    ],
    'installable': True,
    'application': False,
}