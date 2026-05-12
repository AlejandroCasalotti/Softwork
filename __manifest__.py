# -*- coding: utf-8 -*-

{
    'name': 'Coste Proveedor con Reglas',
    'version': '19.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Reglas dinámicas de costo para proveedores',
    'depends': ['product', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'views/regla_costo_views.xml',
        'views/product_supplierinfo_views.xml',
        'views/product_template_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}