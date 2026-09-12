import time
from collections import defaultdict
from datetime import datetime

from odoo.exceptions import UserError

from odoo.addons.softwork_provider_odoo.services.product_reader import OdooExternalProductReader
from odoo.addons.softwork_provider_odoo.services.provider import OdooProvider

from .catalog_reader import MercadoLibreCatalogReader


class ProductReconciliationService:
    """Read-only diagnostics comparing external Odoo products with ML SKUs."""

    PRODUCT_FIELDS = [
        "id",
        "product_tmpl_id",
        "default_code",
        "barcode",
        "active",
        "qty_available",
        "lst_price",
        "product_template_attribute_value_ids",
    ]
    PAGE_SIZE = 100

    def __init__(self, env, account, session=None):
        self.env = env
        self.account = account
        self.session = session

    def _odoo_reader(self):
        return OdooExternalProductReader(OdooProvider(self.env, self.account))

    def _ml_reader(self):
        from odoo.addons.softwork_ecommerce_conector_base.services.provider_factory import ProviderFactory

        provider = ProviderFactory.get_provider(self.account)
        return MercadoLibreCatalogReader(provider)

    def test_odoo_connection(self):
        started = time.monotonic()
        reader = self._odoo_reader()
        fields = reader.get_product_fields()
        rows = reader.search_products(fields=["id", "default_code"], limit=1, order="id asc")
        return {
            "status": "OK",
            "timestamp": datetime.utcnow(),
            "latency_ms": int((time.monotonic() - started) * 1000),
            "message": "Odoo respondió correctamente.",
            "products_accessible": bool(rows),
            "default_code_available": "default_code" in fields,
        }

    def test_mercadolibre_connection(self):
        started = time.monotonic()
        reader = self._ml_reader()
        catalog = reader.list_item_ids(offset=0, limit=1)
        return {
            "status": "OK",
            "timestamp": datetime.utcnow(),
            "latency_ms": int((time.monotonic() - started) * 1000),
            "message": "MercadoLibre respondió correctamente.",
            "seller_id": catalog["seller_id"],
            "publications_accessible": catalog["paging"].get("total"),
        }

    @staticmethod
    def _sku(value):
        return str(value).strip() if value else False

    def _read_all_odoo_products(self):
        reader = self._odoo_reader()
        rows = []
        offset = 0
        while True:
            batch = reader.search_products(
                fields=self.PRODUCT_FIELDS,
                offset=offset,
                limit=self.PAGE_SIZE,
                order="id asc",
            )
            if not batch:
                break
            rows.extend(batch)
            if len(batch) < self.PAGE_SIZE:
                break
            offset += self.PAGE_SIZE
        return rows

    def _read_all_ml_items(self):
        reader = self._ml_reader()
        item_ids = reader.list_all_item_ids()["item_ids"]
        return [reader.get_item(item_id) for item_id in item_ids]

    @staticmethod
    def _ml_candidates(items):
        candidates = defaultdict(list)
        items_with_sku = 0
        for item in items:
            item_has_sku = bool(item.get("canonical_sku"))
            if item_has_sku:
                items_with_sku += 1
                candidates[item["canonical_sku"]].append(
                    {
                        "item_id": item["item_id"],
                        "variation_id": False,
                        "canonical_sku": item["canonical_sku"],
                        "seller_custom_field": item.get("seller_custom_field") or False,
                    }
                )
            for variation in item.get("variations", []):
                sku = variation.get("canonical_sku")
                if not sku:
                    continue
                candidates[sku].append(
                    {
                        "item_id": item["item_id"],
                        "variation_id": variation.get("variation_id"),
                        "canonical_sku": sku,
                        "seller_custom_field": variation.get("seller_custom_field") or False,
                    }
                )
        return candidates, items_with_sku

    def analyze(self):
        started = time.monotonic()
        odoo_products = self._read_all_odoo_products()
        ml_items = self._read_all_ml_items()
        odoo_by_sku = defaultdict(list)
        for product in odoo_products:
            sku = self._sku(product.get("default_code"))
            if sku:
                odoo_by_sku[sku].append(product)
        ml_by_sku, ml_with_sku = self._ml_candidates(ml_items)

        detail = []
        all_skus = sorted(set(odoo_by_sku) | set(ml_by_sku))
        for sku in all_skus:
            odoo_candidates = odoo_by_sku.get(sku, [])
            ml_candidates = ml_by_sku.get(sku, [])
            if len(odoo_candidates) > 1 or len(ml_candidates) > 1:
                status = "CONFLICT"
            elif odoo_candidates and ml_candidates:
                status = "MATCH"
            elif odoo_candidates:
                status = "NO_MATCH"
            else:
                status = "NO_MATCH"
            if odoo_candidates:
                for product in odoo_candidates:
                    candidate = ml_candidates[0] if len(ml_candidates) == 1 else {}
                    detail.append({
                        "status": status,
                        "sku": sku,
                        "odoo_product_id": product.get("id"),
                        "odoo_default_code": product.get("default_code") or False,
                        "mercadolibre_item_id": candidate.get("item_id") or False,
                        "mercadolibre_variation_id": candidate.get("variation_id") or False,
                        "mercadolibre_sku": candidate.get("canonical_sku") or False,
                    })
            else:
                for candidate in ml_candidates:
                    detail.append({
                        "status": status,
                        "sku": sku,
                        "odoo_product_id": False,
                        "odoo_default_code": False,
                        "mercadolibre_item_id": candidate["item_id"],
                        "mercadolibre_variation_id": candidate["variation_id"] or False,
                        "mercadolibre_sku": candidate["canonical_sku"],
                    })

        return {
            "status": "OK",
            "timestamp": datetime.utcnow(),
            "latency_ms": int((time.monotonic() - started) * 1000),
            "stats": {
                "odoo_total_products": len(odoo_products),
                "odoo_products_with_sku": sum(bool(self._sku(p.get("default_code"))) for p in odoo_products),
                "odoo_products_without_sku": sum(not bool(self._sku(p.get("default_code"))) for p in odoo_products),
                "ml_total_publications": len(ml_items),
                "ml_publications_with_sku": ml_with_sku,
                "ml_publications_without_sku": len(ml_items) - ml_with_sku,
                "match": sum(line["status"] == "MATCH" for line in detail),
                "no_match": sum(line["status"] == "NO_MATCH" for line in detail),
                "conflict": sum(line["status"] == "CONFLICT" for line in detail),
                "invalid": 0,
            },
            "details": detail,
        }
