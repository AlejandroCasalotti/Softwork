# -*- coding: utf-8 -*-

{
    "name": "Softwork Product Cost Management",
    "summary": "Advanced product cost rules and margin management",
    "description": """
Softwork Product Cost Management

Module for advanced product cost management.

Features:
- Product cost rules
- Cost calculation framework
- Margin management
- Suggested sales price calculation
- Product cost history preparation
- Multi-company compatibility
- Odoo.sh compatible

Designed as a foundation for future integration
with Softwork Commerce Engine (SCE).
""",
    "author": "Softwork",
    "website": "https://swsistemas.com",
    "category": "Sales/Sales",
    "version": "19.0.1.0.0",
    "license": "LGPL-3",
    "depends": [
        "base",
        "product",
        "purchase",
        "sale_management",
        "sw_product_brand",
        "mail",
    ],

    "data": [
        "security/ir.model.access.csv",

        "views/cost_rule_views.xml",
        "views/product_template_views.xml",
        "views/menu_views.xml",

        "data/cost_rule_data.xml",
    ],

    "assets": {
        "web.assets_backend": [
        ],
    },

    "application": True,
    "installable": True,
    "auto_install": False,
}