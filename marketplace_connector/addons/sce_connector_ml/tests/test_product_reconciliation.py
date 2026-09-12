import unittest
from unittest.mock import MagicMock, patch

from odoo.exceptions import UserError

from ..services.product_reconciliation import ProductReconciliationService


class ProductReconciliationServiceTests(unittest.TestCase):
    def setUp(self):
        self.env = MagicMock()
        self.account = MagicMock()
        self.account.id = 7
        self.odoo_reader = MagicMock()
        self.ml_reader = MagicMock()
        self.service = ProductReconciliationService(self.env, self.account)
        self.service._odoo_reader = MagicMock(return_value=self.odoo_reader)
        self.service._ml_reader = MagicMock(return_value=self.ml_reader)

    def test_odoo_connection_ok_es_read_only(self):
        self.odoo_reader.get_product_fields.return_value = {"default_code": {"type": "char"}}
        self.odoo_reader.search_products.return_value = [{"id": 1, "default_code": "ABC"}]
        result = self.service.test_odoo_connection()
        self.assertEqual(result["status"], "OK")
        self.assertTrue(result["default_code_available"])
        self.odoo_reader.get_product_fields.assert_called_once_with()
        self.odoo_reader.search_products.assert_called_once_with(
            fields=["id", "default_code"], limit=1, order="id asc"
        )

    def test_odoo_connection_error_no_se_silencia(self):
        self.odoo_reader.get_product_fields.side_effect = UserError("Odoo error")
        with self.assertRaises(UserError):
            self.service.test_odoo_connection()

    def test_ml_connection_ok_usa_catalogo_existente(self):
        self.ml_reader.list_item_ids.return_value = {
            "seller_id": "123", "paging": {"total": 2}, "item_ids": ["MLA1"]
        }
        result = self.service.test_mercadolibre_connection()
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["seller_id"], "123")
        self.assertEqual(result["publications_accessible"], 2)
        self.ml_reader.list_item_ids.assert_called_once_with(offset=0, limit=1)

    def test_analyze_match_no_match_y_conflict(self):
        self.odoo_reader.search_products.side_effect = [
            [
                {"id": 1, "default_code": "MATCH"},
                {"id": 2, "default_code": "DUP"},
                {"id": 3, "default_code": "DUP"},
                {"id": 4, "default_code": False},
            ],
            [],
        ]
        self.ml_reader.list_all_item_ids.return_value = {"item_ids": ["MLA1", "MLA2"], "count": 2}
        self.ml_reader.get_item.side_effect = [
            {
                "item_id": "MLA1", "canonical_sku": "MATCH", "seller_custom_field": "legacy",
                "variations": [], "raw": {},
            },
            {
                "item_id": "MLA2", "canonical_sku": "MLONLY", "seller_custom_field": False,
                "variations": [{
                    "variation_id": 10, "canonical_sku": "DUP", "seller_custom_field": "legacy-dup", "raw": {},
                }], "raw": {},
            },
        ]
        result = self.service.analyze()
        self.assertEqual(result["stats"]["odoo_total_products"], 4)
        self.assertEqual(result["stats"]["odoo_products_with_sku"], 3)
        self.assertEqual(result["stats"]["odoo_products_without_sku"], 1)
        self.assertEqual(result["stats"]["ml_total_publications"], 2)
        self.assertEqual(result["stats"]["match"], 1)
        self.assertEqual(result["stats"]["conflict"], 2)
        statuses = {(line["sku"], line["status"]) for line in result["details"]}
        self.assertIn(("MATCH", "MATCH"), statuses)
        self.assertIn(("DUP", "CONFLICT"), statuses)
        self.assertIn(("MLONLY", "NO_MATCH"), statuses)
        self.assertEqual(self.env.method_calls, [])

    def test_analyze_variante_mantiene_item_variation_y_sku_canonico(self):
        self.odoo_reader.search_products.side_effect = [[{"id": 1, "default_code": "RED-M"}], []]
        self.ml_reader.list_all_item_ids.return_value = {"item_ids": ["MLA1"], "count": 1}
        self.ml_reader.get_item.return_value = {
            "item_id": "MLA1", "canonical_sku": False, "seller_custom_field": False,
            "variations": [{"variation_id": 22, "canonical_sku": "RED-M", "seller_custom_field": "legacy", "raw": {}}],
            "raw": {},
        }
        result = self.service.analyze()
        line = next(line for line in result["details"] if line["sku"] == "RED-M")
        self.assertEqual(line["status"], "MATCH")
        self.assertEqual(line["mercadolibre_item_id"], "MLA1")
        self.assertEqual(line["mercadolibre_variation_id"], 22)
        self.assertEqual(line["mercadolibre_sku"], "RED-M")

    def test_ml_error_se_propaga(self):
        self.ml_reader.list_all_item_ids.side_effect = UserError("ML error")
        with patch.object(self.service, "_read_all_odoo_products", return_value=[]):
            with self.assertRaises(UserError):
                self.service.analyze()


if __name__ == "__main__":
    unittest.main()
