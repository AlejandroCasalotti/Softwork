# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.osv import expression


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
    def get_reference_cost(self, product, quantity=1.0):
        """
        Get the supplier cost to use as base cost.
        Priority:
        1. Supplier marked as reference.
        2. First valid supplier.
        3. Product standard price fallback.
        """


        domain = expression.AND([
            expression.OR([
                [("product_tmpl_id", "=", product.id)],
                [("product_id", "in", product.product_variant_ids.ids)],
            ]),
            [("min_qty", "<=", quantity)],
        ])


        suppliers = self.search(
            domain,
            order="min_qty desc, id asc",
        )


        reference_supplier = suppliers.filtered(
            lambda x: x.sw_is_cost_reference
        )


        if reference_supplier:

            return reference_supplier[0].get_supplier_cost()



        if suppliers:

            return suppliers[0].get_supplier_cost()



        return product.standard_price or 0.0