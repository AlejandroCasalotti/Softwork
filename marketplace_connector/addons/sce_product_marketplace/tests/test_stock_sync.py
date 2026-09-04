# -*- coding: utf-8 -*-
import unittest
from unittest.mock import MagicMock

from odoo.exceptions import UserError

from odoo.addons.sce_connector_ml.services.ml_provider import MercadoLibreProvider
from odoo.addons.sce_connector_ml.services.provider import MercadoLibreExternalProvider
from odoo.addons.softwork_ecommerce_conector_base.models.sce_job import SceJob
from odoo.addons.softwork_ecommerce_conector_base.services.providers.ml_provider import (
    MercadoLibreProvider as LegacyMercadoLibreProvider,
)
from odoo.addons.softwork_provider_mercadolibre.services.provider import (
    MercadoLibreExternalProvider as LegacyMercadoLibreExternalProvider,
)

from ..models.marketplace_publication import MarketplacePublication
from ..models.sce_job_marketplace import SceMarketplaceJob
from ..services.publication_service import MarketplacePublicationService


class _CronConfig:
    def __init__(self):
        self.values = {}

    def sudo(self):
        return self

    def get_param(self, key, default=None):
        return self.values.get(key, default)

    def set_param(self, key, value):
        self.values[key] = str(value)


class _CronRecordset(list):
    @property
    def ids(self):
        return [record.id for record in self]


class _CronPublicationModel:
    def __init__(self, ids, config, service):
        self.records = [MagicMock(id=record_id) for record_id in ids]
        self._STOCK_CRON_CURSOR_PARAM = MarketplacePublication._STOCK_CRON_CURSOR_PARAM
        self.env = {
            "ir.config_parameter": config,
            "marketplace.publication.service": service,
        }
        self.search_calls = []

    def search(self, domain, limit, order):
        self.search_calls.append((domain, limit, order))
        last_id = next(value for field, operator, value in domain if field == "id" and operator == ">")
        return _CronRecordset([record for record in self.records if record.id > last_id][:limit])


class MercadoLibreStockProviderTests(unittest.TestCase):
    def setUp(self):
        self.account = MagicMock()
        self.provider = MercadoLibreProvider(MagicMock(), self.account)
        self.provider._request = MagicMock(return_value={"id": "MLA123"})
        self.legacy_provider = LegacyMercadoLibreProvider(MagicMock(), self.account)
        self.legacy_provider._request = MagicMock(return_value={"id": "MLA123"})

    def test_simple_stock_uses_item_endpoint_and_preserves_raw_response(self):
        raw = {"id": "MLA123", "available_quantity": 7}
        self.provider._request.return_value = raw

        result = self.provider.update_stock({"item_id": "MLA123", "available_quantity": 7})

        self.provider._request.assert_called_once_with(
            "PUT", "/items/MLA123", payload={"available_quantity": 7}
        )
        self.assertEqual(result["raw"], raw)
        self.assertFalse(result["variation_id"])

    def test_variant_stock_uses_variation_endpoint(self):
        result = self.provider.update_stock(
            {"item_id": "MLA123", "variation_id": "987654321", "available_quantity": 7}
        )

        self.provider._request.assert_called_once_with(
            "PUT", "/items/MLA123/variations/987654321", payload={"available_quantity": 7}
        )
        self.assertEqual(result["variation_id"], "987654321")

    def test_zero_stock_is_sent_as_zero(self):
        self.provider.update_stock({"item_id": "MLA123", "available_quantity": 0})

        self.provider._request.assert_called_once_with(
            "PUT", "/items/MLA123", payload={"available_quantity": 0}
        )

    def test_legacy_provider_uses_the_same_variant_endpoint(self):
        result = self.legacy_provider.update_stock(
            {"item_id": "MLA123", "variation_id": "987654321", "available_quantity": 4}
        )

        self.legacy_provider._request.assert_called_once_with(
            "PUT", "/items/MLA123/variations/987654321", payload={"available_quantity": 4}
        )
        self.assertEqual(result["available_quantity"], 4)

    def test_both_facades_preserve_update_stock_result(self):
        payload = {"item_id": "MLA123", "available_quantity": 7}
        expected = {"ok": True, "raw": {"id": "MLA123"}}
        for facade_class in (MercadoLibreExternalProvider, LegacyMercadoLibreExternalProvider):
            facade = facade_class(MagicMock(), self.account)
            facade._delegate = MagicMock()
            facade._delegate.update_stock.return_value = expected

            self.assertIs(facade.update_stock(payload), expected)
            facade._delegate.update_stock.assert_called_once_with(payload)


