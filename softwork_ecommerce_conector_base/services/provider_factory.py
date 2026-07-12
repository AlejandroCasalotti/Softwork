# -*- coding: utf-8 -*-
import importlib

from odoo.exceptions import UserError

from .providers.ml_provider import MercadoLibreProvider


class ProviderFactory:
    """
    Factory para resolver providers por tipo de conector.

    Soporta:
    1) providers built-in del core
    2) providers externos vía path python configurable en connector.provider_impl_path
       o fallback convención:
       softwork_provider_<provider_type>.services.provider.get_provider
    """

    @staticmethod
    def _load_external_provider(account, provider_type):
        impl_path = (getattr(account.connector_id, "provider_impl_path", "") or "").strip()
        candidate_paths = []
        if impl_path:
            candidate_paths.append(impl_path)
        candidate_paths.append(
            f"softwork_provider_{provider_type}.services.provider.get_provider"
        )

        for dotted in candidate_paths:
            try:
                module_path, func_name = dotted.rsplit(".", 1)
                module = importlib.import_module(module_path)
                factory_func = getattr(module, func_name)
                provider = factory_func(account.env, account)
                if provider:
                    return provider
            except Exception:
                continue
        return None

    @staticmethod
    def get_provider(account):
        provider_type = (account.connector_id.provider_type or "").strip().lower()
        if provider_type == "mercadolibre":
            return MercadoLibreProvider(account.env, account)

        external = ProviderFactory._load_external_provider(account, provider_type)
        if external:
            return external

        raise UserError(
            f"Provider not implemented yet for type: {provider_type}. "
            f"Configure connector.provider_impl_path or install softwork_provider_{provider_type}."
        )