# -*- coding: utf-8 -*-
{
    "name": "Softwork Product Pricing Base",
    "summary": "Base framework for product pricing and cost management.",
    "description": """
Softwork Product Pricing Base

This module provides the core framework for the Softwork
Product Pricing Suite.

Features:
- Shared pricing services
- Currency conversion helpers
- Margin calculation engine
- Cost calculation engine
- Base mixins
- Company settings
- Multi-company support
- Multi-currency support
- Odoo.sh compatible
    """,
    "version": "19.0.1.0.0",
    "category": "Inventory/Product",
    "author": "Softwork",
    "website": "https://swsistemas.com",
    "license": "LGPL-3",
    "depends": [
        "base",
        "mail",
        "product",
        "purchase",
        "stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/pricing_data.xml",
        "views/res_company_views.xml",
    ],

    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",

    "installable": True,
    "application": False,
    "auto_install": False,
}