{
    'name': 'AFIP Padrón Partner',
    'version': '19.0.1.0.0',
    'category': 'Localization/Argentina',
    'summary': 'Consulta Padrón AFIP para contactos',
    'description': '''
    - Consulta datos de AFIP por CUIT/CUIL
    - Actualiza datos del contacto automáticamente
    
    Requiere:
    - pip install pyafipws
    - Certificado AFIP configurado en la compañía
    ''',
    'author': 'SW Sistemas',
    'depends': ['base'],
    'data': [
        'views/res_partner_view.xml',
        'views/wizard_view.xml',
        'security/ir.model_access.csv',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}