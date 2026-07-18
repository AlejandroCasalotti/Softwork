# -*- coding: utf-8 -*-

{
    "name": "Softwork Import by Code",
    "version": "19.0.1.0.0",
    "summary": "Import matching rules by supplier code/internal reference with safe fallbacks",
    "description": """
Softwork Import by Code
=======================

Behavior for imports (without modifying Odoo base code):
- product.supplierinfo:
  * Try to match existing supplierinfo by vendor + supplier product code.
  * If not found, try to resolve product template by internal reference and link.
  * If no match is found, skip creation (no new supplierinfo/product is created).
- product.template:
  * In import context, try to update by internal reference (default_code).
  * Fallback to product name.
  * If no match, create a new product.

Designed with inheritance and minimal coupling to reduce future upgrade impact.
    """,
    "category": "Inventory/Product",
    "author": "Softwork",
    "website": "https://swsistemas.com",
    "license": "LGPL-3",
    "depends": [
        "product",
        "purchase",
    ],
    "data": [],
    "installable": True,
    "application": False,
    "auto_install": False,
}