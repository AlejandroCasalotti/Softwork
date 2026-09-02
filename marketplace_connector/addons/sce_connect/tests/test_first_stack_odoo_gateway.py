import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from odoo.addons.softwork_ecommerce_conector_base.services.odoo_external_connection_gateway import (
    OdooExternalConnectionGateway,
)


class FirstStackOdooGatewayTests(unittest.TestCase):
    def test_delega_operaciones_read_only_a_connection_service(self):
        connection = MagicMock()
        env = MagicMock()
        delegated = MagicMock()
        delegated.test_connection.return_value = {"status": "connected"}
        delegated.metadata.return_value = {"name": {"type": "char"}}
        delegated.read.return_value = [{"id": 1}]
        delegated.search.return_value = [1]
        delegated.search_read.return_value = [{"id": 1, "name": "Producto"}]
        module = SimpleNamespace(ConnectionService=MagicMock(return_value=delegated))

        with patch(
            "odoo.addons.softwork_ecommerce_conector_base.services.odoo_external_connection_gateway.importlib.import_module",
            return_value=module,
        ) as import_module:
            gateway = OdooExternalConnectionGateway(connection, env=env, session="session")

        module.ConnectionService.assert_called_once_with(connection, env=env, session="session")
        import_module.assert_called_once_with(
            "odoo.addons.sce_connect.services.connection_service"
        )
        self.assertEqual(gateway.test_connection(), {"status": "connected"})
        self.assertEqual(gateway.metadata("product.template"), {"name": {"type": "char"}})
        self.assertEqual(gateway.read("product.template", [1], ["name"]), [{"id": 1}])
        self.assertEqual(
            gateway.search("product.template", [["active", "=", True]], 0, 5, "id asc"),
            [1],
        )
        self.assertEqual(
            gateway.search_read(
                "product.template", [["active", "=", True]], ["id"], 0, 5, "id asc"
            ),
            [{"id": 1, "name": "Producto"}],
        )

        delegated.test_connection.assert_called_once_with()
        delegated.metadata.assert_called_once_with("product.template")
        delegated.read.assert_called_once_with("product.template", [1], ["name"])
        delegated.search.assert_called_once_with(
            "product.template",
            domain=[["active", "=", True]],
            offset=0,
            limit=5,
            order="id asc",
        )
        delegated.search_read.assert_called_once_with(
            "product.template",
            domain=[["active", "=", True]],
            fields=["id"],
            offset=0,
            limit=5,
            order="id asc",
        )

    def test_no_expone_operaciones_de_escritura(self):
        public_methods = {
            name for name in dir(OdooExternalConnectionGateway) if not name.startswith("_")
        }
        self.assertNotIn("create", public_methods)
        self.assertNotIn("write", public_methods)
        self.assertNotIn("unlink", public_methods)
        self.assertNotIn("execute", public_methods)


if __name__ == "__main__":
    unittest.main()
