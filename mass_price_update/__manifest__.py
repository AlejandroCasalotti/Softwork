# -*- coding: utf-8 -*-

{
    'name': 'Mass Supplier Price Update',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Purchase',
    'summary': """Actualización masiva del precio unitario del proveedor""",
    'description': """Actualización masiva del precio unitario del proveedor""",
    'author': 'Softwork Arg.',
    'company': 'Softwork Arg.',
    'maintainer': 'Softwork Arg.',
    'website': 'https://www.swsistemas.com',
    'depends': ['product', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_views.xml',
        'views/mass_supplier_price_update_views.xml',
        'data/mass_supplier_price_update_data.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'mass_price_update/static/src/*/',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}