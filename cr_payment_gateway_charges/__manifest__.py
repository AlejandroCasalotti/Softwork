# -*- coding: utf-8 -*-
# Part of Odoo Module Developed by Candidroot Solutions Pvt. Ltd.
# See LICENSE file for full copyright and licensing details.

{
    'name': 'Payment Gateway-based Charges',
    'version': '19.0.0.0',
    'description': """
        Implementation of dynamic payment gateway-based charges in both the shopping cart and backend systems. 
        This feature calculates and applies additional fees (e.g., transaction fees, service charges) based on the 
        selected payment gateway during checkout. The charges are transparently displayed to customers in the cart 
        and accurately recorded in the backend for order processing and reporting.
    """,
    'category': 'Website',
    'author': 'Candidroot Solutions Pvt. Ltd.',
    'website': 'https://www.candidroot.com/',
    'depends': [
        'product', 'website_sale', 'sale_management', 'payment'
    ],
    'data': [
        'views/payment_provider.xml',
        'views/payment_form_template.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'cr_payment_gateway_charges/static/src/**/*',
        ],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
