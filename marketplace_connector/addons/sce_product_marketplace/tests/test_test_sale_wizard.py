from odoo.tests import TransactionCase, tagged


@tagged("-at_install", "post_install")
class TestSceMlTestSaleWizard(TransactionCase):
    def test_order_match_requires_buyer_and_publication(self):
        wizard = self.env["sce.ml.test.sale.wizard"]
        orders = [
            {
                "id": 1,
                "buyer": {"id": 11},
                "order_items": [{"item": {"id": "item-a"}}],
            },
            {
                "id": 2,
                "buyer": {"id": 22},
                "order_items": [{"item": {"id": "item-a"}}],
            },
            {
                "id": 3,
                "buyer": {"id": 11},
                "order_items": [{"item": {"id": "item-b"}}],
            },
        ]

        self.assertFalse(wizard._find_matching_order(orders, "11", "item-c"))
        self.assertEqual(
            wizard._find_matching_order(orders, "22", "item-a")["id"], 2
        )
        self.assertEqual(
            wizard._find_matching_order(orders, "11", "item-a")["id"], 1
        )

    def test_match_ignores_malformed_order_rows(self):
        wizard = self.env["sce.ml.test.sale.wizard"]

        self.assertFalse(
            wizard._find_matching_order(
                [None, {"buyer": [], "order_items": [False]}, {"id": 4}],
                "buyer-id",
                "item-id",
            )
        )
