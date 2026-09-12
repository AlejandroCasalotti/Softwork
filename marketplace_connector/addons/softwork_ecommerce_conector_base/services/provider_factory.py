# -*- coding: utf-8 -*-
import importlib
import logging

from odoo.exceptions import UserError

from .provider_interface import IProvider

_logger = logging.getLogger(__name__)


class ProviderFactory:
    """
    Factory para resolver providers por tipo de conector.

    Política actual (transición):
    1) provider externo explícito por connector.provider_impl_path
    2) fallback externo por convención sce_connector_<provider_type>
    3) built-in core como compatibilidad legacy (deprecado)
    """

    REQUIRED_METHODS = (
        "authenticate",
        "refresh_token",
        "health",
        "publish_product",
        "update_product",
        "delete_product",
        "update_stock",
        "update_price",
        "get_item",
        "get_orders",
        "get_order",
        "cancel_order",
        "get_messages",
        "answer_message",
        "download_invoice",
        "upload_invoice",
        "search_categories",
        "get_category_attributes",
        "get_category_required_fields",
        "get_listing_prices",
        "sync",
        "webhook",
    )

    @staticmethod
    def _validate_provider_contract(provider, provider_type, source):
        if provider is None:
            raise UserError(f"La factory de provider '{source}' devolvió None para '{provider_type}'.")

        missing = [
            name for name in ProviderFactory.REQUIRED_METHODS if not callable(getattr(provider, name, None))
        ]
        if missing:
            raise UserError(
                "Provider inválido para tipo '%s' resuelto desde '%s'. "
                "Faltan métodos del contrato: %s"
                % (provider_type, source, ", ".join(missing))
            )

        capabilities = provider.capabilities() if hasattr(provider, "capabilities") else {}
        if not isinstance(capabilities, dict):
            raise UserError(
                "Provider inválido para tipo '%s' resuelto desde '%s': capabilities() debe devolver un dict."
                % (provider_type, source)
            )

        return provider

    @staticmethod
    def _load_external_provider(account, provider_type):
        impl_path = (getattr(account.connector_id, "provider_impl_path", "") or "").strip()
        candidate_paths = []
        if impl_path:
            candidate_paths.append(impl_path)
        candidate_paths.append(
            f"sce_connector_{provider_type}.services.provider.get_provider"
        )
        candidate_paths.append(
            f"odoo.addons.sce_connector_{provider_type}.services.provider.get_provider"
        )
        candidate_paths.append(
            f"softwork_provider_{provider_type}.services.provider.get_provider"
        )
        candidate_paths.append(
            f"odoo.addons.softwork_provider_{provider_type}.services.provider.get_provider"
        )

        attempted = []
        for dotted in candidate_paths:
            try:
                module_path, func_name = dotted.rsplit(".", 1)
                module = importlib.import_module(module_path)
                factory_func = getattr(module, func_name)
                provider = factory_func(account.env, account)
                if provider:
                    return ProviderFactory._validate_provider_contract(
                        provider,
                        provider_type,
                        dotted,
                    )
            except Exception as err:
                attempted.append((dotted, str(err)))
                continue

        if attempted:
            lines = "\n".join([f"- {path}: {error}" for path, error in attempted])
            raise UserError(
                "No se pudo resolver provider externo.\n"
                f"provider_type: {provider_type}\n"
                f"connector: {account.connector_id.display_name} ({account.connector_id.id})\n"
                "Intentos:\n"
                f"{lines}\n"
                "Verifica la convención: <modulo>.services.provider.get_provider"
            )
        return None

    @staticmethod
    def _get_builtin_provider(account, provider_type):
        if provider_type == "mercadolibre":
            from .providers.ml_provider import MercadoLibreProvider

            _logger.warning(
                "Using deprecated legacy built-in provider for '%s' on connector '%s' (%s). "
                "Recommended: configure connector.provider_impl_path or install sce_connector_%s.",
                provider_type,
                account.connector_id.display_name,
                account.connector_id.id,
                provider_type,
            )
            provider = MercadoLibreProvider(account.env, account)
            return ProviderFactory._validate_provider_contract(provider, provider_type, "builtin")
        return None

    @staticmethod
    def is_external_only_enabled(account):
        global_force = (
            account.env["ir.config_parameter"]
            .sudo()
            .get_param("sce.provider_force_external_only", "0")
            in ("1", "true", "True")
        )
        connector_force = bool(getattr(account.connector_id, "force_external_provider", False))
        return global_force or connector_force

    @staticmethod
    def get_provider(account):
        provider_type = (account.connector_id.provider_type or "").strip().lower()
        if not provider_type:
            raise UserError("Connector has no provider_type configured.")

        force_external_only = ProviderFactory.is_external_only_enabled(account)

        external = ProviderFactory._load_external_provider(account, provider_type)
        if external:
            return external

        if force_external_only:
            raise UserError(
                f"External-only mode is enabled (sce.provider_force_external_only=1). "
                f"No external provider resolved for type: {provider_type}. "
                f"Configure connector.provider_impl_path (e.g. "
                f"'sce_connector_{provider_type}.services.provider.get_provider') "
                f"or install module sce_connector_{provider_type}."
            )

        builtin = ProviderFactory._get_builtin_provider(account, provider_type)
        if builtin:
            return builtin

        raise UserError(
            f"Provider not implemented yet for type: {provider_type}. "
            f"Configure connector.provider_impl_path (e.g. "
            f"'sce_connector_{provider_type}.services.provider.get_provider') "
            f"or install module sce_connector_{provider_type}."
        )