# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductSupplierInfo(models.Model):
    """
    Extension of product.supplierinfo.

    Adds additional cost management information
    for supplier prices.
    """

    _inherit = "product.supplierinfo"

    # ---------------------------------------------------------
    # Cost information
    # ---------------------------------------------------------

    sw_cost_valid_from = fields.Date(
        string="Cost Valid From",
        default=fields.Date.context_today,
        help="Date from which this supplier cost is considered valid.",
    )

    sw_cost_active = fields.Boolean(
        string="Active Cost",
        default=True,
        help="Defines if this supplier cost is currently active.",
    )

    sw_last_update = fields.Datetime(
        string="Last Cost Update",
        readonly=True,
    )

    sw_cost_margin_note = fields.Char(
        string="Internal Note",
        help="Internal reference for this supplier cost.",
    )

    # ---------------------------------------------------------
    # Override price update
    # ---------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):

        records = super().create(vals_list)

        records.write(
            {
                "sw_last_update": fields.Datetime.now(),
            }
        )

        return records

    def write(self, vals):

        result = super().write(vals)

        if "price" in vals:

            self.write(
                {
                    "sw_last_update": fields.Datetime.now(),
                }
            )

        return result