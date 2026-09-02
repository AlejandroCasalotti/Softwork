import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from ..services.errors import ApiError, AuthenticationError, NetworkError, PermissionError
from ..services.odoo_external_product_service import OdooExternalProductService


TEMPLATE_METADATA = {
    "id": {"type": "integer"},
    "name": {"type": "char"},
    "default_code": {"type": "char"},
    "barcode": {"type": "char"},
    "list_price": {"type": "float"},
    "standard_price": {"type": "float"},
    "active": {"type": "boolean"},
    "write_date": {"type": "datetime"},
    "categ_id": {"type": "many2one"},
    "description_sale": {"type": "text"},
    "product_variant_ids": {"type": "one2many"},
}

# Metadata realista y DISTINTA de la de template: sin list_price/standard_price/categ_id/
# description_sale/product_variant_ids, con product_tmpl_id/product_template_attribute_value_ids propios.
VARIANT_METADATA = {
    "id": {"type": "integer"},
    "product_tmpl_id": {"type": "many2one"},
    "name": {"type": "char"},
    "default_code": {"type": "char"},
    "barcode": {"type": "char"},
    "active": {"type": "boolean"},
    "write_date": {"type": "datetime"},
    "product_template_attribute_value_ids": {"type": "many2many"},
}


def metadata_by_model(model):
    if model == OdooExternalProductService.TEMPLATE_MODEL:
        return dict(TEMPLATE_METADATA)
    if model == OdooExternalProductService.VARIANT_MODEL:
        return dict(VARIANT_METADATA)
    raise AssertionError(f"metadata solicitada para modelo inesperado: {model}")


class FakeRecord:
    def __init__(self, values, rec_id):
        self.id = rec_id
        self.values = dict(values)

    def write(self, vals):
        self.values.update(vals)
        return True

    def __getattr__(self, name):
        return self.values.get(name)

    def __bool__(self):
        return True

    def __eq__(self, other):
        return isinstance(other, FakeRecord) and other.id == self.id


class EmptyRecordset:
    def __bool__(self):
        return False


class FakeMappingModel:
    def __init__(self):
        self.records = []
        self._next_id = 1

    def sudo(self):
        return self

    def search(self, domain, limit=None):
        conditions = {field: value for field, _op, value in domain}
        for record in self.records:
            if all(record.values.get(field) == value for field, value in conditions.items()):
                return record
        return EmptyRecordset()

    def create(self, values):
        record = FakeRecord(values, self._next_id)
        self._next_id += 1
        self.records.append(record)
        return record


def fake_env():
    return {"sce.external.product.mapping": FakeMappingModel()}


def fake_connection(conn_id=1, tenant_id=1, last_product_sync=None):
    connection = MagicMock()
    connection.id = conn_id
    connection.tenant_id.id = tenant_id
    connection.last_product_sync = last_product_sync
    return connection


def template_row(rec_id, write_date="2026-01-01 00:00:00", **overrides):
    row = {
        "id": rec_id,
        "name": f"Producto {rec_id}",
        "default_code": f"SKU{rec_id}",
        "barcode": False,
        "list_price": 10.0,
        "standard_price": 5.0,
        "active": True,
        "write_date": write_date,
        "categ_id": [1, "All"],
        "description_sale": "",
        "product_variant_ids": [rec_id],
    }
    row.update(overrides)
    return row


def variant_row(rec_id, tmpl_external_id, write_date="2026-01-01 00:00:00", **overrides):
    row = {
        "id": rec_id,
        "product_tmpl_id": [tmpl_external_id, f"Producto {tmpl_external_id}"],
        "name": f"Variante {rec_id}",
        "default_code": f"SKU-V{rec_id}",
        "barcode": False,
        "active": True,
        "write_date": write_date,
        "product_template_attribute_value_ids": [],
    }
    row.update(overrides)
    return row


