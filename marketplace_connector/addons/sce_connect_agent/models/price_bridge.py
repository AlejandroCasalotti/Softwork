from decimal import Decimal, InvalidOperation

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError


class SceConnectPriceBridge(models.AbstractModel):
    _name = "sce.connect.agent"
    _description = "SCE Connect Read-only Remote Bridge"

    @api.model
    def get_product_pricelist_price(
        self, product_id, pricelist_id, quantity=1, date=None, company_id=None
    ):
        try:
            product_id = int(product_id)
            pricelist_id = int(pricelist_id)
            quantity = Decimal(str(quantity))
            company_id = int(company_id) if company_id else self.env.company.id
        except (InvalidOperation, TypeError, ValueError) as error:
            raise ValidationError("Los parámetros de precio remoto no son válidos.") from error
        if product_id <= 0 or pricelist_id <= 0 or quantity <= 0:
            raise ValidationError("Producto, lista y cantidad deben ser válidos.")
        allowed_company_ids = self.env.context.get("allowed_company_ids") or [self.env.company.id]
        if company_id not in {int(value) for value in allowed_company_ids}:
            raise AccessError("La empresa solicitada no está permitida para esta conexión.")
        env = self.env.with_context(
            allowed_company_ids=[company_id],
            company_id=company_id,
            date=date or fields.Date.today(),
        )
        product = env["product.product"].browse(product_id).exists()
        pricelist = env["product.pricelist"].browse(pricelist_id).exists()
        if not product:
            raise ValidationError("No se encontró el producto remoto solicitado.")
        if not pricelist:
            raise ValidationError("No se encontró la lista de precios remota solicitada.")
        if product.company_id and product.company_id.id != company_id:
            raise AccessError("El producto no pertenece a la empresa configurada.")
        if pricelist.company_id and pricelist.company_id.id != company_id:
            raise AccessError("La lista de precios no pertenece a la empresa configurada.")
        price = pricelist._get_product_price(product, float(quantity), uom=product.uom_id)
        try:
            price = Decimal(str(price))
        except (InvalidOperation, TypeError, ValueError) as error:
            raise ValidationError("Odoo devolvió un precio remoto inválido.") from error
        if not price.is_finite():
            raise ValidationError("Odoo devolvió un precio remoto no finito.")
        return {
            "product_id": product.id,
            "pricelist_id": pricelist.id,
            "price": format(price, "f"),
            "currency_id": pricelist.currency_id.id,
            "quantity": format(quantity, "f"),
            "company_id": company_id,
        }