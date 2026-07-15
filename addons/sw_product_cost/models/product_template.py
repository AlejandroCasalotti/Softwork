# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductTemplate(models.Model):
    """
    Extension of product.template.

    Applies advanced cost rules with
    sequential calculation lines.
    """

    _inherit = "product.template"


    # ---------------------------------------------------------
    # Base cost
    # ---------------------------------------------------------

    sw_cost_amount = fields.Float(
        string="Base Cost",
        compute="_compute_sw_cost_values",
        store=True,
        help="Original product cost.",
    )


    # ---------------------------------------------------------
    # Applied rule
    # ---------------------------------------------------------

    sw_cost_rule_id = fields.Many2one(
        "sw.product.cost.rule",
        string="Applied Cost Rule",
        compute="_compute_sw_cost_values",
        store=True,
    )


    # ---------------------------------------------------------
    # Final calculated cost
    # ---------------------------------------------------------

    sw_final_cost = fields.Float(
        string="Final Calculated Cost",
        compute="_compute_sw_cost_values",
        store=True,
        help="Cost after applying all rule operations.",
    )


    # ---------------------------------------------------------
    # Suggested price
    # ---------------------------------------------------------

    sw_suggested_price = fields.Float(
        string="Suggested Sale Price",
        compute="_compute_sw_cost_values",
        store=True,
    )


    # =========================================================
    # Find rule
    # =========================================================

    def _find_cost_rule(self):

        self.ensure_one()

        Rule = self.env["sw.product.cost.rule"]


        rules = Rule.search(
            [
                ("active", "=", True),
                (
                    "|",
                    ("company_id", "=", self.company_id.id),
                    ("company_id", "=", False),
                ),
            ],
            order="sequence asc",
        )


        for rule in rules:

            if rule.match_product(self):
                return rule


        return False



    # =========================================================
    # Calculate costs
    # =========================================================

    @api.depends(
        "standard_price",
        "categ_id",
        "company_id",
        "sw_cost_rule_id",
        "sw_cost_rule_id.line_ids",
        "sw_cost_rule_id.line_ids.sequence",
        "sw_cost_rule_id.line_ids.operation",
        "sw_cost_rule_id.line_ids.value",
    )
    def _compute_sw_cost_values(self):

        for product in self:


            base_cost = product.standard_price


            product.sw_cost_amount = base_cost


            rule = product._find_cost_rule()


            product.sw_cost_rule_id = rule



            if rule:


                final_cost = rule.calculate_cost(
                    base_cost
                )


                product.sw_final_cost = final_cost


                # La regla ya calcula precio final
                # usando margen incluido

                product.sw_suggested_price = final_cost



            else:


                product.sw_final_cost = base_cost


                product.sw_suggested_price = base_cost