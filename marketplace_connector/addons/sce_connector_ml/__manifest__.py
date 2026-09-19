# -*- coding: utf-8 -*-
{
    "name": "SCE Connector MercadoLibre",
    "version": "19.0.1.0.0",
    "summary": "Conector MercadoLibre para SCE",
    "category": "Sales",
    "author": "Softwork",
    "website": "https://swsistemas.com",
    "license": "LGPL-3",
    "depends": [
        "softwork_ecommerce_conector_base",
        "sce_product_marketplace",
    ],
    "pre_init_hook": "pre_init_deduplicate_ml_question_channels",
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron.xml",
        "views/ml_category_search_wizard_views.xml",
        "views/ml_attribute_option_picker_wizard_views.xml",
        "views/marketplace_publication_views.xml",
        "views/ml_attribute_editor_wizard_views.xml",
        "views/ml_publish_config_wizard_views.xml",
        "views/ml_publish_assistant_wizard_views.xml",
    ],
    "installable": True,
    "application": False,
}