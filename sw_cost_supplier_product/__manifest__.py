# -*- coding: utf-8 -*-
{
    'name': 'Costo Proveedor y Margen',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Costo automático desde proveedor y margen de venta',
    'description': '''
        Extiende el módulo de reglas de costo:
        - Costo proveedor: toma el net_price del primer proveedor
        - Margen de venta: calcula list_price automáticamente
    ''',
    'author': 'SW Sistemas',
    'company': 'SW Sistemas',
    'maintainer': 'SoftWork Arg',
    'website': 'https://www.swsistemas.com',
    'depends': ['product'],
    'data': [],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}