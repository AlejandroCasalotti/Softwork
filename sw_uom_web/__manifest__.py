# -*- coding: utf-8 -*-
{
    "name": "SW UoM Web",
    "summary": "Venta web por UoM específica con cantidad mínima configurable",
    "version": "19.0.1.0.0",
    "category": "Website/eCommerce",
    "author": "SoftWork",
    "license": "LGPL-3",
    "depends": [
        "website_sale",
        "uom",
        "product",
        "sale",
    ],
    "data": [
        "views/product_template_views.xml",
        "views/website_templates.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "sw_uom_web/static/src/js/sw_uom_web.js",
        ],
    },
    "installable": True,
    "application": False,
}