class OdooExternalProductServiceTests(unittest.TestCase):
    def _service(self, connection=None, batch_size=None, env=None):
        connection = connection or fake_connection()
        return OdooExternalProductService(connection, env=env or fake_env(), batch_size=batch_size), connection

    @staticmethod
    def _configure_metadata(connection_service_class):
        connection_service_class.return_value.metadata.side_effect = metadata_by_model

    # -- Lectura básica -------------------------------------------------

    @patch("odoo.addons.sce_connect.services.odoo_external_product_service.ConnectionService")
    def test_connection_valida_lectura_de_productos(self, connection_service_class):
        self._configure_metadata(connection_service_class)
        connection_service_class.return_value.search_read.side_effect = [
            [template_row(1)],
            [],
        ]
        service, connection = self._service()
        summary = service.sync_products(full=True)
        self.assertEqual(summary["records_read"], 1)
        self.assertEqual(summary["records_created"], 1)
        connection.sudo().write.assert_called()

    @patch("odoo.addons.sce_connect.services.odoo_external_product_service.ConnectionService")
    def test_producto_nuevo_se_crea(self, connection_service_class):
        self._configure_metadata(connection_service_class)
        connection_service_class.return_value.search_read.side_effect = [[template_row(1)], []]
        service, _connection = self._service()
        summary = service.sync_products(full=True)
        self.assertEqual(summary["records_created"], 1)
        self.assertEqual(summary["records_updated"], 0)

    @patch("odoo.addons.sce_connect.services.odoo_external_product_service.ConnectionService")
    def test_producto_existente_se_actualiza(self, connection_service_class):
        self._configure_metadata(connection_service_class)
        connection_service_class.return_value.search_read.side_effect = [
            [template_row(1, list_price=10.0)],
            [],
            [template_row(1, list_price=15.0)],
            [],
        ]
        service, _connection = self._service()
        service.sync_products(full=True)
        summary = service.sync_products(full=True)
        self.assertEqual(summary["records_created"], 0)
        self.assertEqual(summary["records_updated"], 1)

    @patch("odoo.addons.sce_connect.services.odoo_external_product_service.ConnectionService")
    def test_reejecutar_sync_no_duplica(self, connection_service_class):
        self._configure_metadata(connection_service_class)
        connection_service_class.return_value.search_read.side_effect = [
            [template_row(1)],
            [],
            [template_row(1)],
            [],
        ]
        service, _connection = self._service()
        service.sync_products(full=True)
        service.sync_products(full=True)
        mapping_model = service.env["sce.external.product.mapping"]
        self.assertEqual(len(mapping_model.records), 1)

    @patch("odoo.addons.sce_connect.services.odoo_external_product_service.ConnectionService")
    def test_campo_remoto_inexistente_no_rompe_el_sync(self, connection_service_class):
        partial_template_metadata = dict(TEMPLATE_METADATA)
        del partial_template_metadata["description_sale"]

        def metadata_side_effect(model):
            if model == OdooExternalProductService.TEMPLATE_MODEL:
                return partial_template_metadata
            return dict(VARIANT_METADATA)

        connection_service_class.return_value.metadata.side_effect = metadata_side_effect
        connection_service_class.return_value.search_read.side_effect = [[template_row(1)], []]
        service, _connection = self._service()
        summary = service.sync_products(full=True)
        self.assertEqual(summary["records_created"], 1)
        mapping_model = service.env["sce.external.product.mapping"]
        template_mapping = next(
            r for r in mapping_model.records if r.values["external_model"] == OdooExternalProductService.TEMPLATE_MODEL
        )
        self.assertIn("description_sale", template_mapping.values["missing_fields_json"])

    @patch("odoo.addons.sce_connect.services.odoo_external_product_service.ConnectionService")
    def test_dos_tenants_dos_conexiones_no_se_mezclan(self, connection_service_class):
        self._configure_metadata(connection_service_class)
        shared_env = fake_env()

        connection_service_class.return_value.search_read.side_effect = [[template_row(1)], []]
        connection_a = fake_connection(conn_id=1, tenant_id=1)
        OdooExternalProductService(connection_a, env=shared_env).sync_products(full=True)

        connection_service_class.return_value.search_read.side_effect = [[template_row(1)], []]
        connection_b = fake_connection(conn_id=2, tenant_id=2)
        OdooExternalProductService(connection_b, env=shared_env).sync_products(full=True)

        mapping_model = shared_env["sce.external.product.mapping"]
        self.assertEqual(len(mapping_model.records), 2)
        connections_seen = {record.values["external_connection_id"] for record in mapping_model.records}
        self.assertEqual(connections_seen, {1, 2})

    def test_mapping_unique_constraint_definido(self):
        from ..models.sce_external_product_mapping import SceExternalProductMapping

        constraint = SceExternalProductMapping._uniq_external_identity
        self.assertIn(
            "UNIQUE(external_connection_id, external_model, external_id)",
            constraint._definition,
        )

    # -- 1. Variante en sync incremental: parent resuelto contra mapping persistente ----

    @patch("odoo.addons.sce_connect.services.odoo_external_product_service.ConnectionService")
    def test_variante_resuelve_parent_mapping_persistente_sin_template_en_el_run(self, connection_service_class):
        self._configure_metadata(connection_service_class)
        env = fake_env()
        mapping_model = env["sce.external.product.mapping"]
        template_mapping = mapping_model.create(
            {
                "external_connection_id": 1,
                "external_model": OdooExternalProductService.TEMPLATE_MODEL,
                "external_id": 10,
                "name": "Producto de una ejecución anterior",
            }
        )
        connection_service_class.return_value.search_read.side_effect = [
            [],  # template: sin cambios en este run
            [variant_row(99, tmpl_external_id=10)],  # variante modificada
        ]
        connection = fake_connection(conn_id=1, last_product_sync=datetime(2026, 1, 1))
        service = OdooExternalProductService(connection, env=env)
        summary = service.sync_products(full=False)

        self.assertEqual(summary["records_skipped"], 0)
        variant_mappings = [
            r for r in mapping_model.records if r.values["external_model"] == OdooExternalProductService.VARIANT_MODEL
        ]
        self.assertEqual(len(variant_mappings), 1)
        self.assertEqual(variant_mappings[0].values["parent_mapping_id"], template_mapping.id)

    @patch("odoo.addons.sce_connect.services.odoo_external_product_service.ConnectionService")
    def test_variante_sin_mapping_padre_se_omite_sin_crash(self, connection_service_class):
        self._configure_metadata(connection_service_class)
        connection_service_class.return_value.search_read.side_effect = [
            [],
            [variant_row(99, tmpl_external_id=404)],
        ]
        service, _connection = self._service()
        summary = service.sync_products(full=False)
        self.assertEqual(summary["records_skipped"], 1)
        mapping_model = service.env["sce.external.product.mapping"]
        self.assertEqual(len(mapping_model.records), 0)

    # -- 3. Errores de red/API/permisos --------------------------------

    @patch("odoo.addons.sce_connect.services.odoo_external_product_service.ConnectionService")
    def test_authentication_error_no_se_reintenta_y_se_propaga(self, connection_service_class):
        connection_service_class.return_value.metadata.side_effect = AuthenticationError("bad token")
        service, _connection = self._service()
        with self.assertRaises(AuthenticationError):
            service.sync_products(full=True)

    @patch("odoo.addons.sce_connect.services.odoo_external_product_service.ConnectionService")
    def test_permission_error_no_se_reintenta_y_se_propaga(self, connection_service_class):
        connection_service_class.return_value.metadata.side_effect = PermissionError("forbidden")
        service, connection = self._service()
        with self.assertLogs(level="ERROR") as captured:
            with self.assertRaises(PermissionError):
                service.sync_products(full=True)
        self.assertTrue(any(f"connection={connection.id}" in line for line in captured.output))
        connection.sudo().write.assert_not_called()

    @patch("odoo.addons.sce_connect.services.odoo_external_product_service.ConnectionService")
    def test_network_error_se_reintenta_y_luego_funciona(self, connection_service_class):
        connection_service_class.return_value.metadata.side_effect = [
            NetworkError("timeout"),
            TEMPLATE_METADATA,
            VARIANT_METADATA,
        ]
        connection_service_class.return_value.search_read.side_effect = [[template_row(1)], []]
        service, _connection = self._service()
        summary = service.sync_products(full=True)
        self.assertEqual(summary["records_created"], 1)

    @patch("odoo.addons.sce_connect.services.odoo_external_product_service.ConnectionService")
    def test_network_error_agota_reintentos_y_se_propaga_con_log_contextual(self, connection_service_class):
        connection_service_class.return_value.metadata.side_effect = NetworkError("timeout persistente")
        service, connection = self._service()
        with self.assertLogs(level="ERROR") as captured:
            with self.assertRaises(NetworkError):
                service.sync_products(full=True)
        self.assertTrue(any("reintentos agotados" in line for line in captured.output))
        connection.sudo().write.assert_not_called()

    @patch("odoo.addons.sce_connect.services.odoo_external_product_service.ConnectionService")
    def test_api_error_agota_reintentos_y_se_propaga(self, connection_service_class):
        connection_service_class.return_value.metadata.side_effect = ApiError("HTTP 503")
        service, connection = self._service()
        with self.assertLogs(level="ERROR") as captured:
            with self.assertRaises(ApiError):
                service.sync_products(full=True)
        self.assertTrue(any("reintentos agotados" in line for line in captured.output))
        connection.sudo().write.assert_not_called()

    # -- 4. Checkpoint --------------------------------------------------

    @patch("odoo.addons.sce_connect.services.odoo_external_product_service.ConnectionService")
    @patch("odoo.addons.sce_connect.services.odoo_external_product_service.datetime")
    def test_checkpoint_avanza_con_el_valor_exacto_de_started_at(self, datetime_mock, connection_service_class):
        self._configure_metadata(connection_service_class)
        connection_service_class.return_value.search_read.side_effect = [[template_row(1)], []]
        fixed_with_tz = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
        datetime_mock.now.return_value = fixed_with_tz
        service, connection = self._service()
        service.sync_products(full=True)
        connection.sudo().write.assert_called_with({"last_product_sync": datetime(2026, 5, 1, 12, 0, 0)})

    @patch("odoo.addons.sce_connect.services.odoo_external_product_service.ConnectionService")
    def test_checkpoint_no_avanza_si_falla_pagina_intermedia(self, connection_service_class):
        self._configure_metadata(connection_service_class)
        connection_service_class.return_value.search_read.side_effect = [
            [template_row(1), template_row(2)],  # página 1: llena, pide página 2
            AuthenticationError("bad token en página 2"),
        ]
        service, connection = self._service(batch_size=2)
        with self.assertRaises(AuthenticationError):
            service.sync_products(full=True)
        connection.sudo().write.assert_not_called()

    # -- 5. Sync incremental: dominio real enviado a search_read --------

    @patch("odoo.addons.sce_connect.services.odoo_external_product_service.ConnectionService")
    def test_full_false_con_checkpoint_envia_filtro_write_date(self, connection_service_class):
        self._configure_metadata(connection_service_class)
        connection_service_class.return_value.search_read.side_effect = [[], []]
        checkpoint = datetime(2026, 6, 1, 8, 30, 0)
        connection = fake_connection(last_product_sync=checkpoint)
        service = OdooExternalProductService(connection, env=fake_env())
        service.sync_products(full=False)
        first_call_kwargs = connection_service_class.return_value.search_read.call_args_list[0].kwargs
        self.assertEqual(first_call_kwargs["domain"], [("write_date", ">", "2026-06-01 08:30:00")])

    @patch("odoo.addons.sce_connect.services.odoo_external_product_service.ConnectionService")
    def test_full_false_sin_checkpoint_se_comporta_como_primera_sincronizacion(self, connection_service_class):
        self._configure_metadata(connection_service_class)
        connection_service_class.return_value.search_read.side_effect = [[], []]
        connection = fake_connection(last_product_sync=None)
        service = OdooExternalProductService(connection, env=fake_env())
        service.sync_products(full=False)
        first_call_kwargs = connection_service_class.return_value.search_read.call_args_list[0].kwargs
        self.assertEqual(first_call_kwargs["domain"], [])

    # -- 6. Metadata realista y distinta: campos enviados por modelo -----

    @patch("odoo.addons.sce_connect.services.odoo_external_product_service.ConnectionService")
    def test_campos_enviados_respetan_metadata_real_por_modelo(self, connection_service_class):
        self._configure_metadata(connection_service_class)
        connection_service_class.return_value.search_read.side_effect = [
            [template_row(1)],
            [variant_row(2, tmpl_external_id=1)],
        ]
        service, _connection = self._service()
        service.sync_products(full=True)
        calls = connection_service_class.return_value.search_read.call_args_list
        template_call, variant_call = calls[0], calls[1]
        self.assertEqual(template_call.args[0], OdooExternalProductService.TEMPLATE_MODEL)
        self.assertEqual(sorted(template_call.kwargs["fields"]), sorted(OdooExternalProductService.TEMPLATE_FIELDS))
        self.assertEqual(variant_call.args[0], OdooExternalProductService.VARIANT_MODEL)
        self.assertEqual(sorted(variant_call.kwargs["fields"]), sorted(OdooExternalProductService.VARIANT_FIELDS))
        # Campos exclusivos de un modelo no deben filtrarse al otro.
        self.assertNotIn("list_price", variant_call.kwargs["fields"])
        self.assertNotIn("product_tmpl_id", template_call.kwargs["fields"])

    # -- 7. Paginación ----------------------------------------------------

    @patch("odoo.addons.sce_connect.services.odoo_external_product_service.ConnectionService")
    def test_paginacion_offset_incrementa_por_batch_size_y_usa_order_id_asc(self, connection_service_class):
        self._configure_metadata(connection_service_class)
        page1 = [template_row(i) for i in range(1, 3)]  # len 2 == batch_size -> pide página 2
        page2 = [template_row(3)]  # len 1 < batch_size -> termina
        connection_service_class.return_value.search_read.side_effect = [page1, page2]
        service, _connection = self._service(batch_size=2)
        records, _missing = service.list_templates()
        self.assertEqual(len(records), 3)
        calls = connection_service_class.return_value.search_read.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0].kwargs["offset"], 0)
        self.assertEqual(calls[1].kwargs["offset"], 2)
        for call in calls:
            self.assertEqual(call.kwargs["order"], "id asc")
            self.assertEqual(call.kwargs["limit"], 2)

    # -- 8. Identidad protegida por la tupla, no por default_code/barcode/name ----

    @patch("odoo.addons.sce_connect.services.odoo_external_product_service.ConnectionService")
    def test_identidad_protegida_por_tupla_no_por_default_code_o_name(self, connection_service_class):
        self._configure_metadata(connection_service_class)
        connection_service_class.return_value.search_read.side_effect = [
            [template_row(1, default_code="OLD-SKU", name="Nombre viejo")],
            [],
            [template_row(1, default_code="NEW-SKU", name="Nombre nuevo")],
            [],
        ]
        service, _connection = self._service()
        service.sync_products(full=True)
        service.sync_products(full=True)
        mapping_model = service.env["sce.external.product.mapping"]
        template_mappings = [
            r for r in mapping_model.records if r.values["external_model"] == OdooExternalProductService.TEMPLATE_MODEL
        ]
        self.assertEqual(len(template_mappings), 1)
        self.assertEqual(template_mappings[0].values["default_code"], "NEW-SKU")
        self.assertEqual(template_mappings[0].values["name"], "Nombre nuevo")


if __name__ == "__main__":
    unittest.main()