class MarketplaceStockSyncTests(unittest.TestCase):
    def _service(self, provider):
        service = MagicMock(spec=MarketplacePublicationService)
        service.update_stock = MarketplacePublicationService.update_stock.__get__(service)
        service.enqueue = MarketplacePublicationService.enqueue.__get__(service)
        service._get_provider.return_value = provider
        return service

    @staticmethod
    def _publication(external_id="MLA123", variants=1):
        publication = MagicMock()
        publication.id = 1
        publication.display_name = "Publication"
        publication.external_id = external_id
        publication.account_id.id = 10
        publication.account_id.company_id = MagicMock()
        publication.last_stock_sent = 0
        publication.last_stock_sync_at = False
        publication.effective_qty = 7
        publication._stock_variant_mappings.return_value = []
        publication._stock_quantity.return_value = 7
        publication.product_tmpl_id.product_variant_ids.filtered.return_value = [MagicMock()] * variants
        return publication

    def test_simple_publication_sends_effective_quantity(self):
        publication = self._publication()
        provider = MagicMock(return_value={})
        provider.update_stock.return_value = {"ok": True, "raw": {"id": "MLA123"}}
        service = self._service(provider)

        result = service.update_stock(publication)

        self.assertTrue(result["ok"])
        provider.update_stock.assert_called_once_with(
            {"item_id": "MLA123", "available_quantity": 7}
        )
        self.assertEqual(publication.write.call_count, 2)
        self.assertEqual(publication.write.call_args_list[0].args[0]["last_stock_sent"], 7)
        self.assertIn("sync_date", publication.write.call_args_list[1].args[0])

    def test_variant_sends_only_its_mapping_and_quantity(self):
        publication = self._publication(variants=2)
        mapping = MagicMock()
        mapping.publication_id = publication
        mapping.external_id = "MLA123"
        mapping.external_variant_id = "987654321"
        mapping.last_stock_sent = 0
        mapping.last_stock_sync_at = False
        publication._stock_quantity.return_value = 7
        provider = MagicMock()
        provider.update_stock.return_value = {"ok": True}
        service = self._service(provider)

        service.update_stock(publication, mapping=mapping)

        provider.update_stock.assert_called_once_with(
            {
                "item_id": "MLA123",
                "variation_id": "987654321",
                "available_quantity": 7,
            }
        )
        mapping.write.assert_called_once()

    def test_variant_publication_without_mapping_is_rejected(self):
        publication = self._publication(variants=2)
        service = self._service(MagicMock())

        with self.assertRaises(UserError):
            service.enqueue(publication, "update_stock")

    def test_publication_without_external_id_is_rejected(self):
        publication = self._publication(external_id=False)
        service = self._service(MagicMock())

        with self.assertRaises(UserError):
            service.update_stock(publication)

    def test_equal_stock_is_not_sent_again(self):
        publication = self._publication()
        publication.last_stock_sent = 7
        publication.last_stock_sync_at = "2026-01-01 00:00:00"
        provider = MagicMock()
        service = self._service(provider)

        result = service.update_stock(publication)

        self.assertTrue(result["skipped"])
        provider.update_stock.assert_not_called()

    def test_simple_and_variant_stock_history_are_independent(self):
        publication = self._publication()
        publication.last_stock_sent = 7
        publication.last_stock_sync_at = "2026-01-01 00:00:00"
        mapping = MagicMock()
        mapping.publication_id = publication
        mapping.external_id = "MLA123"
        mapping.external_variant_id = "987654321"
        mapping.last_stock_sent = 3
        mapping.last_stock_sync_at = "2026-01-01 00:00:00"
        publication._stock_quantity.return_value = 7
        provider = MagicMock()
        provider.update_stock.return_value = {"ok": True}
        service = self._service(provider)

        result = service.update_stock(publication, mapping=mapping)

        self.assertFalse(result.get("skipped"))
        provider.update_stock.assert_called_once()

    def test_variant_stock_uses_publication_account_company(self):
        publication = MagicMock()
        publication.ensure_one = MagicMock()
        company = MagicMock()
        publication.account_id.company_id = company
        product = MagicMock()
        product.with_company.return_value.qty_available = 9.8
        mapping = MagicMock()
        mapping.publication_id = publication
        mapping.product_id = product

        quantity = MarketplacePublication._stock_quantity(publication, mapping)

        self.assertEqual(quantity, 9)
        product.with_company.assert_called_once_with(company)

    def test_stock_cron_enqueues_without_calling_provider(self):
        config = _CronConfig()
        service = MagicMock()
        model = _CronPublicationModel([1], config, service)

        MarketplacePublication.cron_enqueue_stock_sync(model)

        service.enqueue.assert_called_once_with(model.records[0], "update_stock")


