# -*- coding: utf-8 -*-

{
    'name': 'Aumentar Precio Proveedor',
    'version': '1.0',
    'category': 'Inventory',
    'summary': 'Permite aumentar precios de productos de proveedores en batch',
    'description': """
        Módulo que agrega una acción para aumentar precios en lote 
        en el modelo de información de proveedores de productos.
    """,
    'author': 'Tu Nombre',
    'website': 'https://www.tuwebsite.com',
    'license': 'LGPL-3',
    'depends': ['product'],
    'data': [
        'views/increase_price_wizard_menu.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}