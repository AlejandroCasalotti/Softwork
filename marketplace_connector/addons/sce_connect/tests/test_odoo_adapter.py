import unittest
from unittest.mock import Mock, patch

import requests

from ..services.errors import (
    ApiError,
    AuthenticationError,
    ConfigurationError,
    OperationBlocked,
    PermissionError,
)
from ..services.odoo19_json2_adapter import Odoo19Json2Adapter
from ..services.secret_storage import SecretStorage


class FakeResponse:
    def __init__(self, status_code=200, payload=None, redirect=False):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.is_redirect = redirect
        self.is_permanent_redirect = False

    def json(self):
        return self._payload


class OdooAdapterTests(unittest.TestCase):
    def setUp(self):
        self.storage = SecretStorage(master_key=SecretStorage.generate_master_key())
        self.secret = self.storage.encrypt("test-api-key")
        self.session = Mock()
        self.public_dns = {"example.com": [(None, None, None, None, ("93.184.216.34", 443))]}

    def adapter(self):
        with patch("socket.getaddrinfo", return_value=self.public_dns["example.com"]):
            return Odoo19Json2Adapter(
                base_url="https://example.com",
                database="test-db",
                user="bot@example.com",
                secret_storage=self.storage,
                secret_ref=self.secret,
                session=self.session,
            )

    def test_https_required(self):
        with patch("socket.getaddrinfo", return_value=self.public_dns["example.com"]):
            with self.assertRaises(ConfigurationError):
                Odoo19Json2Adapter(
                    base_url="http://example.com",
                    database="test-db",
                    user="bot@example.com",
                    secret_storage=self.storage,
                    secret_ref=self.secret,
                )

    def test_private_network_blocked(self):
        with patch("socket.getaddrinfo", return_value=[(None, None, None, None, ("127.0.0.1", 443))]):
            with self.assertRaises(ConfigurationError):
                Odoo19Json2Adapter(
                    base_url="https://example.com",
                    database="test-db",
                    user="bot@example.com",
                    secret_storage=self.storage,
                    secret_ref=self.secret,
                )

    def test_read_search_search_read_and_metadata(self):
        adapter = self.adapter()
        self.session.post.return_value = FakeResponse(payload={"ok": True})
        self.assertEqual(adapter.read("res.partner", [1], ["name"]), {"ok": True})
        self.assertEqual(adapter.search("res.partner", [["active", "=", True]], limit=1), {"ok": True})
        self.assertEqual(adapter.search_read("res.partner", fields=["id"], limit=1), {"ok": True})
        self.assertEqual(adapter.metadata("res.partner"), {"ok": True})
        self.assertEqual(self.session.post.call_count, 4)

    def test_connection_checks_basic_models_without_writes(self):
        adapter = self.adapter()
        self.session.post.return_value = FakeResponse(payload=[])
        result = adapter.test_connection()
        self.assertEqual(result["status"], "connected")
        self.assertEqual(self.session.post.call_count, 4)
        for call in self.session.post.call_args_list:
            self.assertEqual(call.kwargs["json"]["limit"], 1)

    def test_create_and_write_are_explicit_operations(self):
        adapter = self.adapter()
        self.session.post.return_value = FakeResponse(payload=[42])
        self.assertEqual(adapter.create("res.partner", {"name": "test"}), [42])
        self.assertEqual(adapter.write("res.partner", [42], {"active": False}), [42])

    def test_unlink_and_execute_are_blocked(self):
        adapter = self.adapter()
        with self.assertRaises(OperationBlocked):
            adapter.unlink("res.partner", [42])
        with self.assertRaises(OperationBlocked):
            adapter.execute("res.partner", "unlink", [[42]])

    def test_http_error_classification(self):
        cases = [(401, AuthenticationError), (403, PermissionError), (500, ApiError)]
        for status, error_type in cases:
            adapter = self.adapter()
            self.session.post.return_value = FakeResponse(status_code=status)
            with self.assertRaises(error_type):
                adapter.read("res.partner", [1])

    def test_timeout_is_classified(self):
        adapter = self.adapter()
        self.session.post.side_effect = requests.Timeout()
        with self.assertRaises(Exception) as raised:
            adapter.read("res.partner", [1])
        self.assertEqual(raised.exception.__class__.__name__, "NetworkError")


if __name__ == "__main__":
    unittest.main()
