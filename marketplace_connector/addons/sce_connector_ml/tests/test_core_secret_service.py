import importlib.util
import os
import sys
import types
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
