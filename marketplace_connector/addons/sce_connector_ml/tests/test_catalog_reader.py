import unittest
from unittest.mock import MagicMock

from odoo.exceptions import UserError

from ..services.catalog_reader import MercadoLibreCatalogReader
from ..services.ml_provider import MercadoLibreProvider
from ..services.provider import MercadoLibreExternalProvider
from odoo.addons.softwork_provider_mercadolibre.services.provider import (
    MercadoLibreExternalProvider as AlternateMercadoLibreExternalProvider,
)


def item(item_id="MLA1", sku=None, seller_custom_field=None, variations=None):
    attributes = [] if sku is None else [{"id": "SELLER_SKU", "value_name": sku}]
    return {
        "id": item_id,
        "attributes": attributes,
        "seller_custom_field": seller_custom_field,
        "variations": variations or [],
    }


def page(results, total=None, offset=0, limit=100, scroll_id=None):
    payload = {"results": results, "paging": {"total": len(results) if total is None else total, "offset": offset, "limit": limit}}
    if scroll_id:
        payload["scroll_id"] = scroll_id
    return payload


class MercadoLibreCatalogReaderTests(unittest.TestCase):
    def setUp(self):
        self.provider = MagicMock()
        self.provider.get_authenticated_user_id.return_value = "123"
        self.reader = MercadoLibreCatalogReader(self.provider)

    def test_lista_vacia(self):
        self.provider.list_item_ids.return_value = page([], total=0)
        result = self.reader.list_item_ids()
        self.assertEqual(result["item_ids"], [])
        self.assertEqual(result["paging"]["total"], 0)
        self.provider.list_item_ids.assert_called_once_with("123", offset=0, limit=50)

    def test_una_pagina_con_publicaciones(self):
        self.provider.list_item_ids.return_value = page(["MLA1", "MLA2"], total=2)
        result = self.reader.list_item_ids(offset=0, limit=100)
        self.assertEqual(result["item_ids"], ["MLA1", "MLA2"])
        self.provider.list_item_ids.assert_called_once_with("123", offset=0, limit=100)

    def test_multiples_paginas_normal_preservan_ids_unicos(self):
        self.provider.list_item_ids.side_effect = [
            page([f"MLA{i}" for i in range(100)], total=250),
            page([f"MLA{i}" for i in range(100, 200)], total=250, offset=100),
            page([f"MLA{i}" for i in range(200, 250)], total=250, offset=200),
        ]
        result = self.reader.list_all_item_ids()
        self.assertEqual(result["count"], 250)
        self.assertEqual(len(set(result["item_ids"])), 250)
        self.assertEqual(
            self.provider.list_item_ids.call_args_list[1].kwargs,
            {"offset": 100, "limit": 100},
        )

    def test_limite_maximo_y_offset_invalidos_son_rechazados(self):
        for kwargs in ({"limit": 101}, {"limit": 0}, {"offset": -1}):
            with self.subTest(kwargs=kwargs), self.assertRaises(UserError):
                self.reader.list_item_ids(**kwargs)
        self.provider.list_item_ids.assert_not_called()

    def test_catalogo_exactamente_mil_items_usa_offset(self):
        pages = [page([f"MLA{offset + index}" for index in range(100)], total=1000, offset=offset) for offset in range(0, 1000, 100)]
        self.provider.list_item_ids.side_effect = pages
        result = self.reader.list_all_item_ids()
        self.assertEqual(result["count"], 1000)
        self.assertEqual(self.provider.list_item_ids.call_count, 10)
        self.assertFalse(any("scroll_id" in call.kwargs for call in self.provider.list_item_ids.call_args_list))

    def test_catalogo_mayor_a_mil_usa_scan_y_scroll_id(self):
        self.provider.list_item_ids.side_effect = [
            page(["ignored"], total=1001),
            page(["MLA1", "MLA2"], total=1001, scroll_id="first"),
            page(["MLA3"], total=1001, scroll_id="second"),
            page([], total=1001),
        ]
        result = self.reader.list_all_item_ids()
        self.assertEqual(result["item_ids"], ["MLA1", "MLA2", "MLA3"])
        scan_calls = self.provider.list_item_ids.call_args_list[1:]
        self.assertEqual(scan_calls[0].kwargs, {"limit": 100, "scroll_id": None})
        self.assertEqual(scan_calls[1].kwargs, {"limit": 100, "scroll_id": "first"})
        self.assertEqual(scan_calls[2].kwargs, {"limit": 100, "scroll_id": "second"})

    def test_scan_detecta_scroll_id_repetido(self):
        self.provider.list_item_ids.side_effect = [
            page([], total=1001),
            page(["MLA1"], total=1001, scroll_id="same"),
            page(["MLA2"], total=1001, scroll_id="same"),
        ]
        with self.assertRaises(UserError):
            self.reader.list_all_item_ids()

    def test_deduplica_ids_sin_perder_orden(self):
        self.provider.list_item_ids.return_value = page(["MLA1", "MLA2", "MLA1"], total=3)
        self.assertEqual(self.reader.list_item_ids()["item_ids"], ["MLA1", "MLA2"])

    def test_item_simple_con_seller_sku(self):
        self.provider.get_item.return_value = {"item": item(sku="ABC-001", seller_custom_field="legacy")}
        result = self.reader.get_item("MLA1")
        self.assertEqual(result["canonical_sku"], "ABC-001")
        self.assertEqual(result["seller_custom_field"], "legacy")
        self.assertEqual(result["variations"], [])
        self.provider.get_item.assert_called_once_with("MLA1", params={"include_attributes": "all"})

    def test_seller_custom_field_no_se_convierte_en_sku(self):
        self.provider.get_item.return_value = {"item": item(seller_custom_field="legacy-only")}
        result = self.reader.get_item("MLA1")
        self.assertFalse(result["canonical_sku"])
        self.assertEqual(result["seller_custom_field"], "legacy-only")

    def test_variaciones_con_sku_y_custom_field_separados(self):
        variations = [
            {"id": 10, "attributes": [{"id": "SELLER_SKU", "value_name": "RED-M"}], "seller_custom_field": "legacy-red"},
            {"id": 11, "attributes": [], "seller_custom_field": "legacy-blue"},
        ]
        self.provider.get_item.return_value = {"item": item(variations=variations)}
        result = self.reader.get_item("MLA1")
        self.assertEqual(result["variations"][0]["variation_id"], 10)
        self.assertEqual(result["variations"][0]["canonical_sku"], "RED-M")
        self.assertEqual(result["variations"][1]["canonical_sku"], False)
        self.assertEqual(result["variations"][1]["seller_custom_field"], "legacy-blue")

    def test_seller_sku_y_sku_no_sustituyen_el_atributo_seller_sku(self):
        self.provider.get_item.return_value = {
            "item": {
                **item(),
                "sku": "not-canonical",
                "seller_sku": "not-canonical-either",
            }
        }
        result = self.reader.get_item("MLA1")
        self.assertFalse(result["canonical_sku"])

    def test_seller_sku_attribute_has_priority_among_attributes(self):
        self.provider.get_item.return_value = {
            "item": {
                **item(),
                "attributes": [
                    {"id": "BRAND", "value_name": "Softwork"},
                    {"id": "SELLER_SKU", "value_name": "ABC-001"},
                ],
            }
        }
        self.assertEqual(self.reader.get_item("MLA1")["canonical_sku"], "ABC-001")

    def test_item_id_vacio_falla_sin_consultar_provider(self):
        with self.assertRaises(UserError):
            self.reader.get_item("  ")
        self.provider.get_item.assert_not_called()

    def test_variations_invalidas_rechazan_respuesta(self):
        self.provider.get_item.return_value = {"item": {**item(), "variations": "invalid"}}
        with self.assertRaises(UserError):
            self.reader.get_item("MLA1")

    def test_errores_http_401_403_y_404_se_propagan(self):
        for status in (401, 403, 404):
            with self.subTest(status=status):
                self.provider.get_item.side_effect = UserError(f"HTTP {status}")
                with self.assertRaisesRegex(UserError, f"HTTP {status}"):
                    self.reader.get_item("MLA1")
                self.provider.get_item.reset_mock()
                self.provider.get_item.side_effect = None

    def test_respuesta_invalida_y_errores_del_provider_se_propagan(self):
        self.provider.list_item_ids.return_value = {"results": "invalid"}
        with self.assertRaises(UserError):
            self.reader.list_item_ids()
        self.provider.get_item.side_effect = UserError("HTTP 401")
        with self.assertRaisesRegex(UserError, "HTTP 401"):
            self.reader.get_item("MLA1")

    def test_aislamiento_por_provider(self):
        provider_a = MagicMock()
        provider_a.get_authenticated_user_id.return_value = "seller-a"
        provider_a.list_item_ids.return_value = page([], total=0)
        provider_b = MagicMock()
        provider_b.get_authenticated_user_id.return_value = "seller-b"
        provider_b.list_item_ids.return_value = page([], total=0)
        MercadoLibreCatalogReader(provider_a).list_item_ids()
        MercadoLibreCatalogReader(provider_b).list_item_ids()
        provider_a.list_item_ids.assert_called_once_with("seller-a", offset=0, limit=50)
        provider_b.list_item_ids.assert_called_once_with("seller-b", offset=0, limit=50)

    def test_list_items_reutiliza_get_item_y_no_escribe_modelos_odoo(self):
        self.provider.list_item_ids.return_value = page(["MLA1"], total=1)
        self.provider.get_item.return_value = {"item": item("MLA1", sku="ABC")}
        result = self.reader.list_items()
        self.assertEqual(result["items"][0]["item_id"], "MLA1")
        self.provider.get_item.assert_called_once_with("MLA1", params={"include_attributes": "all"})

    def test_reader_no_expone_operaciones_de_escritura(self):
        public_methods = {name for name in dir(MercadoLibreCatalogReader) if not name.startswith("_")}
        for method in ("create", "write", "unlink", "publish", "update_stock", "update_price"):
            self.assertNotIn(method, public_methods)


