{
    'name': 'Cálculos Automáticos Ventas y Web',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Calculo de materiales en orden de venta',
    'description': 'Módulo para calcular productos por m2 o m3',
    'author': 'SW Sistemas',
    'company': 'SW Sistemas',
    'website': 'https://www.swsistemas.com',
    'depends': ['sale', 'product', 'uom', 'website_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/calculation_view.xml',
        'views/product_template_views.xml',
        'views/website_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'sw_automatic_product_calculations/static/src/js/website_calculation.js',
        ],
    },
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}