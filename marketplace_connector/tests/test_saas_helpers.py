import runpy
import unittest
from datetime import date
from pathlib import Path


ADDONS = Path(__file__).resolve().parents[1] / "addons"
periods = runpy.run_path(str(ADDONS / "softwork_ecommerce_conector_base/services/billing_period.py"))
parse_reserves = runpy.run_path(str(ADDONS / "sce_customer_portal/controllers/reserve_csv.py"))["parse_reserves"]


class SaaSHelpersTest(unittest.TestCase):
    def test_anniversary_does_not_drift(self):
        anchor = date(2026, 1, 31)
        self.assertEqual(periods["period_for_date"](anchor, date(2026, 3, 30)),
                         (date(2026, 2, 28), date(2026, 3, 30)))
        self.assertEqual(periods["period_for_date"](anchor, date(2026, 3, 31)),
                         (date(2026, 3, 31), date(2026, 4, 29)))

    def test_leap_year(self):
        self.assertEqual(periods["anniversary"](date(2024, 1, 31), 1), date(2024, 2, 29))

    def test_trial_and_cancellation_proration(self):
        self.assertEqual(periods["billable_days"](date(2026, 1, 1), date(2026, 1, 31),
                                                  date(2026, 1, 14)), 17)
        self.assertEqual(periods["billable_days"](date(2026, 1, 1), date(2026, 1, 31),
                                                  date(2026, 1, 14), date(2026, 1, 20)), 6)

    def test_csv_excel_delimiters_and_zero(self):
        for separator in (",", ";"):
            content = f"sku{separator}reserve_qty\nA{separator}0\nB{separator}2\n".encode()
            self.assertEqual(parse_reserves(content), [("A", 0), ("B", 2)])

    def test_csv_invalid_rows_fail_whole_import(self):
        for content in (b"sku,reserve_qty\nA,-1\n", b"sku,reserve_qty\nA,1.5\n",
                        b"sku,reserve_qty\nA,2\nA,3\n", b"sku,reserve_qty\n,2\n",
                        b"sku\nA\n", b"sku,reserve_qty\n"):
            with self.subTest(content=content), self.assertRaises(ValueError):
                parse_reserves(content)


if __name__ == "__main__":
    unittest.main()