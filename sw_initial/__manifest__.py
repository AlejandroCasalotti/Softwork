# -*- coding: utf-8 -*-
{
    "name": "SW Initial",
    "summary": "Campos iniciales y funciones base para Ventas, Compras y Contabilidad",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "author": "SoftWork",
    "license": "LGPL-3",
    "depends": [
        "sale_management",
        "purchase",
        "account",
        "website_sale",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/account_journal_data.xml",
        "report/sw_sale_budget_report.xml",
        "views/sale_order_views.xml",
        "views/purchase_order_views.xml",
    ],
    "installable": True,
    "application": False,
}