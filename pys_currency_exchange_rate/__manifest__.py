{
    # Module Info
    'name': "Currency Exchange Rate",
    'version': '19.0.1.0.0',
    "category": "Tools",

    'summary': """
        Automatically update and manage daily currency exchange rates
    """,
    "description": """
        Automatically fetches and updates currency exchange rates on a daily basis
        using a scheduled cron job. Ensures accurate currency values across
        accounting, invoicing, and reporting in Odoo.
    """,
    'license': 'AGPL-3',

    # Author
    'author': 'Pysquad Informatics',
    'website': 'https://pysquad.com/odoo-erp',

    # Dependencies
    'depends': [
        "base",
        "web"
    ],

    # Data File
     'data': [
        'data/ir_cron.xml',
        'views/ir_configuration_view.xml'
    ],

    'assets': {
        'web.assets_backend': [
            'pys_currency_exchange_rate/static/src/js/**/*'
        ]
    },

    'images': [
        'static/description/banner_icon.png',
    ],

    # Technical Spec
    'installable': True,
    'application': False,
    'auto_install': False,

    # Other Info
    'price': 0.0,
    'currency': 'EUR',
}



