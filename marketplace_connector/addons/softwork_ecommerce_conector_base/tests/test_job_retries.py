import json

from odoo.tests import TransactionCase, tagged


@tagged("-at_install", "post_install")
class TestSceJobRetries(TransactionCase):
    def test_partial_result_is_not_reported_as_success(self):
        job_model = self.env["sce.job"]

        self.assertEqual(job_model._get_result_state({"ok": True}), "done")
        self.assertEqual(
            job_model._get_result_state(
                {"ok": False, "partial": True, "manual_retry_count": 2}
            ),
            "partial",
        )

    def test_manual_order_retries_are_preserved_and_reset(self):
        job_model = self.env["sce.job"]
        retry_payload = job_model._reset_import_order_retries(
            json.dumps(
                {
                    "offset": 250,
                    "failed_orders": {"first-order": 2},
                    "manual_retry_orders": {"last-order": 3},
                }
            )
        )

        self.assertEqual(
            json.loads(retry_payload),
            {
                "offset": 250,
                "failed_orders": {"first-order": 0, "last-order": 0},
            },
        )

    def test_retry_summary_does_not_persist_order_identifiers(self):
        summary = self.env["sce.job"]._summarize_result(
            {
                "ok": False,
                "manual_retry_count": 1,
                "manual_retry_orders": {"sensitive-order-id": 3},
            }
        )

        self.assertEqual(summary["manual_retry_count"], 1)
        self.assertNotIn("manual_retry_orders", summary)
