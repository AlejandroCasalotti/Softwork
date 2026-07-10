# -*- coding: utf-8 -*-


{
    "name": "SCE Connector - Mercado Libre",
    "summary": "Official Mercado Libre connector for Softwork Commerce Engine.",
    "description": """Softwork Commerce Engine (SCE)Official Mercado Libre connector for Odoo 19 Enterprise.

Main features:
- OAuth 2.0 authentication
- Product publication
- Stock synchronization
- Price synchronization
- Order import
- Shipment synchronization
- Webhook support
- Multi-company
- Odoo.sh compatible
""",
    "version": "19.0.1.0.0",
    "category": "Sales/Sales",
    "author": "Softwork",
    "website": "https://swsistemas.com",
    "license": "LGPL-3",
    "depends": [
        "sce_base",
        "sale_management",
        "stock",
        "delivery",
        "mail",
        "product",
    ],
  "data": [
    # Security
    "security/sce_ml_security.xml",
    "security/ir.model.access.csv",
    # Master Data
    "data/ml_site_data.xml",
    # Views
    "views/menus.xml",
    "views/ml_site_views.xml",
    "views/ml_account_views.xml",
    # Scheduled Actions
    "data/ir_cron.xml",
],
    "demo": [],
    "assets": {},
    "application": False,
    "installable": True,
    "auto_install": False,
}