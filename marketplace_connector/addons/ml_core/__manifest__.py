# -*- coding: utf-8 -*-

{
    "name": "MercadoLibre Core Connector",
    "version": "19.0.1.0.0",
    "summary": "Core de autenticación, API y logs para MercadoLibre",
    "category": "Sales",
    "author": "Softwork",
    "license": "LGPL-3",
    "depends": ["base", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron.xml",
        "views/ml_account_views.xml",
        "views/ml_log_views.xml",
        "views/menu_views.xml"
    ],
    "installable": True,
    "application": False
}
