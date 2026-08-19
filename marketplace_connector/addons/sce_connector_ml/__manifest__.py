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
    "data": [
        "security/ir.model.access.csv",
        "views/ml_category_search_wizard_views.xml",
        "views/ml_attribute_option_picker_wizard_views.xml",
    ],
    "installable": True,
    "application": False,
}