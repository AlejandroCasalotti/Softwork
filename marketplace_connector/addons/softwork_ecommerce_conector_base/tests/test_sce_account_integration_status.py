import unittest
from unittest.mock import MagicMock, patch

from odoo.exceptions import UserError

from ..models.sce_account import SceAccount
from ..services.provider_factory import ProviderFactory


class _FakeRecordset:
    """Minimal truthy/falsy stand-in for an Odoo recordset used in tests."""

    def __init__(self, truthy=True, name="Mock"):
        self._truthy = truthy
        self.name = name
        self.display_name = name
        self.id = 1

    def __bool__(self):
        return self._truthy

    def mapped(self, field):
        return []


def _build_account_mock(access_token="token-123"):
    """Builds a MagicMock standing in for an sce.account record with just
    enough surface for _run_integration_status_tests() to run end to end."""
    models = {}

    def model(name, search_result):
        m = MagicMock()
        m.sudo.return_value.search.return_value = search_result
        models[name] = m
        return m

    model("ir.config_parameter", "19.0")
    model("ir.module.module", _FakeRecordset(truthy=False))
    model("stock.warehouse", _FakeRecordset(truthy=True, name="WH"))
    model("stock.location", _FakeRecordset(truthy=True, name="Stock"))
    model("product.pricelist", _FakeRecordset(truthy=True, name="Price List"))

    # ir.config_parameter needs get_param(), not search()
    models["ir.config_parameter"].sudo.return_value.get_param.return_value = "19.0"

    account = MagicMock(spec=SceAccount)
    account.env = MagicMock()
    account.env.__getitem__.side_effect = lambda key: models[key]
    account.env.cr.dbname = "test_db"
    account.env.user.name = "Test User"
    account.env.user.has_group.return_value = True
    account.env.company = _FakeRecordset(truthy=True, name="Company")
    account.company_id = _FakeRecordset(truthy=True, name="Company")
    account.access_token = access_token
    return account


class SceAccountIntegrationStatusTests(unittest.TestCase):
    def _mercadolibre_items_test(self, tests):
        matches = [t for t in tests if t["test_name"] == "MercadoLibre Items"]
        self.assertEqual(len(matches), 1)
        return matches[0]

    @patch("odoo.addons.sce_connector_ml.services.catalog_reader.MercadoLibreCatalogReader")
    @patch.object(ProviderFactory, "get_provider")
    def test_provider_factory_devuelve_wrapper_sin_request(self, mock_get_provider, mock_reader_cls):
        wrapper = MagicMock(spec=["get_authenticated_user_id", "list_item_ids"])
        mock_get_provider.return_value = wrapper
        mock_reader_cls.return_value.list_item_ids.return_value = {"paging": {"total": 3}}

        account = _build_account_mock()
        tests = SceAccount._run_integration_status_tests(account)

        mock_get_provider.assert_called_once_with(account)
        mock_reader_cls.assert_called_once_with(wrapper)
        self.assertFalse(hasattr(wrapper, "_request"))

    @patch.object(ProviderFactory, "get_provider")
    def test_diagnostico_obtiene_total_via_interfaz_publica(self, mock_get_provider):
        wrapper = MagicMock()
        wrapper.get_authenticated_user_id.return_value = "999"
        wrapper.list_item_ids.return_value = {
            "results": ["MLA1", "MLA2", "MLA3"],
            "paging": {"total": 3},
        }
        mock_get_provider.return_value = wrapper

        account = _build_account_mock()
        tests = SceAccount._run_integration_status_tests(account)

        result = self._mercadolibre_items_test(tests)
        self.assertEqual(result["status"], "success")
        self.assertIn("3", result["message"])
        wrapper.list_item_ids.assert_called_once_with("999", offset=0, limit=1)
        self.assertFalse(wrapper.method_calls and any(
            call[0] == "_request" for call in wrapper.method_calls
        ))

    @patch.object(ProviderFactory, "get_provider")
    def test_error_de_api_se_maneja_como_warning(self, mock_get_provider):
        wrapper = MagicMock()
        wrapper.get_authenticated_user_id.side_effect = UserError("token vencido")
        mock_get_provider.return_value = wrapper

        account = _build_account_mock()
        tests = SceAccount._run_integration_status_tests(account)

        result = self._mercadolibre_items_test(tests)
        self.assertEqual(result["status"], "warning")
        self.assertEqual(result["action_type"], "reconnect")

    @patch.object(ProviderFactory, "get_provider")
    def test_sin_access_token_no_llama_al_provider(self, mock_get_provider):
        account = _build_account_mock(access_token=False)
        tests = SceAccount._run_integration_status_tests(account)

        result = self._mercadolibre_items_test(tests)
        self.assertEqual(result["status"], "warning")
        mock_get_provider.assert_not_called()

    @patch.object(ProviderFactory, "get_provider")
    def test_no_hay_operaciones_de_escritura(self, mock_get_provider):
        wrapper = MagicMock()
        wrapper.get_authenticated_user_id.return_value = "999"
        wrapper.list_item_ids.return_value = {"results": [], "paging": {"total": 0}}
        mock_get_provider.return_value = wrapper

        account = _build_account_mock()
        SceAccount._run_integration_status_tests(account)

        for forbidden in ("publish_product", "update_product", "delete_product", "update_stock", "update_price"):
            getattr(wrapper, forbidden).assert_not_called()


if __name__ == "__main__":
    unittest.main()
