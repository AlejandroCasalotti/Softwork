from decimal import Decimal, InvalidOperation, ROUND_FLOOR

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SceConnectStockPolicy(models.Model):
    _name = "sce.connect.stock.policy"
    _description = "SCE Connect Stock Policy"
    _order = "account_id"

    account_id = fields.Many2one("sce.account", required=True, ondelete="cascade", index=True)
    tenant_id = fields.Many2one(related="account_id.tenant_id", store=True, index=True, readonly=True)
    active = fields.Boolean(default=False, index=True)
    source = fields.Selection(
        [("free_qty", "Odoo Free to Use")], required=True, default="free_qty"
    )
    reserve_type = fields.Selection(
        [("none", "Sin reserva"), ("fixed", "Cantidad fija"), ("percent", "Porcentaje")],
        required=True,
        default="none",
    )
    reserve_value = fields.Float(default=0.0, digits=(16, 4))

    _account_unique = models.Constraint(
        "UNIQUE(account_id)",
        "Una cuenta sólo puede tener una política de stock.",
    )

    @api.constrains("account_id", "active", "source", "reserve_type", "reserve_value")
    def _check_policy(self):
        for policy in self:
            if policy.account_id.connect_ownership_state != "ready":
                raise ValidationError(
                    "La cuenta debe tener ownership Connect completo antes de configurar stock."
                )
            if policy.source != "free_qty":
                raise ValidationError("La fuente de stock seleccionada no está soportada.")
            try:
                value = Decimal(str(policy.reserve_value or 0))
            except (InvalidOperation, TypeError, ValueError) as error:
                raise ValidationError("La reserva de stock debe ser numérica.") from error
            if value < 0:
                raise ValidationError("La reserva de stock no puede ser negativa.")
            if policy.reserve_type == "percent" and value > 100:
                raise ValidationError("La reserva porcentual no puede superar el 100%.")
            if policy.reserve_type == "none" and value != 0:
                raise ValidationError("Una política sin reserva debe tener valor cero.")

    def calculate(self, source_stock):
        self.ensure_one()
        from ..services.stock_policy_calculator import StockPolicyCalculator

        return StockPolicyCalculator.calculate(
            source_stock,
            self.reserve_type,
            self.reserve_value,
        )