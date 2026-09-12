import os
import unittest

from ..services.log_sanitizer import redact_json
from ..services.secret_storage import SecretStorage


class SecretStorageTests(unittest.TestCase):
    def setUp(self):
        self.key = SecretStorage.generate_master_key()
        self.storage = SecretStorage(master_key=self.key)

    def test_encrypt_decrypt(self):
        encrypted = self.storage.encrypt("api-key-value")
        self.assertNotEqual(encrypted, "api-key-value")
        self.assertEqual(self.storage.decrypt(encrypted), "api-key-value")

    def test_wrong_key_fails(self):
        encrypted = self.storage.encrypt("api-key-value")
        other = SecretStorage(master_key=SecretStorage.generate_master_key())
        with self.assertRaises(Exception):
            other.decrypt(encrypted)

    def test_missing_secret_fails(self):
        with self.assertRaises(Exception):
            self.storage.decrypt("")

    def test_master_key_is_external(self):
        with self.assertRaises(Exception):
            SecretStorage(environ={})

    def test_nested_redaction(self):
        payload = redact_json(
            {
                "Authorization": "Bearer token-value",
                "items": [{"refresh_token": "refresh-value"}],
                "safe": "visible",
            }
        )
        self.assertEqual(payload["Authorization"], "[REDACTED]")
        self.assertEqual(payload["items"][0]["refresh_token"], "[REDACTED]")
        self.assertEqual(payload["safe"], "visible")

    def test_json_string_redaction(self):
        payload = redact_json('{"api_key": "key-value", "name": "safe"}')
        self.assertEqual(payload["api_key"], "[REDACTED]")
        self.assertEqual(payload["name"], "safe")


if __name__ == "__main__":
    unittest.main()
