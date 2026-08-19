# -*- coding: utf-8 -*-
{
    "name": "SCE Product Marketplace",
    "summary": "Capa genérica de publicación de productos en marketplaces",
    "description": """
SCE Product Marketplace
========================
Modelo de publicación agnóstico de marketplace: un mismo producto puede tener
varias publicaciones (una por cuenta/marketplace) sin acoplar product.template
a los campos específicos de un proveedor.

Los conectores concretos (sce_connector_ml, futuros sce_connector_amazon, etc.)
extienden marketplace.publication con sus propios campos y servicios.
    """,
    "version": "19.0.1.0.0",
    "category": "Sales/Sales",
    "author": "Softwork",
    "website": "https://swsistemas.com",
    "license": "LGPL-3",
    "depends": ["product", "softwork_ecommerce_conector_base"],
    "data": [
        "security/ir.model.access.csv",
        "views/marketplace_publication_views.xml",
        "views/marketplace_product_mapping_views.xml",
        "views/marketplace_account_views.xml",
        "views/marketplace_sale_order_views.xml",
        "views/sce_job_marketplace_views.xml",
        "views/product_template_views.xml",
    ],
    "installable": True,
    "application": False,
}
