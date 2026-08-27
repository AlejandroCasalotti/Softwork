import unittest
from unittest.mock import Mock, patch

from ..services.connection_service import ConnectionService
from ..services.errors import (
    ApiError,
    AuthenticationError,
    ConfigurationError,
    NetworkError,
    PermissionError,
)


class ConnectionServiceTests(unittest.TestCase):
    def connection(self):
        connection = Mock()
        connection.url = "https://example.com"
        connection.database = "test-db"
        connection.user = "bot@example.com"
        connection.timeout_seconds = 30
        connection.allow_insecure_http = False
        connection.allow_private_network = False
        connection.secret_id.with_context.return_value.get_value.return_value = "test-api-key"
        connection.sudo.return_value = connection
        return connection

    @patch("sce_connect.services.connection_service.Odoo19Json2Adapter")
    @patch("sce_connect.services.connection_service.SecretStorage")
    def test_connected(self, storage_class, adapter_class):
        connection = self.connection()
        storage_class.from_environment.return_value.encrypt.return_value = "encrypted"
        adapter_class.return_value.test_connection.return_value = {"models": {}}
        result = ConnectionService(connection).test_connection()
        self.assertEqual(result["status"], "connected")
        connection.sudo.assert_called()

    @patch("sce_connect.services.connection_service.Odoo19Json2Adapter")
    @patch("sce_connect.services.connection_service.SecretStorage")
    def test_authentication_error(self, storage_class, adapter_class):
        connection = self.connection()
        storage_class.from_environment.return_value.encrypt.return_value = "encrypted"
        adapter_class.return_value.test_connection.side_effect = AuthenticationError("bad credentials")
        result = ConnectionService(connection).test_connection()
        self.assertEqual(result["status"], "authentication_error")

    @patch("sce_connect.services.connection_service.Odoo19Json2Adapter")
    @patch("sce_connect.services.connection_service.SecretStorage")
    def test_invalid_configuration(self, storage_class, adapter_class):
        connection = self.connection()
        storage_class.from_environment.return_value.encrypt.return_value = "encrypted"
        adapter_class.side_effect = ConfigurationError("invalid URL")
        result = ConnectionService(connection).test_connection()
        self.assertEqual(result["status"], "invalid_configuration")

    @patch("sce_connect.services.connection_service.Odoo19Json2Adapter")
    @patch("sce_connect.services.connection_service.SecretStorage")
    def test_permission_error(self, storage_class, adapter_class):
        connection = self.connection()
        storage_class.from_environment.return_value.encrypt.return_value = "encrypted"
        adapter_class.return_value.test_connection.side_effect = PermissionError("forbidden")
        result = ConnectionService(connection).test_connection()
        self.assertEqual(result["status"], "permission_error")

    @patch("sce_connect.services.connection_service.Odoo19Json2Adapter")
    @patch("sce_connect.services.connection_service.SecretStorage")
    def test_network_error(self, storage_class, adapter_class):
        connection = self.connection()
        storage_class.from_environment.return_value.encrypt.return_value = "encrypted"
        adapter_class.return_value.test_connection.side_effect = NetworkError("offline")
        result = ConnectionService(connection).test_connection()
        self.assertEqual(result["status"], "network_error")

    @patch("sce_connect.services.connection_service.Odoo19Json2Adapter")
    @patch("sce_connect.services.connection_service.SecretStorage")
    def test_api_error(self, storage_class, adapter_class):
        connection = self.connection()
        storage_class.from_environment.return_value.encrypt.return_value = "encrypted"
        adapter_class.return_value.test_connection.side_effect = ApiError("bad response")
        result = ConnectionService(connection).test_connection()
        self.assertEqual(result["status"], "api_error")


if __name__ == "__main__":
    unittest.main()
