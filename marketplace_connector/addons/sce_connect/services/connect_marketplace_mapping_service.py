from odoo import api, models
from odoo.exceptions import ValidationError


class SceConnectMarketplaceMappingService(models.AbstractModel):
    _name = "sce.connect.marketplace.mapping.service"
    _description = "SCE Connect Marketplace Mapping Service"

    def _validate_inputs(self, product_mapping, marketplace_account):
        if not product_mapping or not product_mapping.exists():
            raise ValidationError("El mapping de producto externo no existe.")
        if not marketplace_account or not marketplace_account.exists():
            raise ValidationError("La cuenta marketplace no existe.")
        if product_mapping.external_model != "product.product":
            raise ValidationError("La identidad marketplace requiere un mapping product.product.")
        connection = product_mapping.external_connection_id
        tenant = product_mapping.tenant_id
        connect_account = marketplace_account.connect_mercadolibre_account_id
        if not connection or not tenant:
            raise ValidationError("El producto externo no tiene una conexión o tenant válido.")
        if marketplace_account.provider_type != "mercadolibre":
            raise ValidationError("La cuenta marketplace no es compatible con Connect.")
        if not connect_account:
            raise ValidationError("La cuenta marketplace no tiene una cuenta Connect vinculada.")
        if marketplace_account.tenant_id != tenant:
            raise ValidationError("La cuenta marketplace y el producto externo pertenecen a tenants distintos.")
        if marketplace_account.external_connection_id != connection:
            raise ValidationError(
                "La cuenta marketplace utiliza una conexión Odoo distinta de la del producto externo."
            )
        if connect_account.tenant_id != tenant:
            raise ValidationError("El producto externo y la cuenta marketplace pertenecen a tenants distintos.")
        return connection, tenant

    def get_mapping(self, product_mapping, marketplace_account):
        self._validate_inputs(product_mapping, marketplace_account)
        return self.env["sce.connect.marketplace.mapping"].sudo().search(
            [
                ("external_product_mapping_id", "=", product_mapping.id),
                ("marketplace_account_id", "=", marketplace_account.id),
            ],
            limit=1,
        )

    @api.model
    def create_or_update_mapping(
        self,
        product_mapping,
        marketplace_account,
        marketplace_item_id,
        marketplace_variation_id=None,
        mapping_status="draft",
    ):
        connection, tenant = self._validate_inputs(product_mapping, marketplace_account)
        item_id = str(marketplace_item_id or "").strip()
        if not item_id:
            raise ValidationError("El item marketplace es obligatorio.")
        if mapping_status not in {"draft", "verified", "conflict", "inactive"}:
            raise ValidationError("El estado del mapping marketplace no es válido.")
        variation_id = str(marketplace_variation_id or "").strip() or False
        values = {
            "tenant_id": tenant.id,
            "external_connection_id": connection.id,
            "external_product_mapping_id": product_mapping.id,
            "marketplace_account_id": marketplace_account.id,
            "marketplace_item_id": item_id,
            "marketplace_variation_id": variation_id,
            "sku": product_mapping.default_code or False,
            "active": mapping_status != "inactive",
            "mapping_status": mapping_status,
        }
        Mapping = self.env["sce.connect.marketplace.mapping"].sudo()
        mapping = Mapping.search(
            [
                ("external_product_mapping_id", "=", product_mapping.id),
                ("marketplace_account_id", "=", marketplace_account.id),
            ],
            limit=1,
        )
        if mapping:
            mapping.write(values)
            return mapping, "updated"
        return Mapping.create(values), "created"

    @api.model
    def link_item(self, product_mapping, marketplace_account, marketplace_item_id, marketplace_variation_id=None):
        return self.create_or_update_mapping(
            product_mapping,
            marketplace_account,
            marketplace_item_id,
            marketplace_variation_id=marketplace_variation_id,
            mapping_status="verified",
        )
