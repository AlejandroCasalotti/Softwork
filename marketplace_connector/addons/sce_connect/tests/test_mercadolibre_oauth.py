import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from odoo.exceptions import UserError

from ..services.errors import SecretStorageError
from ..services.mercadolibre_oauth import MercadoLibreOAuthService


class _Account:
    def __init__(self, refresh_error):
        self.id = 7
        self.status = "connected"
        self.expires_at = None
        self.refresh_token_secret_id = MagicMock()
        self.refresh_token_secret_id.with_context.return_value.get_value.side_effect = refresh_error
        self.writes = []

    def sudo(self):
        return self

    def write(self, values):
        self.writes.append(values)
        self.__dict__.update(values)
        return True

    def invalidate_recordset(self):
        return None


class MercadoLibreOAuthServiceTests(unittest.TestCase):
    def test_linked_execution_account_mismatch_is_rejected_before_reconnect(self):
        env = MagicMock()
        linked_accounts = [SimpleNamespace(external_user_id="seller-b")]
        env.__getitem__.return_value.sudo.return_value.search.return_value = linked_accounts

        service = MercadoLibreOAuthService(env)

        with self.assertRaisesRegex(UserError, "no coincide"):
            service._validate_linked_execution_accounts(SimpleNamespace(id=4), "seller-a")

        env.__getitem__.return_value.sudo.return_value.search.assert_called_once_with(
            [("connect_mercadolibre_account_id", "=", 4)]
        )

    @patch.object(MercadoLibreOAuthService, "_config", return_value={"client_id": "x"})
    def test_refresh_missing_secret_sets_auth_required(self, _config):
        env = MagicMock()
        env.cr = MagicMock()
        account = _Account(UserError("El secreto todavía no fue configurado."))

        service = MercadoLibreOAuthService(env)

        with self.assertRaisesRegex(UserError, "todavía no fue configurado"):
            service.refresh(account)

        self.assertEqual(account.status, "auth_required")
        self.assertEqual(account.last_error, "El secreto todavía no fue configurado.")
        self.assertEqual(account.writes[0]["status"], "token_refreshing")
        self.assertEqual(account.writes[-1]["status"], "auth_required")

    @patch.object(MercadoLibreOAuthService, "_config", return_value={"client_id": "x"})
    def test_refresh_secret_storage_failure_sets_error(self, _config):
        env = MagicMock()
        env.cr = MagicMock()
        account = _Account(SecretStorageError("No se pudo descifrar el secreto."))

        service = MercadoLibreOAuthService(env)

        with self.assertRaisesRegex(SecretStorageError, "descifrar"):
            service.refresh(account)

        self.assertEqual(account.status, "error")
        self.assertEqual(account.last_error, "No se pudo descifrar el secreto.")
        self.assertEqual(account.writes[0]["status"], "token_refreshing")
        self.assertEqual(account.writes[-1]["status"], "error")


if __name__ == "__main__":
    unittest.main()
