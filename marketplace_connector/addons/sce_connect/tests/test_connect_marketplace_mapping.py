import inspect
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from odoo.exceptions import ValidationError

from ..models.sce_account import SceAccount
from ..models.sce_connect_marketplace_mapping import SceConnectMarketplaceMapping


def connect_account(tenant_id=1, seller_user_id="seller-1"):
    return SimpleNamespace(tenant_id=tenant_id, seller_user_id=seller_user_id)


def marketplace_account(tenant_id=1, seller_user_id="seller-1", external_user_id="seller-1"):
    return SimpleNamespace(
        provider_type="mercadolibre",
        connector_id=SimpleNamespace(provider_type="mercadolibre"),
        external_user_id=external_user_id,
        connect_mercadolibre_account_id=connect_account(tenant_id, seller_user_id),
    )


def mapping(tenant_id=1, connection_tenant_id=1, product_connection_matches=True, product_model="product.product"):
    connection = SimpleNamespace(id=1, tenant_id=connection_tenant_id)
    product_connection = connection if product_connection_matches else SimpleNamespace(id=2, tenant_id=tenant_id)
    return SimpleNamespace(
        tenant_id=tenant_id,
        external_connection_id=connection,
        external_product_mapping_id=SimpleNamespace(
            external_connection_id=product_connection,
            external_model=product_model,
        ),
        marketplace_account_id=marketplace_account(tenant_id),
    )


class SceAccountConnectCredentialsTests(unittest.TestCase):
    def test_matching_seller_and_mercadolibre_provider_are_valid(self):
        account = marketplace_account()

        SceAccount._check_connect_mercadolibre_account([account])

    def test_seller_mismatch_is_rejected(self):
        account = marketplace_account(seller_user_id="seller-a", external_user_id="seller-b")

        with self.assertRaises(ValidationError):
            SceAccount._check_connect_mercadolibre_account([account])

    def test_non_mercadolibre_account_is_rejected(self):
        account = marketplace_account()
        account.provider_type = "odoo"

        with self.assertRaises(ValidationError):
            SceAccount._check_connect_mercadolibre_account([account])

    def test_connect_link_does_not_copy_tokens(self):
        source = inspect.getsource(SceAccount)

        self.assertIn('"sce.mercadolibre.account"', source)
        self.assertIn("copy=False", source)
        self.assertNotIn("access_token", inspect.getsource(SceAccount._check_connect_mercadolibre_account))
        self.assertNotIn("refresh_token", inspect.getsource(SceAccount._check_connect_mercadolibre_account))


class SceConnectMarketplaceMappingTests(unittest.TestCase):
    def test_valid_external_variant_mapping_does_not_require_publication(self):
        record = mapping()

        SceConnectMarketplaceMapping._check_identity_scope([record])

    def test_different_connection_tenant_is_rejected(self):
        record = mapping(connection_tenant_id=2)

        with self.assertRaises(ValidationError):
            SceConnectMarketplaceMapping._check_identity_scope([record])

    def test_external_product_from_another_connection_is_rejected(self):
        record = mapping(product_connection_matches=False)

        with self.assertRaises(ValidationError):
            SceConnectMarketplaceMapping._check_identity_scope([record])

    def test_template_mapping_is_rejected_as_noncanonical_unit(self):
        record = mapping(product_model="product.template")

        with self.assertRaises(ValidationError):
            SceConnectMarketplaceMapping._check_identity_scope([record])

    def test_connect_account_from_another_tenant_is_rejected(self):
        record = mapping()
        record.marketplace_account_id.connect_mercadolibre_account_id = connect_account(2)

        with self.assertRaises(ValidationError):
            SceConnectMarketplaceMapping._check_identity_scope([record])

    def test_non_mercadolibre_execution_account_is_rejected(self):
        record = mapping()
        record.marketplace_account_id.provider_type = "odoo"

        with self.assertRaises(ValidationError):
            SceConnectMarketplaceMapping._check_identity_scope([record])

    def test_partial_unique_indexes_cover_simple_and_variant_identities(self):
        cursor = MagicMock()
        model = SimpleNamespace(env=SimpleNamespace(cr=cursor))

        SceConnectMarketplaceMapping.init(model)

        simple_sql, variation_sql = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertIn("WHERE marketplace_variation_id IS NULL", simple_sql)
        self.assertIn("marketplace_account_id, marketplace_item_id", simple_sql)
        self.assertIn("WHERE marketplace_variation_id IS NOT NULL", variation_sql)
        self.assertIn(
            "marketplace_account_id, marketplace_item_id, marketplace_variation_id",
            variation_sql,
        )

    def test_source_identity_constraint_is_declared(self):
        self.assertIn(
            "UNIQUE(external_product_mapping_id, marketplace_account_id)",
            inspect.getsource(SceConnectMarketplaceMapping),
        )


if __name__ == "__main__":
    unittest.main()