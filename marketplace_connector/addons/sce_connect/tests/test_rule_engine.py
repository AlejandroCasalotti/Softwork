import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from odoo.exceptions import ValidationError

from ..services.rule_engine import SceConnectRuleEngine


class RuleRecord:
    def __init__(self, rule_id, **values):
        self.id = rule_id
        self.__dict__.update(values)


class RuleModel:
    def __init__(self, rules):
        self.rules = rules

    def search(self, _domain, order=None):
        return sorted(self.rules, key=lambda rule: (rule.sequence, rule.id))


class Tenant:
    def __init__(self, tenant_id=1):
        self.id = tenant_id

    def exists(self):
        return True


class RuleEngineTests(unittest.TestCase):
    def engine(self, rules):
        engine = MagicMock(spec=SceConnectRuleEngine)
        engine.env = {"sce.connect.rule": RuleModel(rules)}
        engine._rules = SceConnectRuleEngine._rules.__get__(engine)
        engine._decimal = SceConnectRuleEngine._decimal
        engine._parse_value = SceConnectRuleEngine._parse_value
        engine._condition_matches = SceConnectRuleEngine._condition_matches
        engine._action_value = SceConnectRuleEngine._action_value
        engine._serializable = SceConnectRuleEngine._serializable
        engine.evaluate = SceConnectRuleEngine.evaluate.__get__(engine)
        return engine

    @staticmethod
    def rule(rule_id, sequence=10, scope="sync", field="stock", operator="eq", value="10", action="allow", action_value=None):
        return RuleRecord(
            rule_id,
            sequence=sequence,
            scope=scope,
            condition_field=field,
            operator=operator,
            value=value,
            action=action,
            action_value=action_value,
            active=True,
        )

    def test_all_operators(self):
        context = {"stock": 10, "sku": "ABC", "active": True}
        cases = [
            ("eq", "10", True),
            ("neq", "9", True),
            ("gt", "9", True),
            ("gte", "10", True),
            ("lt", "11", True),
            ("lte", "10", True),
            ("in", "[9, 10]", True),
            ("not_in", "[9, 11]", True),
            ("is_set", "", True),
            ("is_not_set", "", False),
        ]
        for operator, value, expected in cases:
            rule = self.rule(1, operator=operator, value=value)
            self.assertEqual(self.engine([rule])._condition_matches(rule, context), expected)

    def test_actions_and_decimal_result(self):
        rules = [
            self.rule(1, sequence=1, field="price", operator="gte", value="100", action="multiply", action_value="1.20"),
            self.rule(2, sequence=2, field="price", operator="gte", value="100", action="add", action_value="500"),
            self.rule(3, sequence=3, field="price", operator="gte", value="100", action="subtract", action_value="100"),
        ]
        result = self.engine(rules).evaluate(Tenant(), "price", {"price": Decimal("10000.00")})

        self.assertTrue(result["allowed"])
        self.assertEqual(result["value"], "12400.00")
        self.assertEqual(result["matched_rules"], [1, 2, 3])

    def test_set_value(self):
        result = self.engine([
            self.rule(1, field="stock", operator="lt", value="3", action="set_value", action_value="3")
        ]).evaluate(Tenant(), "stock", {"stock": 1})

        self.assertTrue(result["allowed"])
        self.assertEqual(result["value"], "3.00")

    def test_block_stops_later_actions(self):
        rules = [
            self.rule(1, sequence=1, action="multiply", field="stock", operator="gte", value="1", action_value="2"),
            self.rule(2, sequence=2, action="block", field="stock", operator="gte", value="1"),
            self.rule(3, sequence=3, action="add", field="stock", operator="gte", value="1", action_value="100"),
        ]
        result = self.engine(rules).evaluate(Tenant(), "stock", {"stock": 5})

        self.assertFalse(result["allowed"])
        self.assertEqual(result["blocked_by"], 2)
        self.assertIsNone(result["value"])
        self.assertEqual([action["rule_id"] for action in result["actions"]], [1, 2])

    def test_order_is_sequence_then_id(self):
        rules = [
            self.rule(3, sequence=10, action="add", field="stock", operator="gte", value="1", action_value="3"),
            self.rule(2, sequence=10, action="add", field="stock", operator="gte", value="1", action_value="2"),
        ]
        result = self.engine(rules).evaluate(Tenant(), "stock", {"stock": 1})

        self.assertEqual(result["matched_rules"], [2, 3])
        self.assertEqual(result["value"], "6.00")

    def test_no_rules_allows_without_changing_value(self):
        result = self.engine([]).evaluate(Tenant(), "stock", {"stock": 10})

        self.assertEqual(result, {
            "allowed": True,
            "value": 10,
            "matched_rules": [],
            "blocked_by": None,
            "actions": [],
        })

    def test_inactive_rules_are_not_evaluated_by_domain(self):
        engine = self.engine([])
        engine.env["sce.connect.rule"].rules = []
        result = engine.evaluate(Tenant(), "sync", {"active": True})
        self.assertEqual(result["matched_rules"], [])

    def test_invalid_tenant_and_field_are_rejected(self):
        with self.assertRaises(ValidationError):
            self.engine([]).evaluate(False, "stock", {"stock": 1})
        rule = self.rule(1, field="secret")
        with self.assertRaises(ValidationError):
            self.engine([rule]).evaluate(Tenant(), "sync", {"secret": "x"})

    def test_invalid_context_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.engine([]).evaluate(Tenant(), "stock", None)

    def test_no_dynamic_code_execution_is_present(self):
        import inspect

        source = inspect.getsource(SceConnectRuleEngine)
        self.assertNotIn("eval(", source)
        self.assertNotIn("exec(", source)
        self.assertNotIn("safe_eval", source)


    if __name__ == "__main__":
        unittest.main()
