from odoo.tests import TransactionCase, tagged


@tagged("-at_install", "post_install")
class TestMarketplaceOrderRetries(TransactionCase):
    def test_order_failures_retry_automatically_three_times(self):
        service = self.env["marketplace.publication.service"]

        self.assertEqual(service._order_retry_bucket("order-1", 0), ("automatic", 1))
        self.assertEqual(service._order_retry_bucket("order-1", 1), ("automatic", 2))
        self.assertEqual(service._order_retry_bucket("order-1", 2), ("automatic", 3))

    def test_exhausted_order_becomes_manually_recoverable(self):
        service = self.env["marketplace.publication.service"]

        self.assertEqual(service._order_retry_bucket("order-1", 3), ("manual", 3))
