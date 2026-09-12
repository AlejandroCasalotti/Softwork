import unittest
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from odoo import fields
from odoo.exceptions import UserError

from odoo.addons.sce_connector_ml.services.http_transport import MercadoLibreHttpTransport
from odoo.addons.sce_connector_ml.services.ml_provider import MercadoLibreProvider
from odoo.addons.softwork_ecommerce_conector_base.services.providers.ml_provider import (
    MercadoLibreProvider as LegacyMercadoLibreProvider,
)

from ..models.sce_account import SceAccount
from ..services.mercadolibre_credential_resolver import MercadoLibreConnectCredentialResolver


class _Secret:
    def __init__(self, value):
        self.value = value
        self.context = None

    def with_context(self, **context):
        self.context = context
        return self

    def get_value(self):
        return self.value


class _ExecutionAccount:
    def __init__(self, connect_account=False, access_token="integrated-token"):
        self.connect_mercadolibre_account_id = connect_account
        self.access_token = access_token
        self.external_user_id = "integrated-seller"
        self.env = MagicMock()

    def ensure_one(self):
        return self


class MercadoLibreConnectCredentialResolverTests(unittest.TestCase):
    def _connect_account(self, token="connect-token", expires_at=False, seller_user_id="connect-seller"):
        return SimpleNamespace(
            seller_user_id=seller_user_id,
            expires_at=expires_at,
            access_token_secret_id=_Secret(token),
        )

    def test_resolver_reads_access_token_from_authorized_secret(self):
        connect_account = self._connect_account()
        account = _ExecutionAccount(connect_account)

        token = MercadoLibreConnectCredentialResolver(account.env, account).get_access_token()

        self.assertEqual(token, "connect-token")
        self.assertEqual(
            connect_account.access_token_secret_id.context,
            {"sce_backend_secret_access": True},
        )
        self.assertEqual(account.access_token, "integrated-token")

    @patch("odoo.addons.sce_connect.services.mercadolibre_credential_resolver.MercadoLibreOAuthService")
    def test_expired_connect_token_delegates_refresh_to_existing_oauth_service(self, oauth_service):
        expired_account = self._connect_account(expires_at=fields.Datetime.now())
        refreshed_account = self._connect_account(
            token="refreshed-token",
            expires_at=fields.Datetime.now() + timedelta(hours=6),
        )
        oauth_service.return_value.refresh.return_value = refreshed_account
        account = _ExecutionAccount(expired_account)

        token = MercadoLibreConnectCredentialResolver(account.env, account).get_access_token()

        self.assertEqual(token, "refreshed-token")
        oauth_service.assert_called_once_with(account.env)
        oauth_service.return_value.refresh.assert_called_once_with(expired_account)
        self.assertGreater(refreshed_account.expires_at, fields.Datetime.now())
        self.assertEqual(account.access_token, "integrated-token")

    def test_missing_connect_secret_raises_without_exposing_token(self):
        connect_account = self._connect_account()
        connect_account.access_token_secret_id = False
        account = _ExecutionAccount(connect_account)

        with self.assertRaisesRegex(UserError, "access token disponible") as error:
            MercadoLibreConnectCredentialResolver(account.env, account).get_access_token()

        self.assertNotIn("connect-token", str(error.exception))

    def test_account_hook_uses_connect_token_only_when_linked(self):
        connect_account = self._connect_account()
        account = _ExecutionAccount(connect_account)
        account._uses_connect_mercadolibre_credentials = lambda: True

        with patch(
            "odoo.addons.sce_connect.services.mercadolibre_credential_resolver.MercadoLibreConnectCredentialResolver"
        ) as resolver:
            resolver.return_value.get_access_token.return_value = "resolved-token"
            token = SceAccount._get_mercadolibre_access_token(account)

        self.assertEqual(token, "resolved-token")
        self.assertEqual(account.access_token, "integrated-token")

    def test_account_hook_preserves_integrated_credentials_without_connect_link(self):
        account = _ExecutionAccount()
        account._uses_connect_mercadolibre_credentials = lambda: False

        self.assertEqual(SceAccount._get_mercadolibre_access_token(account), "integrated-token")
        self.assertEqual(
            SceAccount._get_mercadolibre_external_user_id(account),
            "integrated-seller",
        )

    def test_connect_seller_is_provider_identity(self):
        connect_account = self._connect_account(seller_user_id="connect-seller")
        account = _ExecutionAccount(connect_account)
        account._uses_connect_mercadolibre_credentials = lambda: True

        self.assertEqual(
            SceAccount._get_mercadolibre_external_user_id(account),
            "connect-seller",
        )

    def test_provider_uses_connect_seller_identity_before_network(self):
        account = _ExecutionAccount(self._connect_account(seller_user_id="connect-seller"))
        account._get_mercadolibre_external_user_id = MagicMock(return_value="connect-seller")
        provider = MercadoLibreProvider(MagicMock(), account)
        provider._request = MagicMock()

        self.assertEqual(provider.get_authenticated_user_id(), "connect-seller")
        provider._request.assert_not_called()

    @patch("odoo.addons.sce_connector_ml.services.http_transport.requests.request")
    def test_authenticated_provider_request_uses_resolved_connect_token(self, request):
        response = MagicMock(status_code=200, text='{}')
        response.json.return_value = {}
        request.return_value = response
        account = _ExecutionAccount()
        account.id = 1
        account.provider_timeout_seconds = 30
        account.refresh_token = "legacy-refresh-token"
        account._get_mercadolibre_access_token = MagicMock(return_value="connect-token")
        account._uses_connect_mercadolibre_credentials = MagicMock(return_value=True)
        provider = MercadoLibreProvider(MagicMock(), account)

        provider.update_stock({"item_id": "MLA123", "available_quantity": 1})

        headers = request.call_args.kwargs["headers"]
        self.assertEqual(headers["Authorization"], "Bearer connect-token")
        self.assertNotIn("sce.mercadolibre.account", MercadoLibreHttpTransport._request.__code__.co_consts)

    @patch(
        "odoo.addons.softwork_ecommerce_conector_base.services.providers.ml_provider.requests.request"
    )
    def test_legacy_provider_request_uses_resolved_connect_token(self, request):
        response = MagicMock(status_code=200, text='{}')
        response.json.return_value = {}
        request.return_value = response
        account = _ExecutionAccount()
        account.id = 1
        account.provider_timeout_seconds = 30
        account.refresh_token = "legacy-refresh-token"
        account._get_mercadolibre_access_token = MagicMock(return_value="connect-token")
        account._uses_connect_mercadolibre_credentials = MagicMock(return_value=True)
        provider = LegacyMercadoLibreProvider(MagicMock(), account)

        provider.update_stock({"item_id": "MLA123", "available_quantity": 1})

        self.assertEqual(request.call_args.kwargs["headers"]["Authorization"], "Bearer connect-token")

    def test_connect_401_does_not_use_integrated_refresh(self):
        account = _ExecutionAccount()
        account.id = 1
        account.provider_timeout_seconds = 30
        account.refresh_token = "legacy-refresh-token"
        account._get_mercadolibre_access_token = MagicMock(return_value="connect-token")
        account._uses_connect_mercadolibre_credentials = MagicMock(return_value=True)
        provider = MercadoLibreProvider(MagicMock(), account)
        provider.refresh_token = MagicMock()
        response = MagicMock(status_code=401, text="unauthorized")

        with patch("odoo.addons.sce_connector_ml.services.http_transport.requests.request", return_value=response):
            with self.assertRaises(UserError):
                provider.update_stock({"item_id": "MLA123", "available_quantity": 1})

        provider.refresh_token.assert_not_called()

    @patch("odoo.addons.sce_connector_ml.services.http_transport.requests.request")
    def test_integrated_401_keeps_existing_refresh_retry(self, request):
        account = _ExecutionAccount()
        account.id = 1
        account.provider_timeout_seconds = 30
        account.refresh_token = "integrated-refresh-token"
        account._get_mercadolibre_access_token = MagicMock(return_value="integrated-token")
        account._uses_connect_mercadolibre_credentials = MagicMock(return_value=False)
        provider = MercadoLibreProvider(MagicMock(), account)
        provider.refresh_token = MagicMock(return_value={"access_token": "renewed-token"})
        provider._persist_refreshed_tokens = MagicMock(return_value=True)
        unauthorized = MagicMock(status_code=401, text="unauthorized")
        success = MagicMock(status_code=200, text='{}')
        success.json.return_value = {}
        request.side_effect = [unauthorized, success]

        provider.update_stock({"item_id": "MLA123", "available_quantity": 1})

        provider.refresh_token.assert_called_once_with()
        self.assertEqual(request.call_count, 2)


if __name__ == "__main__":
    unittest.main()
