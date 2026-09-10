import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from odoo.exceptions import ValidationError

from ..services.connect_marketplace_mapping_service import SceConnectMarketplaceMappingService


class _Record:
    def __init__(self, **values):
        self.__dict__.update(values)
        self.id = values.get("id", 1)

    def exists(self):
        return True

    def write(self, values):
        self.__dict__.update(values)
        return True

    def __eq__(self, other):
        return isinstance(other, _Record) and self.id == other.id


class _MappingModel:
    def __init__(self):
        self.current = False
        self.created = []

    def sudo(self):
        return self

    def search(self, _domain, limit=1):
        return self.current

    def create(self, values):
        mapping = _Record(**values)
        self.created.append(mapping)
        self.current = mapping
        return mapping


def make_product(product_id=11, connection_id=5, tenant_id=2, sku="SKU-11"):
    tenant = _Record(id=tenant_id)
    connection = _Record(id=connection_id, tenant_id=tenant)
    return _Record(
        id=product_id,
        external_model="product.product",
        external_connection_id=connection,
        tenant_id=tenant,
        default_code=sku,
    )


def make_account(account_id=8, tenant_id=2, provider_type="mercadolibre"):
    tenant = _Record(id=tenant_id)
    connection = _Record(id=5, tenant_id=tenant)
    connect_account = _Record(id=20, tenant_id=tenant)
    return _Record(
        id=account_id,
        provider_type=provider_type,
        tenant_id=tenant,
        external_connection_id=connection,
        connect_mercadolibre_account_id=connect_account,
    )


class ConnectMarketplaceMappingServiceTests(unittest.TestCase):
    def setUp(self):
        self.mapping_model = _MappingModel()
        self.service = MagicMock(spec=SceConnectMarketplaceMappingService)
        self.service.env = {"sce.connect.marketplace.mapping": self.mapping_model}
        self.service._validate_inputs = SceConnectMarketplaceMappingService._validate_inputs.__get__(self.service)
        self.service.get_mapping = SceConnectMarketplaceMappingService.get_mapping.__get__(self.service)
        self.service.create_or_update_mapping = SceConnectMarketplaceMappingService.create_or_update_mapping.__get__(self.service)
        self.service.link_item = SceConnectMarketplaceMappingService.link_item.__get__(self.service)

    def test_simple_mapping_uses_product_variant_sku_without_publication(self):
        product = make_product(sku="SKU-SIMPLE")
        account = make_account()

        mapping, action = self.service.create_or_update_mapping(product, account, "ML123")

        self.assertEqual(action, "created")
        self.assertEqual(mapping.marketplace_item_id, "ML123")
        self.assertFalse(mapping.marketplace_variation_id)
        self.assertEqual(mapping.sku, "SKU-SIMPLE")
        self.assertEqual(len(self.mapping_model.created), 1)

    def test_variant_mapping_preserves_variation_id(self):
        product = make_product(product_id=12, sku="SKU-VARIANT")
        account = make_account()

        mapping, _action = self.service.link_item(product, account, "ML123", "ML456")

        self.assertEqual(mapping.marketplace_item_id, "ML123")
        self.assertEqual(mapping.marketplace_variation_id, "ML456")
        self.assertEqual(mapping.mapping_status, "verified")

    def test_upsert_updates_existing_mapping_without_duplicate(self):
        product = make_product()
        account = make_account()
        first, first_action = self.service.create_or_update_mapping(product, account, "ML123")
        second, second_action = self.service.create_or_update_mapping(product, account, "ML999")

        self.assertEqual(first_action, "created")
        self.assertEqual(second_action, "updated")
        self.assertEqual(first, second)
        self.assertEqual(second.marketplace_item_id, "ML999")
        self.assertEqual(len(self.mapping_model.created), 1)

    def test_missing_sku_is_allowed_without_inventing_one(self):
        product = make_product(sku=False)
        account = make_account()

        mapping, _action = self.service.create_or_update_mapping(product, account, "ML123")

        self.assertFalse(mapping.sku)

    def test_tenant_mismatch_is_rejected(self):
        product = make_product(tenant_id=2)
        account = make_account(tenant_id=3)

        with self.assertRaises(ValidationError):
            self.service.create_or_update_mapping(product, account, "ML123")

    def test_connection_and_model_are_validated(self):
        product = make_product()
        product.external_model = "product.template"

        with self.assertRaises(ValidationError):
            self.service.create_or_update_mapping(product, make_account(), "ML123")

    def test_invalid_item_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.service.create_or_update_mapping(make_product(), make_account(), "")

    def test_non_marketplace_account_is_rejected(self):
        with self.assertRaises(ValidationError):
            self.service.create_or_update_mapping(
                make_product(), make_account(provider_type="odoo"), "ML123"
            )

    def test_service_has_no_publication_dependency(self):
        source = SceConnectMarketplaceMappingService.create_or_update_mapping.__code__.co_names

        self.assertNotIn("marketplace.publication", source)
        self.assertNotIn("publication_service", source)


if __name__ == "__main__":
    unittest.main()