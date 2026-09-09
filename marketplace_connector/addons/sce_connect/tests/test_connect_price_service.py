import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from odoo.exceptions import UserError

from odoo.addons.sce_connector_ml.services.ml_provider import MercadoLibreProvider

from ..models.sce_connect_marketplace_mapping import SceConnectMarketplaceMapping
from ..services.connect_price_service import SceConnectPriceService


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


def mapping(item_id="ML123", variation_id=False):
    tenant = Record(id=2)
    connection = Record(id=5, tenant_id=tenant)
    product = Record(id=11, external_id=321, external_connection_id=connection, external_model="product.product")
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
        last_price_source=False,
        last_price_sent=False,
        last_price_sync_at=False,
        last_price_error=False,
    )


class MappingSet(list):
    def search(self, _domain):
        return self


class ConnectPriceServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = MagicMock(spec=SceConnectPriceService)
        self.service.env = {"sce.job": MagicMock(), "sce.connect.marketplace.mapping": MappingSet()}
        self.service.SOURCE_FIELD = SceConnectPriceService.SOURCE_FIELD
        self.service._validate_mapping = SceConnectPriceService._validate_mapping.__get__(self.service)
        self.service._remote_price = SceConnectPriceService._remote_price.__get__(self.service)
        self.service._read_item = SceConnectPriceService._read_item.__get__(self.service)
        self.service._item_mappings = SceConnectPriceService._item_mappings.__get__(self.service)
        self.service._provider_payload = SceConnectPriceService._provider_payload.__get__(self.service)
        self.service.sync_mapping = SceConnectPriceService.sync_mapping.__get__(self.service)
        self.service.enqueue_mapping = SceConnectPriceService.enqueue_mapping.__get__(self.service)
        self.service.calculate_price = SceConnectPriceService.calculate_price

    @patch("odoo.addons.sce_connect.services.connect_price_service.ProviderFactory")
    @patch("odoo.addons.sce_connect.services.connect_price_service.ConnectionService")
    def test_simple_price_uses_list_price_and_minimal_payload(self, connection_service_cls, factory):
        record = mapping()
        connection_service_cls.return_value.remote_product_context.return_value = {"company_id": 10, "allowed_company_ids": [10]}
        connection_service_cls.return_value.metadata.return_value = {"id": {}, "list_price": {}}
        connection_service_cls.return_value.search_read.return_value = [{"id": 321, "list_price": 15000}]
        factory.get_provider.return_value.update_price.return_value = {"ok": True}
        factory.get_provider.return_value.get_item.return_value = {"item": {"id": "ML123"}}

        result = self.service.sync_mapping(record)

        factory.get_provider.return_value.update_price.assert_called_once_with(
            {"item_id": "ML123", "price": 15000.0}
        )
        self.assertEqual(result["source_price"], "15000.00")
        self.assertEqual(record.last_price_sent, "15000.00")
        self.assertEqual(
            connection_service_cls.return_value.search_read.call_args.kwargs["context"],
            {"company_id": 10, "allowed_company_ids": [10]},
        )

    @patch("odoo.addons.sce_connect.services.connect_price_service.ProviderFactory")
    @patch("odoo.addons.sce_connect.services.connect_price_service.ConnectionService")
    def test_variant_price_uses_variation_payload(self, connection_service_cls, factory):
        record = mapping(variation_id="ML456")
        connection_service_cls.return_value.remote_product_context.return_value = None
        connection_service_cls.return_value.metadata.return_value = {"list_price": {}}
        connection_service_cls.return_value.search_read.return_value = [{"list_price": 15000.5}]
        factory.get_provider.return_value.update_price.return_value = {"ok": True}
        factory.get_provider.return_value.get_item.return_value = {
            "item": {"id": "ML123", "variations": [{"id": "ML456"}]}
        }
        self.service.env["sce.connect.marketplace.mapping"].append(record)

        self.service.sync_mapping(record)

        factory.get_provider.return_value.update_price.assert_called_once_with(
            {"item_id": "ML123", "variation_prices": [{"id": "ML456", "price": 15000.5}]}
        )

    @patch("odoo.addons.sce_connect.services.connect_price_service.ProviderFactory")
    @patch("odoo.addons.sce_connect.services.connect_price_service.ConnectionService")
    def test_variant_price_sends_all_variations_with_common_price(self, connection_service_cls, factory):
        records = [mapping(variation_id=value) for value in ("A", "B", "C")]
        connection_service_cls.return_value.remote_product_context.return_value = None
        connection_service_cls.return_value.metadata.return_value = {"list_price": {}}
        connection_service_cls.return_value.search_read.side_effect = [
            [{"list_price": 15000}], [{"list_price": 15000}], [{"list_price": 15000}]
        ]
        factory.get_provider.return_value.get_item.return_value = {
            "item": {"id": "ML123", "variations": [{"id": "A"}, {"id": "B"}, {"id": "C"}]}
        }
        factory.get_provider.return_value.update_price.return_value = {"ok": True}
        self.service.env["sce.connect.marketplace.mapping"].extend(records)

        self.service.sync_mapping(records[0])

        factory.get_provider.return_value.update_price.assert_called_once_with(
            {
                "item_id": "ML123",
                "variation_prices": [
                    {"id": "A", "price": 15000.0},
                    {"id": "B", "price": 15000.0},
                    {"id": "C", "price": 15000.0},
                ],
            }
        )

    @patch("odoo.addons.sce_connect.services.connect_price_service.ProviderFactory")
    @patch("odoo.addons.sce_connect.services.connect_price_service.ConnectionService")
    def test_variant_different_prices_are_non_retryable_validation_error(self, connection_service_cls, factory):
        records = [mapping(variation_id=value) for value in ("A", "B", "C")]
        connection_service_cls.return_value.remote_product_context.return_value = None
        connection_service_cls.return_value.metadata.return_value = {"list_price": {}}
        connection_service_cls.return_value.search_read.side_effect = [
            [{"list_price": 10000}], [{"list_price": 12000}], [{"list_price": 10000}]
        ]
        factory.get_provider.return_value.get_item.return_value = {
            "item": {"id": "ML123", "variations": [{"id": "A"}, {"id": "B"}, {"id": "C"}]}
        }
        self.service.env["sce.connect.marketplace.mapping"].extend(records)

        with self.assertRaisesRegex(UserError, "precio común"):
            self.service.sync_mapping(records[0])

        factory.get_provider.return_value.update_price.assert_not_called()

    @patch("odoo.addons.sce_connect.services.connect_price_service.ProviderFactory")
    @patch("odoo.addons.sce_connect.services.connect_price_service.ConnectionService")
    def test_missing_ml_variation_mapping_is_rejected_without_put(self, connection_service_cls, factory):
        records = [mapping(variation_id=value) for value in ("A", "B")]
        connection_service_cls.return_value.remote_product_context.return_value = None
        connection_service_cls.return_value.metadata.return_value = {"list_price": {}}
        factory.get_provider.return_value.get_item.return_value = {
            "item": {"id": "ML123", "variations": [{"id": "A"}, {"id": "B"}, {"id": "C"}]}
        }
        self.service.env["sce.connect.marketplace.mapping"].extend(records)

        with self.assertRaisesRegex(UserError, "discrepancia"):
            self.service.sync_mapping(records[0])

        factory.get_provider.return_value.update_price.assert_not_called()

    @patch("odoo.addons.sce_connect.services.connect_price_service.ProviderFactory")
    @patch("odoo.addons.sce_connect.services.connect_price_service.ConnectionService")
    def test_extra_mapping_variation_is_rejected_without_put(self, connection_service_cls, factory):
        records = [mapping(variation_id=value) for value in ("A", "B", "C")]
        connection_service_cls.return_value.remote_product_context.return_value = None
        connection_service_cls.return_value.metadata.return_value = {"list_price": {}}
        factory.get_provider.return_value.get_item.return_value = {
            "item": {"id": "ML123", "variations": [{"id": "A"}, {"id": "B"}]}
        }
        self.service.env["sce.connect.marketplace.mapping"].extend(records)

        with self.assertRaisesRegex(UserError, "discrepancia"):
            self.service.sync_mapping(records[0])

        factory.get_provider.return_value.update_price.assert_not_called()

    @patch("odoo.addons.sce_connect.services.connect_price_service.ProviderFactory")
    @patch("odoo.addons.sce_connect.services.connect_price_service.ConnectionService")
    def test_duplicate_ml_variation_id_is_rejected_without_put(self, connection_service_cls, factory):
        records = [mapping(variation_id=value) for value in ("A", "B")]
        connection_service_cls.return_value.remote_product_context.return_value = None
        factory.get_provider.return_value.get_item.return_value = {
            "item": {"id": "ML123", "variations": [{"id": "A"}, {"id": "B"}, {"id": "B"}]}
        }
        self.service.env["sce.connect.marketplace.mapping"].extend(records)

        with self.assertRaisesRegex(UserError, "duplicados"):
            self.service.sync_mapping(records[0])

        factory.get_provider.return_value.update_price.assert_not_called()

    @patch("odoo.addons.sce_connect.services.connect_price_service.ProviderFactory")
    @patch("odoo.addons.sce_connect.services.connect_price_service.ConnectionService")
    def test_duplicate_mapping_variation_id_is_rejected_without_put(self, connection_service_cls, factory):
        records = [mapping(variation_id=value) for value in ("A", "B", "B")]
        connection_service_cls.return_value.remote_product_context.return_value = None
        factory.get_provider.return_value.get_item.return_value = {
            "item": {"id": "ML123", "variations": [{"id": "A"}, {"id": "B"}]}
        }
        self.service.env["sce.connect.marketplace.mapping"].extend(records)

        with self.assertRaisesRegex(UserError, "duplicados"):
            self.service.sync_mapping(records[0])

        factory.get_provider.return_value.update_price.assert_not_called()

    @patch("odoo.addons.sce_connect.services.connect_price_service.ProviderFactory")
    @patch("odoo.addons.sce_connect.services.connect_price_service.ConnectionService")
    def test_price_automation_is_controlled_error_without_update(self, connection_service_cls, factory):
        record = mapping()
        connection_service_cls.return_value.remote_product_context.return_value = None
        factory.get_provider.return_value.get_item.return_value = {
            "item": {"id": "ML123", "price_automation_active": True}
        }

        with self.assertRaisesRegex(UserError, "PRICE_AUTOMATION_ACTIVE"):
            self.service.sync_mapping(record)

        factory.get_provider.return_value.update_price.assert_not_called()

    def test_decimal_calculator_rejects_invalid_prices(self):
        self.assertEqual(SceConnectPriceService.calculate_price("15000.505"), self.service.calculate_price("15000.505"))
        for value in (None, 0, -1, "nan", "inf", "invalid"):
            with self.assertRaises(UserError):
                SceConnectPriceService.calculate_price(value)

    @patch("odoo.addons.sce_connect.services.connect_price_service.ProviderFactory")
    @patch("odoo.addons.sce_connect.services.connect_price_service.ConnectionService")
    def test_same_price_is_skipped(self, connection_service_cls, factory):
        record = mapping()
        record.last_price_source = "15000.00"
        record.last_price_sent = "15000.00"
        record.last_price_sync_at = datetime(2026, 1, 1)
        connection_service_cls.return_value.remote_product_context.return_value = None
        connection_service_cls.return_value.metadata.return_value = {"list_price": {}}
        connection_service_cls.return_value.search_read.return_value = [{"list_price": 15000}]
        factory.get_provider.return_value.get_item.return_value = {"item": {"id": "ML123"}}

        result = self.service.sync_mapping(record)

        self.assertTrue(result["skipped"])
        factory.get_provider.return_value.update_price.assert_not_called()

    def test_missing_item_is_rejected(self):
        with self.assertRaises(UserError):
            self.service.sync_mapping(mapping(item_id=False))

    @patch("odoo.addons.sce_connect.services.connect_price_service.ConnectionService")
    def test_invalid_price_does_not_call_provider(self, connection_service_cls):
        record = mapping()
        connection_service_cls.return_value.remote_product_context.return_value = None
        connection_service_cls.return_value.metadata.return_value = {"list_price": {}}
        connection_service_cls.return_value.search_read.return_value = [{"list_price": 0}]
        provider = MagicMock()
        provider.get_item.return_value = {"item": {"id": "ML123"}}
        with patch("odoo.addons.sce_connect.services.connect_price_service.ProviderFactory.get_provider", return_value=provider):
            with self.assertRaises(UserError):
                self.service.sync_mapping(record)
        provider.update_price.assert_not_called()

    @patch("odoo.addons.sce_connect.services.connect_price_service.ProviderFactory")
    @patch("odoo.addons.sce_connect.services.connect_price_service.ConnectionService")
    def test_job_enqueue_is_deduplicated(self, connection_service_cls, factory):
        record = mapping()
        pending = Record(id=99)
        self.service.env["sce.job"].search.return_value = pending

        result = self.service.enqueue_mapping(record)

        self.assertEqual(result, pending)
        self.service.env["sce.job"].create.assert_not_called()

    def test_no_publication_or_stock_dependency_in_price_service(self):
        names = SceConnectPriceService.sync_mapping.__code__.co_names
        self.assertNotIn("marketplace.publication", names)
        self.assertNotIn("update_stock", names)
        self.assertNotIn("publish_product", names)

    def test_provider_simple_and_variant_endpoint_payloads(self):
        provider = MercadoLibreProvider(MagicMock(), MagicMock())
        provider._request = MagicMock(return_value={"id": "ML123"})

        provider.update_price({"item_id": "ML123", "price": 15000})
        with self.assertRaises(UserError):
            provider.update_price({"item_id": "ML123", "variation_id": "ML456", "price": 15000.5})
        provider.update_price(
            {
                "item_id": "ML123",
                "variation_prices": [
                    {"id": "A", "price": 15000.5},
                    {"id": "B", "price": 15000.5},
                    {"id": "C", "price": 15000.5},
                ],
            }
        )

        self.assertEqual(
            provider._request.call_args_list[0].args,
            ("PUT", "/items/ML123"),
        )
        self.assertEqual(
            provider._request.call_args_list[0].kwargs["payload"],
            {"price": 15000.0},
        )
        self.assertEqual(
            provider._request.call_args_list[1].kwargs["payload"],
            {"variations": [{"id": "A", "price": 15000.5}, {"id": "B", "price": 15000.5}, {"id": "C", "price": 15000.5}]},
        )


class ConnectPriceJobTests(unittest.TestCase):
    def test_job_source_declares_connect_price(self):
        source = open(
            "marketplace_connector/addons/sce_connect/models/sce_connect_price_job.py",
            encoding="utf-8",
        ).read()
        self.assertIn("sync_connect_price", source)
        self.assertIn("connect_marketplace_mapping_id", source)


if __name__ == "__main__":
    unittest.main()
