# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductTemplate(models.Model):
    """
    Extension of product.template for advanced
    cost calculation management.
    """

    _inherit = "product.template"


    # ---------------------------------------------------------
    # Applied rule
    # ---------------------------------------------------------

    sw_cost_rule_id = fields.Many2one(
        comodel_name="sw.product.cost.rule",
        string="Applied Cost Rule",
        compute="_compute_sw_cost_values",
        store=True,
    )


    # ---------------------------------------------------------
    # Base cost
    # ---------------------------------------------------------

    sw_base_cost = fields.Float(
        string="Base Cost",
        compute="_compute_sw_cost_values",
        store=True,
        help="Initial cost before applying rules.",
    )


    # ---------------------------------------------------------
    # Final calculated cost
    # ---------------------------------------------------------

    sw_final_cost = fields.Float(
        string="Calculated Cost",
        compute="_compute_sw_cost_values",
        store=True,
        help="Final cost after cascade rules.",
    )


    # ---------------------------------------------------------
    # Suggested sale price
    # ---------------------------------------------------------

    sw_suggested_price = fields.Float(
        string="Suggested Sale Price",
        compute="_compute_sw_cost_values",
        store=True,
    )


    # ---------------------------------------------------------
    # Compute engine
    # ---------------------------------------------------------

    @api.depends(
        "standard_price",
        "categ_id",
        "company_id",
    )
    def _compute_sw_cost_values(self):

        Rule = self.env[
            "sw.product.cost.rule"
        ]


        for product in self:


            # -------------------------------------------------
            # Base cost
            # -------------------------------------------------

            base_cost = product.standard_price


            product.sw_base_cost = base_cost


            # -------------------------------------------------
            # Find rule
            # -------------------------------------------------

            rule = Rule.get_rule_for_product(
                product
            )


            product.sw_cost_rule_id = rule


            # -------------------------------------------------
            # Apply cascade
            # -------------------------------------------------

            if rule:

                calculated_cost = (
                    rule.calculate_cost(
                        base_cost
                    )
                )

            else:

                calculated_cost = base_cost



            product.sw_final_cost = calculated_cost



            # -------------------------------------------------
            # Suggested sale price
            # -------------------------------------------------

            product.sw_suggested_price = (
                calculated_cost
            )