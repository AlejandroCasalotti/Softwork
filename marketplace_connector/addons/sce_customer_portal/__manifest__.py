# -*- coding: utf-8 -*-
{
    "name": "SCE Customer Portal",
    "version": "19.0.1.1.0",
    "summary": "Portal de suscripción y uso de SCE",
    "category": "Sales",
    "author": "Softwork",
    "website": "https://swsistemas.com",
    "license": "LGPL-3",
    "depends": ["portal", "sce_connector_ml"],
    "data": ["views/portal_templates.xml", "views/portal_home_templates.xml", "views/portal_rules_templates.xml"],
    "assets": {
        "web.assets_frontend": [
            "sce_customer_portal/static/src/js/remote_options.js",
        ],
    },
    "installable": True,
    "application": False,
}
