# -*- coding: utf-8 -*-
{
    "name": "MercadoLibre Product Connector",
    "version": "19.0.1.0.0",
    "summary": "Publicación y gestión de productos en MercadoLibre",
    "category": "Sales",
    "author": "Softwork",
    "license": "LGPL-3",
    "depends": ["product", "stock", "softwork_ecommerce_conector_base", "sce_product_marketplace"],
    "data": [
        "security/ir.model.access.csv",
        "views/product_template_views.xml",
        "views/marketplace_publication_views.xml",
        "views/ml_category_search_wizard_views.xml",
        "views/ml_attribute_editor_wizard_views.xml",
        "views/ml_publish_config_wizard_views.xml",
        "views/ml_publish_assistant_wizard_views.xml",
        "views/ml_attribute_option_picker_wizard_views.xml",
    ],
    "installable": True,
    "application": False
}