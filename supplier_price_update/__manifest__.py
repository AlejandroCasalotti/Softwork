# -*- coding: utf-8 -*-

{
    'name': 'Aumentar Precio Proveedor',
    'version': '19.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Permite aumentar precios de proveedores en lote',
    'description': 'Wizard para aumentar precios de productos de proveedores.',
    'author': 'SW Sistemas',
    'company': 'SW Sistemas',
    'maintainer': 'SoftWork Arg',
    'website': 'https://www.swsistemas.com',
    'depends': ['product'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/increase_price_wizard.xml',
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}