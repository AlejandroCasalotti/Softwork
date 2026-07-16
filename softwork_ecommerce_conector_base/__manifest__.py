# -*- coding: utf-8 -*-
{
    "name": "Softwork Ecommerce Conector Base",
    "summary": "Framework base enterprise para integraciones ecommerce multicanal",
    "description": """
Softwork Ecommerce Conector Base
================================
Núcleo del framework para sincronización entre Odoo y múltiples ecommerce/marketplaces.

Incluye:
- Gestión de conectores y cuentas
- Jobs de sincronización y eventos
- Logging y métricas base
- Suscripciones, planes y uso
- Multiempresa, seguridad y base para extensibilidad por providers
    """,
    "version": "19.0.1.0.0",
    "category": "Sales/Sales",
    "author": "Softwork",
    "website": "https://swsistemas.com",
    "license": "LGPL-3",
    "depends": [
        "base",
        "mail",
        "web",
        "product",
        "sale_management",
        "stock",
        "account",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron.xml",
        "views/sce_connector_views.xml",
        "views/sce_account_views.xml",
        "views/sce_job_views.xml",
        "views/sce_log_views.xml",
        "views/sce_subscription_views.xml",
        "views/sce_integration_status_wizard_views.xml",
        "views/menu_views.xml",
    ],
    "demo": [],
    "assets": {
        "web.assets_backend": [],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
}