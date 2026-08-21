# -*- coding: utf-8 -*-
{
    "name": "MercadoLibre Product Connector",
    "version": "19.0.1.0.0",
    "summary": "Publicación y gestión de productos en MercadoLibre",
    "category": "Sales",
    "author": "Softwork",
    "license": "LGPL-3",
    "depends": ["product", "stock", "softwork_ecommerce_conector_base", "sce_product_marketplace", "sce_connector_ml"],
    "data": [
        "data/migration_actions.xml",
        "views/product_template_views.xml",
    ],
    "installable": True,
    "application": False,
    "post_init_hook": "post_init_migrate_legacy_marketplace",
}