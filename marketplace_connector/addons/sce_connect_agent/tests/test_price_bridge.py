import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from odoo.exceptions import AccessError

from ..models.price_bridge import SceConnectPriceBridge


class FakeRecord:
    def __init__(self, record_id, company_id=2):
        self.id = record_id
        self.company_id = SimpleNamespace(id=company_id)
        self.uom_id = SimpleNamespace(id=1)

    def exists(self):
        return self


class FakeModel:
    def __init__(self, record):
        self.record = record

    def browse(self, _record_id):
        return self.record


class FakePricelist(FakeRecord):
    currency_id = SimpleNamespace(id=3)

    def _get_product_price(self, _product, _quantity, uom=None):
        return 1250.5


class FakeEnv:
    def __init__(self):
        self.context = {"allowed_company_ids": [2], "company_id": 2}
        self.company = SimpleNamespace(id=2)
        self.models = {
            "product.product": FakeModel(FakeRecord(11)),
            "product.pricelist": FakeModel(FakePricelist(4)),
        }

    def with_context(self, **values):
        self.context = values
        return self

    def __getitem__(self, model):
        return self.models[model]


class PriceBridgeTests(unittest.TestCase):
    def bridge(self):
        bridge = MagicMock(spec=SceConnectPriceBridge)
        bridge.env = FakeEnv()
        bridge.get_product_pricelist_price = SceConnectPriceBridge.get_product_pricelist_price.__get__(bridge)
        return bridge

    def test_uses_official_pricelist_calculation_and_returns_decimal_text(self):
        result = self.bridge().get_product_pricelist_price(11, 4, quantity=1, company_id=2)

        self.assertEqual(result["price"], "1250.5")
        self.assertEqual(result["currency_id"], 3)

    def test_rejects_company_outside_remote_context(self):
        with self.assertRaises(AccessError):
            self.bridge().get_product_pricelist_price(11, 4, quantity=1, company_id=9)


if __name__ == "__main__":
    unittest.main()