class MarketplaceStockCronPaginationTests(unittest.TestCase):
    def setUp(self):
        self.config = _CronConfig()
        self.service = MagicMock()

    def _run(self, ids):
        model = _CronPublicationModel(ids, self.config, self.service)
        MarketplacePublication.cron_enqueue_stock_sync(model)
        return model

    def test_first_page_uses_id_ascending_and_limit_100(self):
        model = self._run(range(1, 251))

        self.assertEqual([call.args[0].id for call in self.service.enqueue.call_args_list], list(range(1, 101)))
        domain, limit, order = model.search_calls[0]
        self.assertIn(("id", ">", 0), domain)
        self.assertEqual(limit, 100)
        self.assertEqual(order, "id asc")

    def test_catalog_of_250_is_processed_in_three_pages_then_rolls_over(self):
        pages = []
        for _index in range(3):
            self.service.reset_mock()
            self._run(range(1, 251))
            pages.append([call.args[0].id for call in self.service.enqueue.call_args_list])

        self.assertEqual(pages, [list(range(1, 101)), list(range(101, 201)), list(range(201, 251))])
        self.assertEqual(self.config.values[MarketplacePublication._STOCK_CRON_CURSOR_PARAM], "250")

        self.service.reset_mock()
        model = self._run(range(1, 251))
        self.assertEqual([call.args[0].id for call in self.service.enqueue.call_args_list], list(range(1, 101)))
        self.assertEqual(len(model.search_calls), 2)
        self.assertIn(("id", ">", 250), model.search_calls[0][0])
        self.assertIn(("id", ">", 0), model.search_calls[1][0])

    def test_new_publication_is_reached_before_rollover(self):
        self.config.values[MarketplacePublication._STOCK_CRON_CURSOR_PARAM] = "200"

        self._run(list(range(1, 251)) + [251])

        self.assertEqual(
            [call.args[0].id for call in self.service.enqueue.call_args_list],
            list(range(201, 252)),
        )

    def test_deleted_or_ineligible_ids_do_not_break_cursor_progression(self):
        self.config.values[MarketplacePublication._STOCK_CRON_CURSOR_PARAM] = "100"

        self._run(list(range(1, 101)) + list(range(201, 251)))

        self.assertEqual(
            [call.args[0].id for call in self.service.enqueue.call_args_list],
            list(range(201, 251)),
        )
        self.assertEqual(self.config.values[MarketplacePublication._STOCK_CRON_CURSOR_PARAM], "250")


class MarketplaceStockJobTests(unittest.TestCase):
    def test_variant_job_passes_mapping_to_publication_service(self):
        job = MagicMock(spec=SceMarketplaceJob)
        job.job_type = "sync_publication_stock"
        job.publication_id = MagicMock()
        job.mapping_id = MagicMock()
        service = MagicMock()
        job.env.__getitem__.return_value = service

        SceMarketplaceJob._execute_provider_operation(job, MagicMock(), {})

        service.update_stock.assert_called_once_with(job.publication_id, mapping=job.mapping_id)

    def test_existing_queued_job_is_reused(self):
        publication = MarketplaceStockSyncTests._publication()
        provider = MagicMock()
        service = MarketplaceStockSyncTests()._service(provider)
        existing_job = MagicMock()
        job_model = MagicMock()
        job_model.search.return_value = existing_job
        service.env.__getitem__.return_value = job_model

        result = service.enqueue(publication, "update_stock")

        self.assertIs(result, existing_job)
        job_model.create.assert_not_called()

    def test_existing_running_job_is_reused(self):
        publication = MarketplaceStockSyncTests._publication()
        service = MarketplaceStockSyncTests()._service(MagicMock())
        existing_job = MagicMock()
        job_model = MagicMock()
        job_model.search.return_value = existing_job
        service.env.__getitem__.return_value = job_model

        result = service.enqueue(publication, "update_stock")

        self.assertIs(result, existing_job)
        self.assertIn(("state", "in", ["queued", "running"]), job_model.search.call_args.args[0])
        job_model.create.assert_not_called()

    def test_variant_enqueue_records_its_mapping(self):
        publication = MarketplaceStockSyncTests._publication(variants=2)
        mapping = MagicMock()
        mapping.id = 99
        mapping.publication_id = publication
        mapping.external_variant_id = "987654321"
        mapping.last_stock_sent = 0
        mapping.last_stock_sync_at = False
        publication._stock_quantity.return_value = 7
        service = MarketplaceStockSyncTests()._service(MagicMock())
        job_model = MagicMock()
        new_job = MagicMock()
        job_model.search.return_value = False
        job_model.create.return_value = new_job
        service.env.__getitem__.return_value = job_model

        result = service.enqueue(publication, "update_stock", mapping=mapping)

        self.assertIs(result, new_job)
        self.assertEqual(job_model.create.call_args.args[0]["mapping_id"], 99)

    def test_failed_job_is_requeued_by_existing_retry(self):
        job_model = MagicMock()
        failed_job = MagicMock()
        failed_job.attempts = 1
        failed_job.max_retries = 3
        job_model.search.return_value = [failed_job]

        SceJob.cron_retry_failed_jobs(job_model)

        failed_job.write.assert_called_once_with({"state": "queued", "error_message": False})


if __name__ == "__main__":
    unittest.main()
