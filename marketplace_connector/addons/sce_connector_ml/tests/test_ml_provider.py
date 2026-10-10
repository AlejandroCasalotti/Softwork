from types import SimpleNamespace
from unittest.mock import Mock

from odoo.tests import TransactionCase, tagged

from ..services.ml_provider import MercadoLibreProvider


@tagged("post_install", "-at_install")
class MercadoLibreProviderTest(TransactionCase):
    def setUp(self):
        super().setUp()
        self.provider = MercadoLibreProvider(
            self.env,
            SimpleNamespace(id=7, external_user_id="seller-7"),
        )

    def test_build_item_payload_without_core_provider(self):
        payload = self.provider._build_item_payload({
            "title": "Test product",
            "category_id": "MLA123",
            "price": 1250.125,
            "stock": -2,
            "seller_custom_field": "SKU-7",
            "family_name": "Test family",
            "warranty": "12 meses",
            "attributes": [{"id": "BRAND", "value_name": "Acme"}],
            "pictures": ["https://example.com/product.jpg"],
            "variations": [{
                "price": 1200,
                "available_quantity": 3,
                "attribute_combinations": [{"id": "COLOR", "value_name": "Blue"}],
            }],
        })

        self.assertEqual(payload["price"], 1250.13)
        self.assertEqual(payload["available_quantity"], 0)
        self.assertEqual(payload["seller_custom_field"], "SKU-7")
        self.assertEqual(payload["pictures"], [{"source": "https://example.com/product.jpg"}])
        self.assertEqual(payload["sale_terms"], [{"id": "WARRANTY_TYPE", "value_name": "12 meses"}])
        self.assertEqual(payload["variations"][0]["available_quantity"], 3)

    def test_questions_use_connector_transport(self):
        self.provider._request = Mock(return_value={"questions": [{"id": 10}]})

        result = self.provider.get_questions(limit=200)

        self.assertEqual(result["items"], [{"id": 10}])
        self.provider._request.assert_called_once_with(
            "GET",
            "/questions/search",
            params={
                "seller_id": "seller-7",
                "status": "UNANSWERED",
                "api_version": 4,
                "limit": 50,
            },
        )

    def test_answer_question_uses_connector_transport(self):
        self.provider._request = Mock(return_value={"id": 10})

        result = self.provider.answer_question("10", "  Answer  ")

        self.assertTrue(result["ok"])
        self.provider._request.assert_called_once_with(
            "POST",
            "/answers",
            payload={"question_id": "10", "text": "Answer"},
        )