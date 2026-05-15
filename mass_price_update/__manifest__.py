# -*- coding: utf-8 -*-

{
    'name': 'Mass Price Update',
    'version': '19.0.1.0.0',
    'category': 'Warehouse',
    'summary': """Actualizar precio unitario del proveedor por porcentaje""",
    'description': """Este módulo permite actualizar masivamente los precios del proveedor""",
    'author': 'SoftWork Arg.',
    'company': 'SoftWork Arg',
    'maintainer': 'SoftWork Arg',
    'website': 'https://www.swsistemas.com',
    'depends': ['purchase'],
    'data': [
        'security/mass_price_update_groups.xml',
        'security/ir.model.access.csv',
        'wizard/mass_price_update_views.xml'
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
