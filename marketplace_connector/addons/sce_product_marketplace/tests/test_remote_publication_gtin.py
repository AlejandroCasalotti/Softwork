from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("-at_install", "post_install")
class TestRemotePublicationGtin(TransactionCase):
    def setUp(self):
        super().setUp()
        self.publication_line = self.env["marketplace.remote.publication.wizard.line"]

    def test_gtin_value_is_accepted_without_empty_reason(self):
        state = self.publication_line._gtin_submission_state([
            {"id": "GTIN", "value_name": "7790001000018"},
            {"id": "EMPTY_GTIN_REASON"},
        ])

        self.assertEqual(state, {"has_gtin": True, "has_reason": False})

    def test_allowed_empty_gtin_reason_is_accepted_without_gtin(self):
        state = self.publication_line._gtin_submission_state([
            {"id": "GTIN"},
            {
                "id": "EMPTY_GTIN_REASON",
                "value_id": "17055160",
                "allowed_values_json": '[{"id": "17055160", "name": "No aplica"}]',
            },
        ])

        self.assertEqual(state, {"has_gtin": False, "has_reason": True})

    def test_reason_requires_allowed_value_id(self):
        with self.assertRaisesRegex(UserError, "ID valor"):
            self.publication_line._gtin_submission_state([
                {
                    "id": "EMPTY_GTIN_REASON",
                    "value_name": "No aplica",
                    "allowed_values_json": '[{"id": "17055160", "name": "No aplica"}]',
                },
            ])

        with self.assertRaisesRegex(UserError, "no es válido"):
            self.publication_line._gtin_submission_state([
                {
                    "id": "EMPTY_GTIN_REASON",
                    "value_id": "invalid",
                    "allowed_values_json": '[{"id": "17055160", "name": "No aplica"}]',
                },
            ])

    def test_gtin_and_empty_reason_cannot_be_sent_together(self):
        with self.assertRaisesRegex(UserError, "pero no ambos"):
            self.publication_line._gtin_submission_state([
                {"id": "GTIN", "value_name": "7790001000018"},
                {
                    "id": "EMPTY_GTIN_REASON",
                    "value_id": "17055160",
                    "allowed_values_json": '[{"id": "17055160", "name": "No aplica"}]',
                },
            ])

    def test_category_without_gtin_attributes_does_not_require_a_value(self):
        state = self.publication_line._gtin_submission_state([])

        self.assertEqual(state, {"has_gtin": False, "has_reason": False})
