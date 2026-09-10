import unittest
from decimal import Decimal

from odoo.exceptions import ValidationError

from ..services.price_policy_calculator import PricePolicyCalculator
from ..services.stock_policy_calculator import StockPolicyCalculator


class PolicyCalculatorTests(unittest.TestCase):
    def test_stock_without_reserve(self):
        self.assertEqual(StockPolicyCalculator.calculate(20, "none", 0), Decimal("20"))

    def test_stock_fixed_reserve_clamps_to_zero(self):
        self.assertEqual(StockPolicyCalculator.calculate(2, "fixed", 5), Decimal("0"))

    def test_stock_percent_reserve(self):
        self.assertEqual(StockPolicyCalculator.calculate(20, "percent", 10), Decimal("18"))

    def test_stock_invalid_reserve(self):
        with self.assertRaises(ValidationError):
            StockPolicyCalculator.calculate(20, "percent", 101)
        with self.assertRaises(ValidationError):
            StockPolicyCalculator.calculate(20, "fixed", -1)

    def test_price_percentage_fixed_and_rounding(self):
        result = PricePolicyCalculator.calculate(
            "100.00",
            adjustment_percent=10,
            adjustment_fixed=50,
            commercial_rounding="100",
        )
        self.assertEqual(result["price"], Decimal("100.00"))

    def test_price_rounding_is_commercial_downward(self):
        self.assertEqual(
            PricePolicyCalculator.calculate("1234", commercial_rounding="10")["price"],
            Decimal("1230.00"),
        )
        self.assertEqual(
            PricePolicyCalculator.calculate("1234", commercial_rounding="100")["price"],
            Decimal("1200.00"),
        )

    def test_price_safety_allows_first_sync_and_blocks_large_drop(self):
        first = PricePolicyCalculator.calculate("100", safety_enabled=True, previous_price=None)
        blocked = PricePolicyCalculator.calculate(
            "70", safety_enabled=True, max_decrease_percent=20, previous_price="100"
        )
        allowed = PricePolicyCalculator.calculate(
            "85", safety_enabled=True, max_decrease_percent=20, previous_price="100"
        )
        self.assertFalse(first["blocked"])
        self.assertTrue(blocked["blocked"])
        self.assertFalse(allowed["blocked"])


if __name__ == "__main__":
    unittest.main()