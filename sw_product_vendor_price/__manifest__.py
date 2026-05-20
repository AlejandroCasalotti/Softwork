# -*- coding: utf-8 -*-

{
    'name': 'Gestión de Precios de Proveedor',
    'version': '19.0.1.0.0',
    'category': 'Ventas',
    'summary': 'Sincroniza standard_price con precio de proveedor y márgenes',
    'description': """
        Este módulo permite:
        1. Copiar el precio del proveedor al standard_price del producto (ambos editables)
        2. Calcular el list_price basándose en el margen de venta del proveedor
    """,
    'author': 'SW Sistemas',
    'company': 'SW Sistemas',
    'maintainer': 'SoftWork Arg',
    'website': 'https://www.swsistemas.com',
    'depends': ['product', 'purchase'],
    'data': [
        'views/views.xml',
    ],
    'demo': [],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}