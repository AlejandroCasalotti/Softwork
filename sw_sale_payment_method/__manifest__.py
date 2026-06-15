# -*- coding: utf-8 -*-
{
    'name': 'Pagos Múltiples',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': "Método de pago con recargo",
    'description': "Permite seleccionar un método de pago que incrementa el precio unitario en un porcentaje (también recalcula líneas existentes).",
    'author': 'SW Sistemas',
    'company': 'SW Sistemas',
    'website': 'https://www.swsistemas.com',
    'depends': ['sale_management'],
    'data': [
        "security/ir.model.access.csv",
        "data/sale_payment_method_sequence.xml",
        "views/payment_method_views.xml",
        "views/sale_order_views.xml",
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}