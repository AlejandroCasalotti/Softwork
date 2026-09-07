import inspect
import unittest
from unittest.mock import Mock, patch

from odoo.exceptions import ValidationError

from ..models.sce_external_connection import SceExternalConnection
from ..services.connection_service import ConnectionService
from ..services.errors import ApiError, ConfigurationError
from ..services.odoo19_json2_adapter import Odoo19Json2Adapter
from ..services.secret_storage import SecretStorage


class FakeResponse:
    def __init__(self, payload=None):
        self.status_code = 200
        self.text = "{}"
        self._payload = payload if payload is not None else {}
        self.is_redirect = False
        self.is_permanent_redirect = False

    def json(self):
        return self._payload


class Odoo19Json2RemoteContextTests(unittest.TestCase):
    def setUp(self):
        self.storage = SecretStorage(master_key=SecretStorage.generate_master_key())
        self.secret = self.storage.encrypt("test-api-key")
        self.session = Mock()

    def _adapter(self):
        with patch("socket.getaddrinfo", return_value=[(None, None, None, None, ("93.184.216.34", 443))]):
            return Odoo19Json2Adapter(
                base_url="https://example.com",
                database="test-db",
                user="bot@example.com",
                secret_storage=self.storage,
                secret_ref=self.secret,
                session=self.session,
            )

    def test_none_context_preserves_existing_payload(self):
        adapter = self._adapter()
        self.session.post.return_value = FakeResponse([])

        adapter.search_read("product.product", fields=["id"], limit=1)

        payload = self.session.post.call_args.kwargs["json"]
        self.assertEqual(payload, {"domain": [], "fields": ["id"], "offset": 0, "limit": 1})
        self.assertNotIn("context", payload)

    def test_empty_context_is_serialized_explicitly(self):
        adapter = self._adapter()
        self.session.post.return_value = FakeResponse([])

        adapter.search_read("product.product", fields=["id"], limit=1, context={})

        self.assertEqual(self.session.post.call_args.kwargs["json"]["context"], {})

    def test_explicit_context_is_transmitted_without_company_defaults(self):
        adapter = self._adapter()
        self.session.post.return_value = FakeResponse([])
        context = {"lang": "es_AR", "custom_probe": True}

        adapter.search("product.template", limit=2, order="id asc", context=context)

        payload = self.session.post.call_args.kwargs["json"]
        self.assertEqual(payload["context"], context)
        self.assertNotIn("company_id", payload["context"])
        self.assertNotIn("allowed_company_ids", payload["context"])
        self.assertNotIn("force_company", payload["context"])

    def test_non_dictionary_context_is_rejected(self):
        adapter = self._adapter()

        with self.assertRaises(ConfigurationError):
            adapter.search("product.template", context=["invalid"])

    def test_current_user_context_uses_context_get_without_request_context(self):
        adapter = self._adapter()
        self.session.post.return_value = FakeResponse({"company_id": 7, "allowed_company_ids": [7, 8]})

        result = adapter.current_user_context()

        self.assertEqual(result["company_id"], 7)
        self.assertTrue(self.session.post.call_args.args[0].endswith("/json/2/res.users/context_get"))
        self.assertEqual(self.session.post.call_args.kwargs["json"], {})


class ConnectionServiceRemoteContextTests(unittest.TestCase):
    def _connection(self):
        connection = Mock()
        connection.url = "https://example.com"
        connection.database = "test-db"
        connection.user = "bot@example.com"
        connection.timeout_seconds = 30
        connection.allow_insecure_http = False
        connection.allow_private_network = False
        connection.external_company_id = 42
        connection.secret_id.with_context.return_value.get_value.return_value = "test-api-key"
        return connection

    @patch("odoo.addons.sce_connect.services.connection_service.Odoo19Json2Adapter")
    @patch("odoo.addons.sce_connect.services.connection_service.SecretStorage")
    def test_explicit_context_is_forwarded_to_adapter(self, storage_class, adapter_class):
        storage_class.from_environment.return_value.encrypt.return_value = "encrypted"
        adapter = adapter_class.return_value
        service = ConnectionService(self._connection())

        service.search_read("product.product", fields=["id"], context={"lang": "es_AR"})

        adapter.search_read.assert_called_once_with(
            "product.product",
            domain=None,
            fields=["id"],
            offset=0,
            limit=None,
            order=None,
            context={"lang": "es_AR"},
        )

    @patch("odoo.addons.sce_connect.services.connection_service.Odoo19Json2Adapter")
    @patch("odoo.addons.sce_connect.services.connection_service.SecretStorage")
    def test_absent_context_and_external_company_do_not_inject_company_keys(self, storage_class, adapter_class):
        storage_class.from_environment.return_value.encrypt.return_value = "encrypted"
        adapter = adapter_class.return_value
        service = ConnectionService(self._connection())

        service.search("product.product")

        adapter.search.assert_called_once_with(
            "product.product",
            domain=None,
            offset=0,
            limit=None,
            order=None,
            context=None,
        )

    @patch("odoo.addons.sce_connect.services.connection_service.Odoo19Json2Adapter")
    @patch("odoo.addons.sce_connect.services.connection_service.SecretStorage")
    def test_remote_company_context_returns_only_company_identity_fields(self, storage_class, adapter_class):
        storage_class.from_environment.return_value.encrypt.return_value = "encrypted"
        adapter_class.return_value.current_user_context.return_value = {
            "uid": 2,
            "lang": "es_AR",
            "company_id": 7,
            "allowed_company_ids": [7, 8],
        }
        service = ConnectionService(self._connection())

        result = service.remote_company_context()

        self.assertEqual(result, {"company_id": 7, "allowed_company_ids": [7, 8]})
        adapter_class.return_value.current_user_context.assert_called_once_with()

    @patch("odoo.addons.sce_connect.services.connection_service.Odoo19Json2Adapter")
    @patch("odoo.addons.sce_connect.services.connection_service.SecretStorage")
    def test_invalid_remote_context_is_rejected_without_logging_credentials(self, storage_class, adapter_class):
        storage_class.from_environment.return_value.encrypt.return_value = "encrypted"
        adapter_class.return_value.current_user_context.return_value = ["invalid"]
        service = ConnectionService(self._connection())

        with self.assertRaises(ApiError) as error:
            service.remote_company_context()

        self.assertNotIn("test-api-key", str(error.exception))


class ExternalCompanyIdentityTests(unittest.TestCase):
    def test_external_company_id_is_an_integer_remote_identifier(self):
        source = inspect.getsource(SceExternalConnection)

        self.assertIn("external_company_id = fields.Integer", source)
        self.assertIn("ID de res.company en el Odoo remoto", source)
        self.assertNotIn("Many2one(\"res.company\"", source)

    def test_negative_external_company_id_is_rejected(self):
        connection = Mock()
        connection.external_company_id = -1

        with self.assertRaises(ValidationError):
            SceExternalConnection._check_external_company_id([connection])

    def test_empty_external_company_id_remains_compatible(self):
        connection = Mock()
        connection.external_company_id = 0

        SceExternalConnection._check_external_company_id([connection])


if __name__ == "__main__":
    unittest.main()
