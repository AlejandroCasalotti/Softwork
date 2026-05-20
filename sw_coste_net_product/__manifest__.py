# -*- coding: utf-8 -*-

{
    'name': 'Aumentar Precio Proveedor',
    'version': '19.0.1.0.0',
    'category': 'Purchase',
    'summary': 'Calcula costo neto con reglas de descuento y recargo',
    'description': 'Módulo para calcular el precio neto de productos de proveedores',
    'author': 'SW Sistemas',
    'company': 'SW Sistemas',
    'maintainer': 'SoftWork Arg',
    'website': 'https://www.swsistemas.com',
    'depends': ['product', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/assign_rule_wizard_views.xml',
        'views/coste_net_rule_views.xml',
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}