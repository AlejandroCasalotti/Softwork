import importlib.util
import os
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from cryptography.fernet import Fernet


class UserError(Exception):
    pass


def _load_core_secret_service():
    odoo_module = types.ModuleType("odoo")
    exceptions_module = types.ModuleType("odoo.exceptions")
    exceptions_module.UserError = UserError
    odoo_module.exceptions = exceptions_module
    sys.modules.setdefault("odoo", odoo_module)
    sys.modules["odoo.exceptions"] = exceptions_module

    module_path = (
        Path(__file__).resolve().parents[1] / "services" / "core_secret_service.py"
    )
    spec = importlib.util.spec_from_file_location("sce_core_secret_service_test", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.CoreSecretService


def _load_sce_global_settings():
    def _field(*args, **kwargs):
        return None

    def _decorator(*args, **kwargs):
        def wrapper(func):
            return func

        return wrapper

    odoo_module = sys.modules.setdefault("odoo", types.ModuleType("odoo"))
    exceptions_module = sys.modules.setdefault(
        "odoo.exceptions", types.ModuleType("odoo.exceptions")
    )
    exceptions_module.UserError = UserError
    odoo_module.exceptions = exceptions_module
    odoo_module.api = types.SimpleNamespace(depends_context=_decorator)
    odoo_module.fields = types.SimpleNamespace(
        Char=_field,
        Integer=_field,
        Selection=_field,
        Text=_field,
    )
    odoo_module.models = types.SimpleNamespace(Model=object)

    service_module_name = (
        "marketplace_connector.addons.sce_connector_ml.services.core_secret_service"
    )
    service_module = types.ModuleType(service_module_name)
    service_module.CoreSecretService = CoreSecretService
    sys.modules[service_module_name] = service_module

    module_path = (
        Path(__file__).resolve().parents[1] / "models" / "sce_global_settings.py"
    )
    spec = importlib.util.spec_from_file_location(
        "marketplace_connector.addons.sce_connector_ml.models.sce_global_settings_test",
        module_path,
    )
    module = importlib.util.module_from_spec(spec)
    module.__package__ = "marketplace_connector.addons.sce_connector_ml.models"
    spec.loader.exec_module(module)
    return module.SceGlobalSettings


class _Params:
    def __init__(self, values=None):
        self.values = values or {}

    def sudo(self):
        return self

    def get_param(self, key, default=""):
        return self.values.get(key, default)


class _Env(dict):
    def __getitem__(self, item):
        return super().__getitem__(item)


CoreSecretService = _load_core_secret_service()
SceGlobalSettings = _load_sce_global_settings()


class CoreSecretServiceTests(unittest.TestCase):
    def setUp(self):
        self.env_key = Fernet.generate_key().decode()
        self.db_key = Fernet.generate_key().decode()

    def test_environment_keyring_has_priority(self):
        env = _Env({"ir.config_parameter": _Params({"sce.core.keyring": self.db_key})})
        keyring, source = CoreSecretService.resolve_runtime_keyring(
            env=env,
            environ={CoreSecretService.KEYRING_ENV: self.env_key},
        )
        self.assertEqual(keyring, self.env_key)
        self.assertEqual(source, "environment")

    def test_database_keyring_is_used_as_fallback(self):
        env = _Env({"ir.config_parameter": _Params({"sce.core.keyring": self.db_key})})
        keyring, source = CoreSecretService.resolve_runtime_keyring(env=env, environ={})
        self.assertEqual(keyring, self.db_key)
        self.assertEqual(source, "database")

    def test_resolve_runtime_keyring_trims_whitespace(self):
        env = _Env(
            {"ir.config_parameter": _Params({"sce.core.keyring": f"  {self.db_key}  "})}
        )
        keyring, source = CoreSecretService.resolve_runtime_keyring(
            env=env,
            environ={CoreSecretService.KEYRING_ENV: f"  {self.env_key}  "},
        )
        self.assertEqual(keyring, self.env_key)
        self.assertEqual(source, "environment")

    def test_resolve_runtime_keyring_returns_missing_tuple(self):
        env = _Env({"ir.config_parameter": _Params({})})
        self.assertEqual(
            CoreSecretService.resolve_runtime_keyring(env=env, environ={}),
            ("", False),
        )

    def test_missing_keyring_raises(self):
        with self.assertRaises(UserError):
            CoreSecretService(environ={})

    def test_invalid_database_keyring_raises(self):
        env = _Env({"ir.config_parameter": _Params({"sce.core.keyring": "invalid-key"})})
        with self.assertRaises(UserError):
            CoreSecretService.from_runtime(env=env, environ={})

    def test_encrypt_and_decrypt_with_database_keyring(self):
        env = _Env({"ir.config_parameter": _Params({"sce.core.keyring": self.db_key})})
        service = CoreSecretService.from_runtime(env=env, environ={})
        encrypted = service.encrypt("secret-value")
        self.assertNotEqual(encrypted, "secret-value")
        self.assertEqual(service.decrypt(encrypted), "secret-value")


class _SecretModel:
    def __init__(self, count):
        self.count = count

    def sudo(self):
        return self

    def search_count(self, domain):
        return self.count


class _SettingsRecord(SimpleNamespace):
    pass


class SceGlobalSettingsTests(unittest.TestCase):
    def setUp(self):
        self.db_key = Fernet.generate_key().decode()
        self.env_key = Fernet.generate_key().decode()

    def test_validate_database_keyring_blocks_rotation_with_active_secrets(self):
        env = _Env(
            {
                "ir.config_parameter": _Params({"sce.core.keyring": self.db_key}),
                "sce.credential.secret": _SecretModel(1),
            }
        )
        record = _SettingsRecord(env=env)
        with self.assertRaises(UserError):
            SceGlobalSettings._validate_database_keyring(
                record, Fernet.generate_key().decode()
            )

    def test_inverse_blocks_database_edit_while_env_keyring_is_active(self):
        writes = []
        record = _SettingsRecord(
            env=_Env({}),
            mercadolibre_client_id="id",
            mercadolibre_client_secret="secret",
            mercadolibre_redirect_uri="https://example.com/callback",
            sce_core_keyring=Fernet.generate_key().decode(),
        )
        record._config_parameter_values = lambda: {
            "sce_core_keyring": self.db_key,
            "mercadolibre_client_id": "",
            "mercadolibre_client_secret": "",
            "mercadolibre_redirect_uri": "",
        }
        record._write_config_values = lambda values: writes.append(values)
        with patch.object(
            CoreSecretService,
            "resolve_runtime_keyring",
            return_value=(self.env_key, "environment"),
        ):
            with self.assertRaises(UserError):
                SceGlobalSettings._inverse_config_values([record])
        self.assertEqual(writes, [])

    def test_inverse_allows_database_fallback_write_when_env_is_empty(self):
        writes = []
        record = _SettingsRecord(
            env=_Env({}),
            mercadolibre_client_id="id",
            mercadolibre_client_secret="secret",
            mercadolibre_redirect_uri="https://example.com/callback",
            sce_core_keyring=self.db_key,
        )
        record._config_parameter_values = lambda: {
            "sce_core_keyring": "",
            "mercadolibre_client_id": "",
            "mercadolibre_client_secret": "",
            "mercadolibre_redirect_uri": "",
        }
        record._write_config_values = lambda values: writes.append(values)
        with patch.object(
            CoreSecretService, "resolve_runtime_keyring", return_value=("", False)
        ):
            SceGlobalSettings._inverse_config_values([record])
        self.assertEqual(writes[0]["sce_core_keyring"], self.db_key)

    def test_unlink_is_forbidden(self):
        with self.assertRaises(UserError):
            SceGlobalSettings.unlink(_SettingsRecord())


if __name__ == "__main__":
    unittest.main()
