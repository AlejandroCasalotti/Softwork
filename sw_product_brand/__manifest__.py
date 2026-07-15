# -*- coding: utf-8 -*-

{
    "name": "Softwork Product Brand",
    "summary": "Manage product brands and manufacturers.",
    "description": """
Softwork Product Brand

Adds brand management to products.

Main Features
-------------
* Product brands
* Manufacturer information
* Brand logo
* Multi-company
* Chatter support
* Odoo 19 compatible
* Ready for Softwork Pricing Suite
* Ready for Softwork Commerce Engine (SCE)
""",
    "version": "19.0.1.0.0",
    "category": "Inventory/Product",
    "author": "Softwork",
    "website": "https://swsistemas.com",
    "license": "LGPL-3",
    "depends": [
        "mail",
        "product",
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