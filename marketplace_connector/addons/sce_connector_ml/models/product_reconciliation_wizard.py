from odoo import fields, models


class SceProductReconciliationWizard(models.TransientModel):
    _name = "sce.product.reconciliation.wizard"
    _description = "SCE Product Reconciliation Diagnostics"

    account_id = fields.Many2one("sce.account", required=True, readonly=True)
    status = fields.Selection(
        [("OK", "OK"), ("ERROR", "Error")], default="OK", readonly=True
    )
    analyzed_at = fields.Datetime(readonly=True)
    latency_ms = fields.Integer(readonly=True)
    odoo_total_products = fields.Integer(readonly=True)
    odoo_products_with_sku = fields.Integer(readonly=True)
    odoo_products_without_sku = fields.Integer(readonly=True)
    ml_total_publications = fields.Integer(readonly=True)
    ml_publications_with_sku = fields.Integer(readonly=True)
    ml_publications_without_sku = fields.Integer(readonly=True)
    match_count = fields.Integer(readonly=True)
    no_match_count = fields.Integer(readonly=True)
    conflict_count = fields.Integer(readonly=True)
    invalid_count = fields.Integer(readonly=True)
    line_ids = fields.One2many(
        "sce.product.reconciliation.line", "wizard_id", readonly=True
    )


class SceProductReconciliationLine(models.TransientModel):
    _name = "sce.product.reconciliation.line"
    _description = "SCE Product Reconciliation Diagnostic Line"
    _order = "sku, id"

    wizard_id = fields.Many2one(
        "sce.product.reconciliation.wizard", required=True, ondelete="cascade"
    )
    status = fields.Selection(
        [("MATCH", "MATCH"), ("NO_MATCH", "NO_MATCH"), ("CONFLICT", "CONFLICT"), ("INVALID", "INVALID")],
        required=True,
        readonly=True,
    )
    sku = fields.Char(readonly=True, index=True)
    odoo_product_id = fields.Integer(readonly=True)
    odoo_default_code = fields.Char(readonly=True)
    mercadolibre_item_id = fields.Char(readonly=True)
    mercadolibre_variation_id = fields.Char(readonly=True)
    mercadolibre_sku = fields.Char(readonly=True)
