from decimal import Decimal, InvalidOperation

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SceConnectPricePolicy(models.Model):
    _name = "sce.connect.price.policy"
    _description = "SCE Connect Price Policy"
    _order = "account_id"

    account_id = fields.Many2one("sce.account", required=True, ondelete="cascade", index=True)
    tenant_id = fields.Many2one(related="account_id.tenant_id", store=True, index=True, readonly=True)
    external_connection_id = fields.Many2one(
        related="account_id.external_connection_id", store=True, index=True, readonly=True
    )
    active = fields.Boolean(default=False, index=True)
    remote_pricelist_id = fields.Integer(string="ID remoto", copy=False)
    remote_pricelist_name = fields.Char(string="Lista de precios Odoo", copy=False)
    adjustment_percent = fields.Float(string="Ajuste porcentual", digits=(16, 4), default=0.0)
    adjustment_fixed = fields.Float(string="Ajuste fijo", digits=(16, 4), default=0.0)
    commercial_rounding = fields.Selection(
        [("none", "Sin redondeo"), ("10", "10"), ("100", "100"), ("1000", "1000")],
        required=True,
        default="none",
    )
    safety_enabled = fields.Boolean(string="Protección de precio", default=True)
    max_decrease_percent = fields.Float(
        string="Baja máxima permitida (%)", digits=(16, 4), default=20.0
    )

    _account_unique = models.Constraint(
        "UNIQUE(account_id)",
        "Una cuenta sólo puede tener una política de precio.",
    )

    @api.constrains(
        "account_id",
        "active",
        "remote_pricelist_id",
        "adjustment_percent",
        "adjustment_fixed",
        "commercial_rounding",
        "max_decrease_percent",
    )
    def _check_policy(self):
        for policy in self:
            if policy.account_id.connect_ownership_state != "ready":
                raise ValidationError(
                    "La cuenta debe tener ownership Connect completo antes de configurar precios."
                )
            if policy.active and policy.remote_pricelist_id <= 0:
                raise ValidationError("Seleccione una lista de precios Odoo válida.")
            try:
                max_decrease = Decimal(str(policy.max_decrease_percent or 0))
            except (InvalidOperation, TypeError, ValueError) as error:
                raise ValidationError("La protección de precio debe ser numérica.") from error
            if max_decrease < 0 or max_decrease > 100:
                raise ValidationError("La baja máxima permitida debe estar entre 0% y 100%.")

    def calculate(self, base_price, previous_price=None):
        self.ensure_one()
        from ..services.price_policy_calculator import PricePolicyCalculator

        return PricePolicyCalculator.calculate(
            base_price,
            adjustment_percent=self.adjustment_percent,
            adjustment_fixed=self.adjustment_fixed,
            commercial_rounding=self.commercial_rounding,
            safety_enabled=self.safety_enabled,
            max_decrease_percent=self.max_decrease_percent,
            previous_price=previous_price,
        )

    def action_select_remote_pricelist(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Seleccionar lista de precios Odoo",
            "res_model": "sce.connect.pricelist.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_account_id": self.account_id.id, "default_policy_id": self.id},
        }