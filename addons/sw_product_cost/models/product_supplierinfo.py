# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools.float_utils import float_is_zero


class ProductSupplierInfo(models.Model):
    """
    Extension of product.supplierinfo.
    Provides supplier cost information
    for advanced cost calculation.
    """

    _inherit = "product.supplierinfo"


    sw_is_cost_reference = fields.Boolean(
        string="Use as Cost Reference",
        default=False,
        help="Use this supplier price as product cost reference.",
    )


    def get_supplier_cost(self):
        """
        Return supplier purchase price.
        """

        self.ensure_one()

        return self.price or 0.0



    @api.model
    def _get_first_supplier(self, product, quantity=1.0):
        """
        Return first supplier candidate for product.
        Deterministic order:
        - lowest sequence first
        - then lowest min_qty
        - then lowest id
        """
        domain = [
            ("min_qty", "<=", quantity),
            "|",
            ("product_tmpl_id", "=", product.id),
            ("product_id", "in", product.product_variant_ids.ids),
        ]
        suppliers = self.search(
            domain,
            order="sequence asc, min_qty asc, id asc",
        )
        return suppliers[:1]

    @api.model
    def get_reference_cost_data(self, product, quantity=1.0):
        """
        Cost base requested by business:
        - first supplier in list (deterministic order)
        - fallback: standard_price
        Returns dict with price, currency, date and supplier.
        """
        supplier = self._get_first_supplier(product, quantity=quantity)
        if supplier:
            supplier = supplier[0]
            price = supplier.get_supplier_cost()
            currency = supplier.currency_id or supplier.company_id.currency_id or product.company_id.currency_id
            return {
                "price": price,
                "currency": currency,
                "supplier": supplier,
                "date": fields.Date.context_today(self),
                "is_fallback": False,
            }

        return {
            "price": product.standard_price or 0.0,
            "currency": product.company_id.currency_id,
            "supplier": False,
            "date": fields.Date.context_today(self),
            "is_fallback": True,
        }

    @api.model
    def get_reference_cost(self, product, quantity=1.0):
        """
        Backward compatible API: return only numeric cost.
        """
        data = self.get_reference_cost_data(product, quantity=quantity)
        price = data.get("price", 0.0)
        if float_is_zero(price, precision_rounding=product.currency_id.rounding):
            return 0.0
        return price

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        products = (records.mapped("product_tmpl_id") | records.mapped("product_id.product_tmpl_id")).exists()
        if products:
            products._sw_recompute_prices()
        return records

    def write(self, vals):
        res = super().write(vals)
        watched = {"price", "currency_id", "sequence", "min_qty", "sw_is_cost_reference"}
        if watched.intersection(vals.keys()):
            products = (self.mapped("product_tmpl_id") | self.mapped("product_id.product_tmpl_id")).exists()
            if products:
                products._sw_recompute_prices()
        return res

    def unlink(self):
        products = (self.mapped("product_tmpl_id") | self.mapped("product_id.product_tmpl_id")).exists()
        res = super().unlink()
        if products:
            products._sw_recompute_prices()
        return res