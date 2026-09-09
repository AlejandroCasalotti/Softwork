import json
from decimal import Decimal, InvalidOperation

from odoo import models
from odoo.exceptions import ValidationError


class SceConnectRuleEngine(models.AbstractModel):
    _name = "sce.connect.rule.engine"
    _description = "SCE Connect Declarative Rule Engine"

    NUMERIC_FIELDS = {"stock", "price", "cost"}
    ALLOWED_FIELDS = {"stock", "price", "cost", "sku", "barcode", "active"}

    def _rules(self, tenant, scope):
        if not tenant or not tenant.exists():
            raise ValidationError("El contexto de reglas requiere un tenant válido.")
        if scope not in {"stock", "price", "sync"}:
            raise ValidationError("El alcance de reglas no está permitido.")
        return self.env["sce.connect.rule"].search(
            [("tenant_id", "=", tenant.id), ("scope", "=", scope), ("active", "=", True)],
            order="sequence asc, id asc",
        )

    @staticmethod
    def _decimal(value):
        try:
            result = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            raise ValidationError("El valor de la regla no es numérico.")
        if not result.is_finite():
            raise ValidationError("El valor de la regla no es finito.")
        return result

    @classmethod
    def _parse_value(cls, rule, current_context):
        raw = rule.value
        if rule.operator in {"is_set", "is_not_set"}:
            return None
        if rule.operator in {"in", "not_in"}:
            try:
                parsed = json.loads(raw or "[]")
            except (TypeError, ValueError):
                parsed = [item.strip() for item in (raw or "").split(",") if item.strip()]
            if not isinstance(parsed, list):
                raise ValidationError("El valor in/not_in debe ser una lista JSON.")
            return parsed
        if rule.condition_field in cls.NUMERIC_FIELDS:
            return cls._decimal(raw)
        return raw

    @classmethod
    def _condition_matches(cls, rule, current_context):
        if rule.condition_field not in cls.ALLOWED_FIELDS:
            raise ValidationError("El campo de regla no está permitido.")
        current = current_context.get(rule.condition_field)
        if rule.operator == "is_set":
            return current not in (None, False, "")
        if rule.operator == "is_not_set":
            return current in (None, False, "")
        expected = cls._parse_value(rule, current_context)
        if rule.condition_field in cls.NUMERIC_FIELDS:
            if current is None or current is False or current == "":
                return False
            current = cls._decimal(current)
        if rule.operator == "eq":
            return current == expected
        if rule.operator == "neq":
            return current != expected
        if rule.operator == "gt":
            return current > expected
        if rule.operator == "gte":
            return current >= expected
        if rule.operator == "lt":
            return current < expected
        if rule.operator == "lte":
            return current <= expected
        if rule.operator == "in":
            return current in expected
        if rule.operator == "not_in":
            return current not in expected
        raise ValidationError("El operador de la regla no está permitido.")

    @classmethod
    def _action_value(cls, rule, current):
        if rule.action == "set_value":
            return cls._decimal(rule.action_value) if isinstance(current, (int, float, Decimal)) else rule.action_value
        return cls._decimal(rule.action_value)

    @staticmethod
    def _serializable(value):
        if isinstance(value, Decimal):
            return format(value.quantize(Decimal("0.01")), "f")
        return value

    def evaluate(self, tenant, scope, context):
        if not isinstance(context, dict):
            raise ValidationError("El contexto de reglas debe ser un diccionario.")
        current_context = dict(context)
        current_value = current_context.get("price") if scope == "price" else current_context.get("stock")
        result = {
            "allowed": True,
            "value": self._serializable(current_value),
            "matched_rules": [],
            "blocked_by": None,
            "actions": [],
        }
        for rule in self._rules(tenant, scope):
            if not self._condition_matches(rule, current_context):
                continue
            result["matched_rules"].append(rule.id)
            if rule.action == "block":
                result["allowed"] = False
                result["value"] = None
                result["blocked_by"] = rule.id
                result["actions"].append({"rule_id": rule.id, "action": rule.action})
                break
            if rule.action == "allow":
                result["actions"].append({"rule_id": rule.id, "action": rule.action})
                continue
            action_value = self._action_value(rule, current_value)
            if current_value is None:
                raise ValidationError("No hay valor actual para aplicar la acción de la regla.")
            numeric_current = self._decimal(current_value)
            if rule.action == "set_value":
                current_value = action_value
            elif rule.action == "multiply":
                current_value = numeric_current * action_value
            elif rule.action == "add":
                current_value = numeric_current + action_value
            elif rule.action == "subtract":
                current_value = numeric_current - action_value
            else:
                raise ValidationError("La acción de la regla no está permitida.")
            current_context["price" if scope == "price" else "stock"] = current_value
            result["value"] = self._serializable(current_value)
            result["actions"].append({"rule_id": rule.id, "action": rule.action, "value": self._serializable(action_value)})
        return result
