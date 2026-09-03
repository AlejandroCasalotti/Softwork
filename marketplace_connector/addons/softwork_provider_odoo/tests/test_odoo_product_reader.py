import unittest
from unittest.mock import MagicMock

from odoo.exceptions import UserError

from ..services.product_reader import OdooExternalProductReader


class OdooExternalProductReaderTests(unittest.TestCase):
    def setUp(self):
        self.provider = MagicMock()
        self.models_rpc = MagicMock()
        self.provider._connect.return_value = (
            42,
            "external_odoo",
            "unused-user",
            "api-key-not-displayed",
            self.models_rpc,
        )
        self.reader = OdooExternalProductReader(self.provider)

    def _assert_search_read(self, *, domain, fields=None, offset=0, limit=None, order=None):
        options = {
            "fields": list(fields) if fields is not None else list(self.reader.DEFAULT_FIELDS),
            "offset": offset,
        }
        if limit is not None:
            options["limit"] = limit
        if order:
            options["order"] = order
        self.models_rpc.execute_kw.assert_called_once_with(
            "external_odoo",
            42,
            "api-key-not-displayed",
            "product.product",
            "search_read",
            [domain],
            options,
        )

    def test_sku_inexistente_returns_no_match(self):
        self.models_rpc.execute_kw.return_value = []

        result = self.reader.get_product_by_sku("ABC123")

        self.assertEqual(result, {
            "ok": True,
            "status": "no_match",
            "sku": "ABC123",
            "products": [],
            "count": 0,
        })
        self._assert_search_read(domain=[("default_code", "=", "ABC123")])

    def test_sku_unico_returns_match(self):
        product = {"id": 7, "default_code": "ABC123"}
        self.models_rpc.execute_kw.return_value = [product]

        result = self.reader.get_product_by_sku("ABC123")

        self.assertEqual(result["status"], "match")
        self.assertEqual(result["products"], [product])
        self.assertEqual(result["count"], 1)
        self._assert_search_read(domain=[("default_code", "=", "ABC123")])

    def test_sku_duplicado_returns_conflict_with_all_candidates(self):
        products = [
            {"id": 7, "default_code": "ABC123"},
            {"id": 8, "default_code": "ABC123"},
        ]
        self.models_rpc.execute_kw.return_value = products

        result = self.reader.get_product_by_sku("ABC123")

        self.assertEqual(result["status"], "conflict")
        self.assertEqual(result["products"], products)
        self.assertEqual(result["count"], 2)
        self._assert_search_read(domain=[("default_code", "=", "ABC123")])

    def test_sku_vacio_fails_without_remote_call(self):
        with self.assertRaises(UserError):
            self.reader.get_product_by_sku("   ")

        self.provider._connect.assert_not_called()
        self.models_rpc.execute_kw.assert_not_called()

    def test_connection_error_propagates(self):
        self.provider._connect.side_effect = UserError("connection failed")

        with self.assertRaisesRegex(UserError, "connection failed"):
            self.reader.get_product_by_sku("ABC123")

        self.models_rpc.execute_kw.assert_not_called()

    def test_xmlrpc_error_propagates(self):
        self.models_rpc.execute_kw.side_effect = RuntimeError("xmlrpc failed")

        with self.assertRaisesRegex(RuntimeError, "xmlrpc failed"):
            self.reader.get_product_by_sku("ABC123")

    def test_explicit_fields_are_sent_exactly(self):
        self.models_rpc.execute_kw.return_value = []

        self.reader.get_product_by_sku("ABC123", fields=["id", "default_code"])

        self._assert_search_read(
            domain=[("default_code", "=", "ABC123")],
            fields=["id", "default_code"],
        )

    def test_search_products_passes_read_only_arguments(self):
        self.models_rpc.execute_kw.return_value = [{"id": 7}]

        result = self.reader.search_products(
            domain=[("active", "=", True)],
            fields=["id"],
            offset=5,
            limit=10,
            order="id asc",
        )

        self.assertEqual(result, [{"id": 7}])
        self._assert_search_read(
            domain=[("active", "=", True)],
            fields=["id"],
            offset=5,
            limit=10,
            order="id asc",
        )

    def test_get_product_fields_uses_fields_get(self):
        metadata = {"default_code": {"type": "char"}}
        self.models_rpc.execute_kw.return_value = metadata

        result = self.reader.get_product_fields()

        self.assertEqual(result, metadata)
        self.models_rpc.execute_kw.assert_called_once_with(
            "external_odoo",
            42,
            "api-key-not-displayed",
            "product.product",
            "fields_get",
            [],
            {"attributes": ["type", "readonly", "required"]},
        )

    def test_reader_has_no_public_write_operations(self):
        public_methods = {
            name for name in dir(OdooExternalProductReader) if not name.startswith("_")
        }
        self.assertNotIn("create", public_methods)
        self.assertNotIn("write", public_methods)
        self.assertNotIn("unlink", public_methods)
        self.assertNotIn("execute", public_methods)

    def test_each_reader_uses_only_its_own_provider(self):
        provider_a = MagicMock()
        rpc_a = MagicMock()
        provider_a._connect.return_value = (1, "odoo_a", "key-a", "user-a", rpc_a)
        provider_b = MagicMock()
        rpc_b = MagicMock()
        provider_b._connect.return_value = (2, "odoo_b", "key-b", "user-b", rpc_b)
        rpc_a.execute_kw.return_value = []
        rpc_b.execute_kw.return_value = []

        OdooExternalProductReader(provider_a).get_product_by_sku("ABC123")
        OdooExternalProductReader(provider_b).get_product_by_sku("ABC123")

        rpc_a.execute_kw.assert_called_once()
        rpc_b.execute_kw.assert_called_once()
        self.assertEqual(rpc_a.execute_kw.call_args.args[0], "odoo_a")
        self.assertEqual(rpc_b.execute_kw.call_args.args[0], "odoo_b")

    def test_get_product_by_sku_does_not_force_limit_one(self):
        self.models_rpc.execute_kw.return_value = []

        self.reader.get_product_by_sku("ABC123")

        options = self.models_rpc.execute_kw.call_args.args[6]
        self.assertNotIn("limit", options)


if __name__ == "__main__":
    unittest.main()
