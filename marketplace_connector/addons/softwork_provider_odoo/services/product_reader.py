from odoo.exceptions import UserError


class OdooExternalProductReader:
    """Read-only product catalog access through an existing OdooProvider."""

    MODEL = "product.product"
    DEFAULT_FIELDS = [
        "id",
        "product_tmpl_id",
        "default_code",
        "barcode",
        "active",
        "qty_available",
        "lst_price",
        "product_template_attribute_value_ids",
    ]

    def __init__(self, provider):
        self.provider = provider

    def _connection(self):
        uid, database, _user, password, models_rpc = self.provider._connect()
        return uid, database, password, models_rpc

    def _search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        uid, database, password, models_rpc = self._connection()
        options = {
            "fields": list(fields) if fields is not None else list(self.DEFAULT_FIELDS),
            "offset": offset,
        }
        if limit is not None:
            options["limit"] = limit
        if order:
            options["order"] = order
        return models_rpc.execute_kw(
            database,
            uid,
            password,
            self.MODEL,
            "search_read",
            [domain or []],
            options,
        )

    def get_product_by_sku(self, sku, fields=None):
        sku = (sku or "").strip()
        if not sku:
            raise UserError("La referencia interna / SKU no puede estar vacía.")
        products = self._search_read(
            domain=[("default_code", "=", sku)],
            fields=fields,
        )
        count = len(products)
        status = "no_match" if count == 0 else "match" if count == 1 else "conflict"
        return {
            "ok": True,
            "status": status,
            "sku": sku,
            "products": products,
            "count": count,
        }

    def search_products(self, domain=None, fields=None, offset=0, limit=None, order=None):
        return self._search_read(
            domain=domain,
            fields=fields,
            offset=offset,
            limit=limit,
            order=order,
        )

    def get_product_fields(self):
        uid, database, password, models_rpc = self._connection()
        return models_rpc.execute_kw(
            database,
            uid,
            password,
            self.MODEL,
            "fields_get",
            [],
            {"attributes": ["type", "readonly", "required"]},
        )
