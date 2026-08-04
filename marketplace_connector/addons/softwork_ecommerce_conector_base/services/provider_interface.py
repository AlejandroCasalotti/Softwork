# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod


class IProvider(ABC):
    def capabilities(self):
        """
        Optional feature flags for provider behavior.
        Defaults are permissive for backward compatibility.
        """
        return {
            "oauth_exchange": True,
            "oauth_refresh": True,
            "health_check": True,
        }

    @abstractmethod
    def authenticate(self):
        raise NotImplementedError

    @abstractmethod
    def refresh_token(self):
        raise NotImplementedError

    @abstractmethod
    def health(self):
        raise NotImplementedError

    @abstractmethod
    def publish_product(self, payload):
        raise NotImplementedError

    @abstractmethod
    def update_product(self, payload):
        raise NotImplementedError

    @abstractmethod
    def delete_product(self, payload):
        raise NotImplementedError

    @abstractmethod
    def update_stock(self, payload):
        raise NotImplementedError

    @abstractmethod
    def update_price(self, payload):
        raise NotImplementedError

    @abstractmethod
    def get_orders(self, params=None):
        raise NotImplementedError

    @abstractmethod
    def get_order(self, external_id):
        raise NotImplementedError

    @abstractmethod
    def cancel_order(self, external_id):
        raise NotImplementedError

    @abstractmethod
    def get_messages(self, params=None):
        raise NotImplementedError

    @abstractmethod
    def answer_message(self, payload):
        raise NotImplementedError

    @abstractmethod
    def download_invoice(self, external_id):
        raise NotImplementedError

    @abstractmethod
    def upload_invoice(self, payload):
        raise NotImplementedError

    @abstractmethod
    def sync(self, params=None):
        raise NotImplementedError

    @abstractmethod
    def webhook(self, payload):
        raise NotImplementedError