class MercadoLibreProviderCatalogContractTests(unittest.TestCase):
    def setUp(self):
        self.account = MagicMock()
        self.account.external_user_id = "555"
        self.provider = MercadoLibreProvider(MagicMock(), self.account)
        self.provider._request = MagicMock()

    def test_list_item_ids_reuses_transport_with_get(self):
        self.provider._request.return_value = {"results": [], "paging": {}}
        self.provider.list_item_ids("555", offset=100, limit=100)
        self.provider._request.assert_called_once_with(
            "GET", "/users/555/items/search", params={"limit": 100, "offset": 100}
        )

    def test_list_item_ids_scan_reuses_transport_with_get(self):
        self.provider._request.return_value = {"results": [], "paging": {}}
        self.provider.list_item_ids("555", limit=100, scroll_id="scroll")
        self.provider._request.assert_called_once_with(
            "GET", "/users/555/items/search", params={"limit": 100, "search_type": "scan", "scroll_id": "scroll"}
        )

    def test_get_item_with_attributes_reuses_transport_with_get(self):
        self.provider._request.return_value = {"id": "MLA1"}
        result = self.provider.get_item("MLA1", params={"include_attributes": "all"})
        self.assertEqual(result["item"], {"id": "MLA1"})
        self.provider._request.assert_called_once_with(
            "GET", "/items/MLA1", params={"include_attributes": "all"}
        )

    def test_authenticated_user_id_reuses_account_before_network(self):
        self.assertEqual(self.provider.get_authenticated_user_id(), "555")
        self.provider._request.assert_not_called()

    def test_external_wrapper_delegates_catalog_operations(self):
        wrapper = MercadoLibreExternalProvider(MagicMock(), self.account)
        wrapper._delegate = MagicMock()
        wrapper._delegate.get_authenticated_user_id.return_value = "555"
        self.assertEqual(wrapper.get_authenticated_user_id(), "555")
        wrapper.list_item_ids("555", offset=0, limit=100)
        wrapper.get_item("MLA1", params={"include_attributes": "all"})
        wrapper._delegate.list_item_ids.assert_called_once_with("555", offset=0, limit=100, scroll_id=None)
        wrapper._delegate.get_item.assert_called_once_with("MLA1", params={"include_attributes": "all"})

    def test_alternate_external_wrapper_delegates_authenticated_user_id(self):
        wrapper = AlternateMercadoLibreExternalProvider(MagicMock(), self.account)
        wrapper._delegate = MagicMock()
        wrapper._delegate.get_authenticated_user_id.return_value = "555"

        self.assertEqual(wrapper.get_authenticated_user_id(), "555")
        wrapper._delegate.get_authenticated_user_id.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
