from odoo.exceptions import UserError


class MercadoLibreCatalogReader:
    """Read-only discovery and normalization of a MercadoLibre seller catalog."""

    DEFAULT_LIMIT = 50
    MAX_LIMIT = 100
    NORMAL_PAGING_MAX_TOTAL = 1000

    def __init__(self, provider):
        self.provider = provider

    @staticmethod
    def _canonical_sku(attributes):
        for attribute in attributes or []:
            if isinstance(attribute, dict) and attribute.get("id") == "SELLER_SKU":
                value = attribute.get("value_name")
                return str(value).strip() if value else False
        return False

    @classmethod
    def extract_variations(cls, item):
        variations = item.get("variations") if isinstance(item, dict) else []
        if not isinstance(variations, list):
            raise UserError("MercadoLibre devolvió variaciones con formato inválido.")
        return [
            {
                "variation_id": variation.get("id"),
                "canonical_sku": cls._canonical_sku(variation.get("attributes")),
                "seller_custom_field": variation.get("seller_custom_field") or False,
                "raw": variation,
            }
            for variation in variations
            if isinstance(variation, dict)
        ]

    @classmethod
    def normalize_item(cls, item):
        if not isinstance(item, dict) or not item.get("id"):
            raise UserError("MercadoLibre devolvió un item inválido.")
        return {
            "item_id": str(item["id"]),
            "canonical_sku": cls._canonical_sku(item.get("attributes")),
            "seller_custom_field": item.get("seller_custom_field") or False,
            "variations": cls.extract_variations(item),
            "raw": item,
        }

    def _seller_id(self):
        seller_id = self.provider.get_authenticated_user_id()
        if not seller_id:
            raise UserError("No se pudo identificar al vendedor de MercadoLibre.")
        return str(seller_id)

    def _validate_page(self, offset, limit):
        if not isinstance(offset, int) or offset < 0:
            raise UserError("El offset del catálogo debe ser un entero mayor o igual a cero.")
        if not isinstance(limit, int) or limit <= 0 or limit > self.MAX_LIMIT:
            raise UserError("El límite del catálogo debe ser un entero entre 1 y 100.")

    @staticmethod
    def _page_data(response):
        if not isinstance(response, dict):
            raise UserError("MercadoLibre devolvió una respuesta de catálogo inválida.")
        results = response.get("results")
        if not isinstance(results, list):
            raise UserError("MercadoLibre devolvió resultados de catálogo inválidos.")
        paging = response.get("paging") or {}
        if not isinstance(paging, dict):
            raise UserError("MercadoLibre devolvió paginación de catálogo inválida.")
        return results, paging

    @staticmethod
    def _unique_ids(item_ids):
        return list(dict.fromkeys(str(item_id) for item_id in item_ids if item_id))

    def list_item_ids(self, offset=0, limit=DEFAULT_LIMIT):
        self._validate_page(offset, limit)
        seller_id = self._seller_id()
        response = self.provider.list_item_ids(seller_id, offset=offset, limit=limit)
        results, paging = self._page_data(response)
        return {
            "ok": True,
            "seller_id": seller_id,
            "item_ids": self._unique_ids(results),
            "paging": paging,
        }

    def _list_scan_item_ids(self, seller_id):
        item_ids = []
        scroll_id = None
        previous_scroll_id = object()
        while True:
            response = self.provider.list_item_ids(
                seller_id, limit=self.MAX_LIMIT, scroll_id=scroll_id
            )
            results, paging = self._page_data(response)
            item_ids.extend(results)
            next_scroll_id = response.get("scroll_id") or paging.get("scroll_id")
            if not results or not next_scroll_id:
                return self._unique_ids(item_ids)
            if next_scroll_id == previous_scroll_id:
                raise UserError("MercadoLibre devolvió un scroll_id repetido.")
            previous_scroll_id = next_scroll_id
            scroll_id = next_scroll_id

    def list_all_item_ids(self):
        first_page = self.list_item_ids(offset=0, limit=self.MAX_LIMIT)
        total = first_page["paging"].get("total")
        if not isinstance(total, int) or total < 0:
            raise UserError("MercadoLibre no devolvió un total de catálogo válido.")
        seller_id = first_page["seller_id"]
        if total > self.NORMAL_PAGING_MAX_TOTAL:
            item_ids = self._list_scan_item_ids(seller_id)
        else:
            item_ids = list(first_page["item_ids"])
            offset = self.MAX_LIMIT
            while len(item_ids) < total:
                page = self.list_item_ids(offset=offset, limit=self.MAX_LIMIT)
                page_ids = page["item_ids"]
                if not page_ids:
                    break
                item_ids.extend(page_ids)
                offset += self.MAX_LIMIT
            item_ids = self._unique_ids(item_ids)
        return {"ok": True, "seller_id": seller_id, "item_ids": item_ids, "count": len(item_ids)}

    def get_item(self, item_id):
        item_id = str(item_id or "").strip()
        if not item_id:
            raise UserError("El ID de publicación MercadoLibre no puede estar vacío.")
        response = self.provider.get_item(item_id, params={"include_attributes": "all"})
        item = response.get("item") if isinstance(response, dict) else None
        return self.normalize_item(item)

    def list_items(self, offset=0, limit=DEFAULT_LIMIT):
        page = self.list_item_ids(offset=offset, limit=limit)
        return {
            **page,
            "items": [self.get_item(item_id) for item_id in page["item_ids"]],
        }
