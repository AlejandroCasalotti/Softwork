import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from odoo.exceptions import UserError

from odoo.addons.sce_connector_ml.services.ml_provider import MercadoLibreProvider

from ..models.sce_connect_marketplace_mapping import SceConnectMarketplaceMapping
from ..services.connect_stock_service import SceConnectStockService


class Record:
    def __init__(self, **values):
        self.__dict__.update(values)
        self.id = values.get("id", 1)

    def exists(self):
        return True

    def ensure_one(self):
        return self

    def write(self, values):
        self.__dict__.update(values)
        return True

    def __eq__(self, other):
        return isinstance(other, Record) and self.id == other.id

    def _check_identity_scope(self):
        return True


def mapping(item_id="ML123", variation_id=False, free_qty=15):
    tenant = Record(id=2)
    connection = Record(id=5, tenant_id=tenant)
    product = Record(
        id=11,
        external_id=321,
        external_connection_id=connection,
        external_model="product.product",
        default_code="SKU-11",
        barcode=False,
        active=True,
    )
    account = Record(id=8, provider_type="mercadolibre")
    return Record(
        id=20,
        active=True,
        mapping_status="verified",
        marketplace_item_id=item_id,
        marketplace_variation_id=variation_id,
        external_connection_id=connection,
        external_product_mapping_id=product,
        marketplace_account_id=account,
        tenant_id=tenant,
        last_stock_source=0,
        last_stock_sent=0,
        last_stock_sync_at=False,
        last_stock_error=False,
        free_qty=free_qty,
    )


class ConnectStockServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = MagicMock(spec=SceConnectStockService)
        rule_engine = MagicMock()
        rule_engine.evaluate.side_effect = lambda _tenant, _scope, context: {
            "allowed": True,
            "value": context.get("stock"),
            "actions": [],
            "matched_rules": [],
        }
        self.service.env = {"sce.job": MagicMock(), "sce.connect.rule.engine": rule_engine}
        self.service.SOURCE_FIELD = SceConnectStockService.SOURCE_FIELD
        self.service._validate_mapping = SceConnectStockService._validate_mapping.__get__(self.service)
        self.service._remote_stock = SceConnectStockService._remote_stock.__get__(self.service)
        self.service._provider_payload = SceConnectStockService._provider_payload.__get__(self.service)
        self.service._active_policy = SceConnectStockService._active_policy.__get__(self.service)
        self.service._apply_policy = SceConnectStockService._apply_policy.__get__(self.service)
        self.service._reserve_label = SceConnectStockService._reserve_label
        self.service._apply_rules = SceConnectStockService._apply_rules.__get__(self.service)
        self.service.sync_mapping = SceConnectStockService.sync_mapping.__get__(self.service)
        self.service.enqueue_mapping = SceConnectStockService.enqueue_mapping.__get__(self.service)

    @patch("odoo.addons.sce_connect.services.connect_stock_service.ProviderFactory")
    @patch("odoo.addons.sce_connect.services.connect_stock_service.ConnectionService")
    def test_simple_product_uses_free_qty_and_item_payload(self, connection_service_cls, factory):
        record = mapping(free_qty=15)
        connection_service = connection_service_cls.return_value
        connection_service.remote_product_context.return_value = {"company_id": 10, "allowed_company_ids": [10]}
        connection_service.metadata.return_value = {"id": {}, "free_qty": {}}
        connection_service.search_read.return_value = [{"id": 321, "free_qty": 15}]
        provider = factory.get_provider.return_value
        provider.update_stock.return_value = {"ok": True, "item_id": "ML123"}

        result = self.service.sync_mapping(record)

        provider.update_stock.assert_called_once_with({"item_id": "ML123", "available_quantity": 15})
        self.assertEqual(result["source_stock"], 15)
        self.assertEqual(record.last_stock_sent, 15)
        self.assertEqual(record.last_stock_source, 15)
        self.assertIsNotNone(record.last_stock_sync_at)
        connection_service.remote_product_context.assert_called_once_with()
        connection_service.search_read.assert_called_once_with(
            "product.product",
            domain=[("id", "=", 321)],
            fields=["id", "free_qty"],
            limit=1,
            context={"company_id": 10, "allowed_company_ids": [10]},
        )

    @patch("odoo.addons.sce_connect.services.connect_stock_service.ProviderFactory")
    @patch("odoo.addons.sce_connect.services.connect_stock_service.ConnectionService")
    def test_variant_uses_variation_id_and_same_remote_context(self, connection_service_cls, factory):
        record = mapping(variation_id="ML456", free_qty=7)
        connection_service_cls.return_value.remote_product_context.return_value = None
        connection_service_cls.return_value.metadata.return_value = {"free_qty": {}}
        connection_service_cls.return_value.search_read.return_value = [{"free_qty": 7}]
        factory.get_provider.return_value.update_stock.return_value = {"ok": True}

        self.service.sync_mapping(record)

        factory.get_provider.return_value.update_stock.assert_called_once_with(
            {"item_id": "ML123", "variation_id": "ML456", "available_quantity": 7}
        )
        self.assertIsNone(connection_service_cls.return_value.search_read.call_args.kwargs["context"])

    @patch("odoo.addons.sce_connect.services.connect_stock_service.ConnectionService")
    def test_negative_remote_stock_is_clamped_to_zero(self, connection_service_cls):
        record = mapping(free_qty=-4)
        connection_service_cls.return_value.remote_product_context.return_value = None
        connection_service_cls.return_value.metadata.return_value = {"free_qty": {}}
        connection_service_cls.return_value.search_read.return_value = [{"free_qty": -4}]
        provider = MagicMock()
        with patch("odoo.addons.sce_connect.services.connect_stock_service.ProviderFactory.get_provider", return_value=provider):
            provider.update_stock.return_value = {"ok": True}
            result = self.service.sync_mapping(record)

        self.assertEqual(result["available_quantity"], 0)
        provider.update_stock.assert_called_once_with({"item_id": "ML123", "available_quantity": 0})

    @patch("odoo.addons.sce_connect.services.connect_stock_service.ConnectionService")
    def test_same_stock_is_skipped_without_provider_call(self, connection_service_cls):
        record = mapping(free_qty=15)
        record.last_stock_source = 15
        record.last_stock_sent = 15
        record.last_stock_sync_at = datetime(2026, 1, 1)
        connection_service_cls.return_value.remote_product_context.return_value = None
        connection_service_cls.return_value.metadata.return_value = {"free_qty": {}}
        connection_service_cls.return_value.search_read.return_value = [{"free_qty": 15}]
        provider = MagicMock()
        with patch("odoo.addons.sce_connect.services.connect_stock_service.ProviderFactory.get_provider", return_value=provider):
            result = self.service.sync_mapping(record)

        self.assertTrue(result["skipped"])
        provider.update_stock.assert_not_called()

    @patch("odoo.addons.sce_connect.services.connect_stock_service.ProviderFactory")
    @patch("odoo.addons.sce_connect.services.connect_stock_service.ConnectionService")
    def test_rule_block_prevents_stock_put(self, connection_service_cls, factory):
        record = mapping(free_qty=2)
        connection_service_cls.return_value.remote_product_context.return_value = None
        connection_service_cls.return_value.metadata.return_value = {"free_qty": {}}
        connection_service_cls.return_value.search_read.return_value = [{"free_qty": 2}]
        self.service.env["sce.connect.rule.engine"].evaluate.side_effect = None
        self.service.env["sce.connect.rule.engine"].evaluate.return_value = {
            "allowed": False, "blocked_by": 15, "value": None, "actions": []
        }

        result = self.service.sync_mapping(record)

        self.assertTrue(result["blocked"])
        factory.get_provider.assert_not_called()
        self.assertIn("15", record.last_stock_error)

    @patch("odoo.addons.sce_connect.services.connect_stock_service.ProviderFactory")
    @patch("odoo.addons.sce_connect.services.connect_stock_service.ConnectionService")
    def test_rule_transform_changes_stock_before_put(self, connection_service_cls, factory):
        record = mapping(free_qty=10)
        connection_service_cls.return_value.remote_product_context.return_value = None
        connection_service_cls.return_value.metadata.return_value = {"free_qty": {}}
        connection_service_cls.return_value.search_read.return_value = [{"free_qty": 10}]
        self.service.env["sce.connect.rule.engine"].evaluate.side_effect = None
        self.service.env["sce.connect.rule.engine"].evaluate.return_value = {
            "allowed": True, "value": "5.00", "actions": [{"action": "multiply"}]
        }
        factory.get_provider.return_value.update_stock.return_value = {"ok": True}

        self.service.sync_mapping(record)

        factory.get_provider.return_value.update_stock.assert_called_once_with(
            {"item_id": "ML123", "available_quantity": 5}
        )

    def test_missing_item_is_rejected_without_provider(self):
        record = mapping(item_id=False)
        with self.assertRaises(UserError):
            self.service.sync_mapping(record)

    def test_inactive_or_unverified_mapping_is_rejected(self):
        record = mapping()
        record.mapping_status = "draft"
        with self.assertRaises(UserError):
            self.service.sync_mapping(record)

    @patch("odoo.addons.sce_connect.services.connect_stock_service.ProviderFactory")
    @patch("odoo.addons.sce_connect.services.connect_stock_service.ConnectionService")
    def test_provider_error_is_recorded_without_credentials(self, connection_service_cls, factory):
        record = mapping()
        connection_service_cls.return_value.remote_product_context.return_value = None
        connection_service_cls.return_value.metadata.return_value = {"free_qty": {}}
        connection_service_cls.return_value.search_read.return_value = [{"free_qty": 3}]
        factory.get_provider.return_value.update_stock.side_effect = UserError("HTTP 429")

        with self.assertRaises(UserError):
            self.service.sync_mapping(record)

        self.assertIn("HTTP 429", record.last_stock_error)
        self.assertNotIn("token", record.last_stock_error.lower())

    def test_enqueue_deduplicates_queued_jobs(self):
        record = mapping()
        pending = Record(id=99)
        self.service.env["sce.job"].search.return_value = pending

        result = self.service.enqueue_mapping(record)

        self.assertEqual(result, pending)
        self.service.env["sce.job"].create.assert_not_called()

    def test_enqueue_requires_existing_item(self):
        record = mapping(item_id=False)
        with self.assertRaises(UserError):
            self.service.enqueue_mapping(record)

    def test_no_publication_model_or_create_endpoint_is_used(self):
        names = SceConnectStockService.sync_mapping.__code__.co_names
        self.assertNotIn("marketplace.publication", names)
        self.assertNotIn("publish_product", names)
        self.assertNotIn("create", names)

    def test_cron_enqueues_only_verified_active_mappings(self):
        model = MagicMock()
        verified = Record(id=1)
        verified._has_syncable_connect_account = MagicMock(return_value=True)
        blocked = Record(id=2)
        blocked._has_syncable_connect_account = MagicMock(return_value=False)
        model.search.return_value = [verified, blocked]
        service = MagicMock()
        model.env.__getitem__.return_value = service

        SceConnectMarketplaceMapping.cron_enqueue_stock_sync(model)

        model.search.assert_called_once_with(
            [
                ("active", "=", True),
                ("mapping_status", "=", "verified"),
                ("marketplace_item_id", "!=", False),
            ],
            limit=100,
            order="id asc",
        )
        service.enqueue_mapping.assert_called_once_with(verified)
        blocked._has_syncable_connect_account.assert_called_once_with()

    def test_provider_simple_uses_item_endpoint_only(self):
        provider = MercadoLibreProvider(MagicMock(), MagicMock())
        provider._request = MagicMock(return_value={"id": "ML123"})

        provider.update_stock({"item_id": "ML123", "available_quantity": 15})

        provider._request.assert_called_once_with(
            "PUT", "/items/ML123", payload={"available_quantity": 15}
        )

    def test_provider_variant_uses_item_endpoint_with_only_variation_stock(self):
        provider = MercadoLibreProvider(MagicMock(), MagicMock())
        provider._request = MagicMock(return_value={"id": "ML123"})

        provider.update_stock(
            {"item_id": "ML123", "variation_id": "456", "available_quantity": 15}
        )

        provider._request.assert_called_once_with(
            "PUT",
            "/items/ML123",
            payload={"variations": [{"id": "456", "available_quantity": 15}]},
        )


class ConnectStockJobTests(unittest.TestCase):
    def test_job_model_declares_connect_stock_operation(self):
        source = open(
            "marketplace_connector/addons/sce_connect/models/sce_connect_job.py",
            encoding="utf-8",
        ).read()
        self.assertIn("sync_connect_stock", source)
        self.assertIn("connect_marketplace_mapping_id", source)


if __name__ == "__main__":
    unittest.main()
