# -*- coding: utf-8 -*-
{
    "name": "Softwork Product Brand",
    "summary": "Product brand management for Odoo 19.",
    "description": """
Softwork Product Brand

Adds a complete brand management system to products.

Features
========
* Product brands
* Brand logo
* Brand code
* Company support
* Manufacturer information
* Product integration
* Ready for Pricing Suite
* Ready for SCE
* Multi-company
* Odoo.sh compatible
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
        "stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/product_brand_views.xml",
        "views/product_template_views.xml",
        "views/menu_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}