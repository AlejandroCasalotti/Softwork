# -*- coding: utf-8 -*-
{
    "name": "Softwork Libre",
    "version": "19.0.1.0.0",
    "summary": "Sincronización base Odoo <-> MercadoLibre",
    "description": """
Módulo base para sincronización con MercadoLibre:
- Configuración OAuth y tokens
- Sincronización de productos (precio/stock)
- Importación de órdenes
- Tareas automáticas (cron)
    """,
    "category": "Sales",
    "author": "Softwork",
    "website": "https://swsistemas.com",
    "license": "LGPL-3",
    "depends": [
        "base",
        "product",
        "sale_management",
        "stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron.xml",
        "views/ml_account_views.xml",
        "views/product_views.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
    "application": True,
}