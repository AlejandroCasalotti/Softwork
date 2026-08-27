# -*- coding: utf-8 -*-
{
    "name": "SCE Connect",
    "summary": "Middleware multi-tenant para conectar Odoo externo con marketplaces",
    "version": "19.0.1.0.0",
    "category": "Connectivity",
    "author": "Softwork",
    "website": "https://swsistemas.com",
    "license": "LGPL-3",
    "depends": ["softwork_ecommerce_conector_base"],
    "external_dependencies": {"python": ["cryptography", "requests"]},
    "data": [
        "security/sce_connect_security.xml",
        "security/ir.model.access.csv",
        "views/sce_tenant_views.xml",
        "views/sce_secret_views.xml",
        "views/sce_secret_set_wizard_views.xml",
        "views/sce_external_connection_views.xml",
    ],
    "demo": [],
    "installable": True,
    "application": False,
    "auto_install": False,
}
