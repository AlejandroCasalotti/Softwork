# -*- coding: utf-8 -*-
"""
Factory externa para proveedor MercadoLibre desacoplado.
Convención esperada por softwork_ecommerce_conector_base ProviderFactory:
softwork_provider_mercadolibre.services.provider.get_provider
"""

from odoo.exceptions import UserError

from odoo.addons.softwork_ecommerce_conector_base.services.provider_interface import IProvider
from odoo.addons.sce_connector_ml.services.ml_provider import MercadoLibreProvider


class MercadoLibreExternalProvider(IProvider):
    """
    Wrapper desacoplado para MercadoLibre.
    Permite evolucionar implementación externa sin impactar llamadas del core.
    """

    def __init__(self, env, account):
        self.env = env
        self.account = account
        self._delegate = MercadoLibreProvider(env, account)

    def capabilities(self):
        return {
            "oauth_exchange": True,
            "oauth_refresh": True,
            "health_check": True,
        }

    def authenticate(self):
        return self._delegate.authenticate()

    def refresh_token(self):
        return self._delegate.refresh_token()

    def health(self):
        return self._delegate.health()

    def get_authenticated_user_id(self):
        return self._delegate.get_authenticated_user_id()

    def publish_product(self, payload):
        return self._delegate.publish_product(payload)

    def update_product(self, payload):
        return self._delegate.update_product(payload)

    def delete_product(self, payload):
        return self._delegate.delete_product(payload)

    def update_stock(self, payload):
        return self._delegate.update_stock(payload)

    def update_price(self, payload):
        return self._delegate.update_price(payload)

    def get_item(self, external_id):
        return self._delegate.get_item(external_id)

    def get_orders(self, params=None):
        return self._delegate.get_orders(params=params)

    def get_order(self, external_id):
        return self._delegate.get_order(external_id)

    def cancel_order(self, external_id):
        return self._delegate.cancel_order(external_id)

    def get_messages(self, params=None):
        return self._delegate.get_messages(params=params)

    def answer_message(self, payload):
        return self._delegate.answer_message(payload)

    def download_invoice(self, external_id):
        return self._delegate.download_invoice(external_id)

    def upload_invoice(self, payload):
        return self._delegate.upload_invoice(payload)

    def sync(self, params=None):
        return self._delegate.sync(params=params)

    def search_categories(self, query, limit=20):
        return self._delegate.search_categories(query=query, limit=limit)

    def get_category_attributes(self, category_id):
        return self._delegate.get_category_attributes(category_id=category_id)

    def get_category_required_fields(self, category_id):
        return self._delegate.get_category_required_fields(category_id=category_id)

    def get_listing_prices(self, category_id, price, listing_type_id):
        return self._delegate.get_listing_prices(
            category_id=category_id,
            price=price,
            listing_type_id=listing_type_id,
        )

    def webhook(self, payload):
        return self._delegate.webhook(payload)


def get_provider(env, account):
    provider_type = (account.connector_id.provider_type or "").strip().lower()
    if provider_type != "mercadolibre":
        raise UserError(f"Invalid provider_type for softwork_provider_mercadolibre: {provider_type}")
    return MercadoLibreExternalProvider(env, account)