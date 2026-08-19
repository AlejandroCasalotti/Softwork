# -*- coding: utf-8 -*-
import importlib
import logging

from odoo.exceptions import UserError

from .providers.ml_provider import MercadoLibreProvider

_logger = logging.getLogger(__name__)


class ProviderFactory:
    """
    Factory para resolver providers por tipo de conector.

    Política actual (transición):
    1) provider externo explícito por connector.provider_impl_path
    2) fallback externo por convención sce_connector_<provider_type>
    3) built-in core como compatibilidad legacy (deprecado)
    """

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
                    return provider
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
            _logger.warning(
                "Using deprecated built-in provider for '%s' on connector '%s' (%s). "
                "Recommended: configure connector.provider_impl_path or install sce_connector_%s.",
                provider_type,
                account.connector_id.display_name,
                account.connector_id.id,
                provider_type,
            )
            return MercadoLibreProvider(account.env, account)
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