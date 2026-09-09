from odoo import api, fields, models
from odoo.exceptions import ValidationError


RULE_SCOPES = (("stock", "Stock"), ("price", "Price"), ("sync", "Sync"))
RULE_FIELDS = tuple((value, value) for value in ("stock", "price", "cost", "sku", "barcode", "active"))
RULE_OPERATORS = tuple(
    (value, value)
    for value in ("eq", "neq", "gt", "gte", "lt", "lte", "in", "not_in", "is_set", "is_not_set")
)
RULE_ACTIONS = tuple(
    (value, value.title())
    for value in ("allow", "block", "set_value", "multiply", "add", "subtract")
)


class SceConnectRule(models.Model):
    _name = "sce.connect.rule"
    _description = "SCE Connect Declarative Rule"
    _order = "sequence, id"

    ALLOWED_FIELDS = ("stock", "price", "cost", "sku", "barcode", "active")
    SCOPES = ("stock", "price", "sync")
    OPERATORS = ("eq", "neq", "gt", "gte", "lt", "lte", "in", "not_in", "is_set", "is_not_set")
    ACTIONS = ("allow", "block", "set_value", "multiply", "add", "subtract")

    name = fields.Char(required=True, index=True)
    tenant_id = fields.Many2one("sce.tenant", required=True, ondelete="cascade", index=True)
    active = fields.Boolean(default=True, index=True)
    sequence = fields.Integer(default=10, required=True, index=True)
    scope = fields.Selection(
        RULE_SCOPES, required=True, default="sync", index=True
    )
    condition_field = fields.Selection(
        RULE_FIELDS, required=True
    )
    operator = fields.Selection(
        RULE_OPERATORS, required=True
    )
    value = fields.Text()
    action = fields.Selection(
        RULE_ACTIONS, required=True, default="allow"
    )
    action_value = fields.Text()

    @api.constrains("sequence")
    def _check_sequence(self):
        for rule in self:
            if rule.sequence < 0:
                raise ValidationError("La secuencia de la regla no puede ser negativa.")

    @api.constrains("condition_field", "operator", "action", "action_value")
    def _check_rule_definition(self):
        for rule in self:
            if rule.condition_field not in self.ALLOWED_FIELDS:
                raise ValidationError("El campo de condición no está permitido.")
            if rule.operator not in self.OPERATORS:
                raise ValidationError("El operador de la regla no está permitido.")
            if rule.action not in self.ACTIONS:
                raise ValidationError("La acción de la regla no está permitida.")
            if rule.action in {"set_value", "multiply", "add", "subtract"} and not rule.action_value:
                raise ValidationError("La acción seleccionada requiere un valor.")
