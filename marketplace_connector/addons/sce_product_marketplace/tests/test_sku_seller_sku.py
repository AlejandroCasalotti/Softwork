# -*- coding: utf-8 -*-
import json
import unittest
from unittest.mock import MagicMock, patch

from odoo.exceptions import UserError

from ..services.publication_service import MarketplacePublicationService


class MarketplacePublicationSKUTests(unittest.TestCase):
    """Tests para la implementación de SELLER_SKU en publicaciones ML."""

    def setUp(self):
        """Inicializar servicio y mocks."""
        self.service = MagicMock(spec=MarketplacePublicationService)
        # Usar los métodos reales del servicio
        self.service._get_category_seller_sku_info = MarketplacePublicationService._get_category_seller_sku_info.__get__(self.service)
        self.service._build_payload = MarketplacePublicationService._build_payload.__get__(self.service)
        self.service.env = MagicMock()

    def _build_publication_mock(self, category_id="MLA1055", variant_count=1, default_codes=None):
        """Helper para crear mock de publicación."""
        publication = MagicMock()
        publication.id = 1
        publication.display_name = "Test Publication"
        publication.product_tmpl_id.id = 10
        publication.account_id.id = 100
        publication.external_id = False
        publication.external_status = False
        publication.category_ref = category_id
        publication.title = "Test Product"
        publication.price = 100.0
        publication.effective_qty = 50
        publication.price_uom_id = None
        publication.product_tmpl_id.uom_id = MagicMock()
        publication.product_tmpl_id.uom_id._compute_quantity.return_value = 1.0
        publication.attributes_json = "[]"
        publication.pictures_json = "[]"
        publication.sale_terms_json = "[]"
        publication.provider_data_json = "{}"
        publication.listing_type = "gold"
        publication.condition = "new"
        publication.shipping_mode = "me2"

        # Crear variantes
        variants = []
        for i in range(variant_count):
            variant = MagicMock()
            variant.id = 20 + i
            variant.default_code = default_codes[i] if default_codes and i < len(default_codes) else f"SKU-{i}"
            variant.qty_available = 25
            variant.lst_price = 100.0
            variant.product_template_attribute_value_ids = []
            variants.append(variant)

        publication.product_tmpl_id.product_variant_ids.filtered.return_value = variants

        return publication

    def _build_category_response_mock(self, has_seller_sku=True, allow_variations=True):
        """Helper para crear respuesta de atributos de categoría."""
        items = []
        if has_seller_sku:
            items.append({
                "id": "SELLER_SKU",
                "name": "SKU del Vendedor",
                "value_type": "string",
                "required": False,
                "allow_variations": allow_variations,
                "values": []
            })
        items.extend([
            {
                "id": "BRAND",
                "name": "Marca",
                "value_type": "string",
                "required": True,
                "allow_variations": False,
                "values": []
            }
        ])
        return {
            "ok": True,
            "items": items
        }

    def test_01_simple_product_with_seller_sku_capability(self):
        """TEST 1: Producto simple + categoría con SELLER_SKU.
        
        Debe agregar atributo SELLER_SKU con el default_code de la variante.
        """
        publication = self._build_publication_mock(
            category_id="MLA1055",
            variant_count=1,
            default_codes=["ABC123"]
        )

        # Mock provider
        provider_mock = MagicMock()
        provider_mock.get_category_attributes.return_value = self._build_category_response_mock(
            has_seller_sku=True
        )
        self.service.env.__getitem__.return_value.get_provider.return_value = provider_mock

        # Ejecutar
        payload = self.service._build_payload(publication)

        # Verificar
        self.assertIn("attributes", payload)
        seller_sku_list = [a for a in payload["attributes"] if a.get("id") == "SELLER_SKU"]
        self.assertEqual(len(seller_sku_list), 1, "Debe haber exactamente un SELLER_SKU")
        self.assertEqual(seller_sku_list[0]["value_name"], "ABC123")

    def test_02_simple_product_without_seller_sku_capability(self):
        """TEST 2: Producto simple + categoría sin SELLER_SKU.
        
        No debe agregar SELLER_SKU automáticamente.
        """
        publication = self._build_publication_mock(
            category_id="MLA1055",
            variant_count=1,
            default_codes=["ABC123"]
        )

        # Mock provider: categoría sin SELLER_SKU
        provider_mock = MagicMock()
        provider_mock.get_category_attributes.return_value = self._build_category_response_mock(
            has_seller_sku=False
        )
        self.service.env.__getitem__.return_value.get_provider.return_value = provider_mock

        # Ejecutar
        payload = self.service._build_payload(publication)

        # Verificar
        seller_sku_list = [a for a in payload.get("attributes", []) if a.get("id") == "SELLER_SKU"]
        self.assertEqual(len(seller_sku_list), 0, "No debe haber SELLER_SKU")

    def test_03_variant_with_seller_sku_allow_variations(self):
        """TEST 3: Producto con variantes + allow_variations=True.
        
        Cada variante debe contener su SELLER_SKU correspondiente.
        """
        publication = self._build_publication_mock(
            category_id="MLA1055",
            variant_count=2,
            default_codes=["SKU-ROJO", "SKU-AZUL"]
        )

        # Mock provider: SELLER_SKU con allow_variations=True
        provider_mock = MagicMock()
        provider_mock.get_category_attributes.return_value = self._build_category_response_mock(
            has_seller_sku=True,
            allow_variations=True
        )
        self.service.env.__getitem__.return_value.get_provider.return_value = provider_mock

        # Ejecutar
        payload = self.service._build_payload(publication)

        # Verificar
        self.assertIn("variations", payload)
        self.assertEqual(len(payload["variations"]), 2)

        for i, variation in enumerate(payload["variations"]):
            expected_sku = ["SKU-ROJO", "SKU-AZUL"][i]
            seller_sku_list = [a for a in variation.get("attributes", []) if a.get("id") == "SELLER_SKU"]
            self.assertEqual(len(seller_sku_list), 1, f"Variation {i} debe tener SELLER_SKU")
            self.assertEqual(seller_sku_list[0]["value_name"], expected_sku)

    def test_04_variant_without_allow_variations(self):
        """TEST 4: Producto con variantes + allow_variations=False.
        
        No debe agregar SELLER_SKU dentro de variation.attributes.
        """
        publication = self._build_publication_mock(
            category_id="MLA1055",
            variant_count=2,
            default_codes=["SKU-ROJO", "SKU-AZUL"]
        )

        # Mock provider: SELLER_SKU con allow_variations=False
        provider_mock = MagicMock()
        provider_mock.get_category_attributes.return_value = self._build_category_response_mock(
            has_seller_sku=True,
            allow_variations=False
        )
        self.service.env.__getitem__.return_value.get_provider.return_value = provider_mock

        # Ejecutar
        payload = self.service._build_payload(publication)

        # Verificar
        for variation in payload.get("variations", []):
            seller_sku_list = [a for a in variation.get("attributes", []) if a.get("id") == "SELLER_SKU"]
            self.assertEqual(len(seller_sku_list), 0, "No debe haber SELLER_SKU en variation")

    def test_05_seller_custom_field_preserved(self):
        """TEST 5: seller_custom_field siempre se mantiene.
        
        La compatibilidad legacy debe preservarse en variaciones.
        """
        publication = self._build_publication_mock(
            category_id="MLA1055",
            variant_count=2,
            default_codes=["SKU-ROJO", "SKU-AZUL"]
        )

        provider_mock = MagicMock()
        provider_mock.get_category_attributes.return_value = self._build_category_response_mock(
            has_seller_sku=True,
            allow_variations=True
        )
        self.service.env.__getitem__.return_value.get_provider.return_value = provider_mock

        # Ejecutar
        payload = self.service._build_payload(publication)

        # Verificar
        for i, variation in enumerate(payload.get("variations", [])):
            expected_sku = ["SKU-ROJO", "SKU-AZUL"][i]
            self.assertIn("seller_custom_field", variation)
            self.assertEqual(variation["seller_custom_field"], expected_sku)

    def test_06_apply_variant_mappings_prioritizes_seller_sku(self):
        """TEST 6: En lectura, SELLER_SKU tiene prioridad sobre seller_custom_field.
        
        Cuando existe variation.attributes[id=SELLER_SKU], usarlo como SKU.
        """
        from ..models.marketplace_publication import MarketplacePublication

        publication = MagicMock(spec=MarketplacePublication)
        publication.product_tmpl_id.id = 10
        publication.ensure_one = MagicMock()

        # Simular respuesta desde MercadoLibre
        result = {
            "raw": {
                "variations": [
                    {
                        "id": "999",
                        "attributes": [
                            {
                                "id": "SELLER_SKU",
                                "value_name": "CANONICAL-SKU"
                            }
                        ],
                        "seller_custom_field": "LEGACY-SKU",
                    }
                ]
            }
        }

        # Mock de variant_model y mapping_model
        variant_model_mock = MagicMock()
        mapping_model_mock = MagicMock()
        publication.env.__getitem__.side_effect = lambda x: (
            variant_model_mock if x == "product.product" else mapping_model_mock
        )

        variant_model_mock.search.return_value = MagicMock()
        mapping_model_mock.search.return_value = MagicMock()

        # Ejecutar método real
        MarketplacePublication._apply_variant_mappings(publication, result, "EXT-123")

        # Verificar que se buscó el producto con el SKU canónico
        call_args = variant_model_mock.search.call_args
        self.assertIsNotNone(call_args)
        # El segundo arg del domain es el valor a buscar
        domain = call_args[0][0]
        # domain es: [("product_tmpl_id", "=", 10), ("default_code", "=", "CANONICAL-SKU")]
        self.assertIn(("default_code", "=", "CANONICAL-SKU"), domain)

    def test_07_apply_variant_mappings_fallback_legacy(self):
        """TEST 7: Sin SELLER_SKU, fallback a seller_custom_field.
        
        Si no hay attributes[id=SELLER_SKU], usar seller_custom_field.
        """
        from ..models.marketplace_publication import MarketplacePublication

        publication = MagicMock(spec=MarketplacePublication)
        publication.product_tmpl_id.id = 10
        publication.ensure_one = MagicMock()

        # Simular respuesta sin SELLER_SKU
        result = {
            "raw": {
                "variations": [
                    {
                        "id": "999",
                        "attributes": [],  # Sin SELLER_SKU
                        "seller_custom_field": "LEGACY-SKU",
                    }
                ]
            }
        }

        variant_model_mock = MagicMock()
        mapping_model_mock = MagicMock()
        publication.env.__getitem__.side_effect = lambda x: (
            variant_model_mock if x == "product.product" else mapping_model_mock
        )

        variant_model_mock.search.return_value = MagicMock()
        mapping_model_mock.search.return_value = MagicMock()

        # Ejecutar
        MarketplacePublication._apply_variant_mappings(publication, result, "EXT-123")

        # Verificar que se usó seller_custom_field
        call_args = variant_model_mock.search.call_args
        domain = call_args[0][0]
        self.assertIn(("default_code", "=", "LEGACY-SKU"), domain)

    def test_08_api_failure_graceful_degradation(self):
        """TEST 8: Si get_category_attributes() falla, continuar sin SELLER_SKU.
        
        No debe ser error fatal de publicación.
        """
        publication = self._build_publication_mock(
            category_id="MLA1055",
            variant_count=1,
            default_codes=["ABC123"]
        )

        # Mock provider que lanza excepción
        provider_mock = MagicMock()
        provider_mock.get_category_attributes.side_effect = Exception("API Error")
        self.service.env.__getitem__.return_value.get_provider.return_value = provider_mock

        # Ejecutar (no debe lanzar excepción)
        payload = self.service._build_payload(publication)

        # Verificar que la publicación continúa
        self.assertIn("attributes", payload)
        seller_sku_list = [a for a in payload["attributes"] if a.get("id") == "SELLER_SKU"]
        self.assertEqual(len(seller_sku_list), 0, "No debe agregar SELLER_SKU si API falla")

    def test_09_no_duplicate_seller_sku(self):
        """TEST 9: No duplicar SELLER_SKU si ya existe en attributes_json.
        
        Respetar valor manual si usuario lo agregó.
        """
        publication = self._build_publication_mock(
            category_id="MLA1055",
            variant_count=1,
            default_codes=["ABC123"]
        )

        # Usuario agregó SELLER_SKU manualmente
        publication.attributes_json = json.dumps([
            {
                "id": "SELLER_SKU",
                "value_name": "MANUAL-SKU"
            }
        ])

        provider_mock = MagicMock()
        provider_mock.get_category_attributes.return_value = self._build_category_response_mock(
            has_seller_sku=True
        )
        self.service.env.__getitem__.return_value.get_provider.return_value = provider_mock

        # Ejecutar
        payload = self.service._build_payload(publication)

        # Verificar
        seller_sku_list = [a for a in payload["attributes"] if a.get("id") == "SELLER_SKU"]
        self.assertEqual(len(seller_sku_list), 1, "Debe haber exactamente un SELLER_SKU")
        self.assertEqual(seller_sku_list[0]["value_name"], "MANUAL-SKU", "Debe respetar valor manual")

    def test_10_empty_default_code_skips_seller_sku(self):
        """TEST 10: Si variant.default_code está vacío, no agregar SELLER_SKU.
        
        Solo agregar si hay valor real.
        """
        publication = self._build_publication_mock(
            category_id="MLA1055",
            variant_count=1,
            default_codes=[""]  # Vacío
        )

        provider_mock = MagicMock()
        provider_mock.get_category_attributes.return_value = self._build_category_response_mock(
            has_seller_sku=True
        )
        self.service.env.__getitem__.return_value.get_provider.return_value = provider_mock

        # Ejecutar
        payload = self.service._build_payload(publication)

        # Verificar
        seller_sku_list = [a for a in payload.get("attributes", []) if a.get("id") == "SELLER_SKU"]
        self.assertEqual(len(seller_sku_list), 0, "No debe agregar SELLER_SKU si default_code está vacío")

    def test_11_normalize_variations_preserves_seller_sku_attributes(self):
        """La normalización compartida preserva attributes en ambos providers."""
        from odoo.addons.sce_connector_ml.services.ml_provider import MercadoLibreProvider
        from odoo.addons.softwork_ecommerce_conector_base.services.providers.ml_provider import (
            MercadoLibreProvider as CoreMercadoLibreProvider,
        )

        provider = object.__new__(CoreMercadoLibreProvider)
        provider._to_int = lambda value, default: int(value or default)
        provider._to_float = lambda value, default: float(value or default)
        attributes = [{"id": "SELLER_SKU", "value_name": "CANONICAL-SKU"}]

        normalized = provider._normalize_variations(
            {
                "variations": [
                    {
                        "available_quantity": 1,
                        "price": 10,
                        "attribute_combinations": [],
                        "attributes": attributes,
                    }
                ]
            }
        )

        self.assertEqual(normalized[0]["attributes"], attributes)
        self.assertIs(MercadoLibreProvider._normalize_variations, CoreMercadoLibreProvider._normalize_variations)


if __name__ == "__main__":
    unittest.main()
