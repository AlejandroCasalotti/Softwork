# -*- coding: utf-8 -*-

{
    "name": "Softwork Commerce Engine (SCE) Base",

    "summary": "Core framework for marketplace integrations",

    "description": """
Softwork Commerce Engine (SCE)

Enterprise marketplace integration framework.

Provides the complete infrastructure used by all
Softwork marketplace connectors.

Main Features
-------------

* Connector framework
* Provider abstraction
* Plugin architecture
* OAuth 2.0 support
* Queue engine
* Job engine
* Webhook engine
* Event dispatcher
* Logging framework
* Multi-company
* Background processing
* Odoo.sh compatible
""",

    "version": "19.0.1.0.0",

    "category": "Sales/Sales",

    "license": "LGPL-3",

    "author": "Softwork",

    "website": "https://swsistemas.com",

    "depends": [

        "base",
        "mail",
        "web",

    ],

    "data": [

    # Security
    "security/security.xml",
    "security/ir.model.access.csv",

    # Data
    "data/ir_sequence.xml",
    "data/ir_cron.xml",
    "data/mail_template.xml",

    # Dashboard
    "views/dashboard_views.xml",

    # Models
    "views/sce_plugin_views.xml",
    "views/sce_connector_views.xml",
    "views/sce_account_views.xml",
    "views/sce_job_views.xml",
    "views/sce_queue_views.xml",
    "views/sce_webhook_views.xml",
    "views/sce_log_views.xml",

    # Settings
    "views/settings_views.xml",

    # Menus
    "views/menu.xml",

    # Wizards

    # Reports
    # "report/report.xml",
    # "report/job_report.xml",
],

    "application": True,

    "installable": True,

    "auto_install": False,

}