import os

from odoo import api, fields, models
from odoo.exceptions import UserError

from ..services.core_secret_service import CoreSecretService


class SceGlobalSettings(models.Model):
    _name = "sce.global.settings"
    _description = "SCE Global Settings"
    _sql_constraints = [
        (
            "sce_global_settings_singleton_key_uniq",
            "unique(singleton_key)",
            "Solo puede existir un registro de configuración global de SCE.",
        )
    ]

    name = fields.Char(required=True, default="Configuración global SCE")
    singleton_key = fields.Integer(default=1, required=True, copy=False)
    sce_core_keyring = fields.Char(
        string="SCE Core Keyring",
        compute="_compute_config_values",
        inverse="_inverse_config_values",
        groups="base.group_system",
    )
    mercadolibre_client_id = fields.Char(
        string="Mercado Libre Client ID",
        compute="_compute_config_values",
        inverse="_inverse_config_values",
        groups="base.group_system",
    )
    mercadolibre_client_secret = fields.Char(
        string="Mercado Libre Client Secret",
        compute="_compute_config_values",
        inverse="_inverse_config_values",
        groups="base.group_system",
    )
    mercadolibre_redirect_uri = fields.Char(
        string="Mercado Libre Redirect URI",
        compute="_compute_config_values",
        inverse="_inverse_config_values",
        groups="base.group_system",
    )
    keyring_runtime_source = fields.Selection(
        [
            ("environment", "Variable de entorno"),
            ("database", "Base de datos"),
            ("missing", "Faltante"),
        ],
        compute="_compute_keyring_runtime_state",
    )
    keyring_runtime_status = fields.Selection(
        [
            ("ready", "Disponible"),
            ("missing", "Faltante"),
            ("invalid", "Inválido"),
        ],
        compute="_compute_keyring_runtime_state",
    )
    keyring_runtime_message = fields.Text(compute="_compute_keyring_runtime_state")

    _CONFIG_PARAMS = {
        "sce_core_keyring": CoreSecretService.KEYRING_PARAM,
        "mercadolibre_client_id": "sce.mercadolibre.client_id",
        "mercadolibre_client_secret": "sce.mercadolibre.client_secret",
        "mercadolibre_redirect_uri": "sce.mercadolibre.redirect_uri",
    }

    def _config_parameter_values(self):
        params = self.env["ir.config_parameter"].sudo()
        return {
            field_name: params.get_param(param_name, "") or ""
            for field_name, param_name in self._CONFIG_PARAMS.items()
        }

    def _validate_database_keyring(self, value):
        keyring = (value or "").strip()
        params = self.env["ir.config_parameter"].sudo()
        current_keyring = (
            params.get_param(CoreSecretService.KEYRING_PARAM, "") or ""
        ).strip()
        active_secret_count = self.env["sce.credential.secret"].sudo().search_count(
            [("active", "=", True), ("encrypted_value", "!=", False)]
        )
        if not keyring:
            if active_secret_count:
                raise UserError(
                    "No podés limpiar el keyring mientras existan secretos SCE activos."
                )
            return ""
        if current_keyring and keyring != current_keyring and active_secret_count:
            raise UserError(
                "No podés cambiar el keyring mientras existan secretos SCE activos. "
                "Primero tendrías que re-cifrar o limpiar esas credenciales."
            )
        CoreSecretService(keyring=keyring)
        return keyring

    def _write_config_values(self, values):
        params = self.env["ir.config_parameter"].sudo()
        if "sce_core_keyring" in values:
            values["sce_core_keyring"] = self._validate_database_keyring(
                values["sce_core_keyring"]
            )
        for field_name, param_name in self._CONFIG_PARAMS.items():
            if field_name in values:
                params.set_param(param_name, values[field_name] or "")

    @api.depends_context("uid")
    def _compute_config_values(self):
        values = self._config_parameter_values()
        for record in self:
            for field_name, value in values.items():
                record[field_name] = value

    def _inverse_config_values(self):
        for record in self:
            current_values = record._config_parameter_values()
            values = {
                "mercadolibre_client_id": record.mercadolibre_client_id,
                "mercadolibre_client_secret": record.mercadolibre_client_secret,
                "mercadolibre_redirect_uri": record.mercadolibre_redirect_uri,
            }
            runtime_keyring, source = CoreSecretService.resolve_runtime_keyring(
                env=record.env, environ=os.environ
            )
            del runtime_keyring
            if source != "environment":
                values["sce_core_keyring"] = record.sce_core_keyring
            elif (record.sce_core_keyring or "").strip() != (
                current_values["sce_core_keyring"] or ""
            ).strip():
                raise UserError(
                    "No podés modificar el keyring en base de datos mientras SCE_CORE_KEYRING esté definido en el entorno."
                )
            record._write_config_values(values)

    @api.depends_context("uid")
    def _compute_keyring_runtime_state(self):
        for record in self:
            runtime_keyring, source = CoreSecretService.resolve_runtime_keyring(
                env=record.env, environ=os.environ
            )
            source = source or "missing"
            record.keyring_runtime_source = source
            if not runtime_keyring:
                record.keyring_runtime_status = "missing"
                record.keyring_runtime_message = (
                    "SCE no tiene un keyring operativo. Cargalo en esta configuración "
                    "o mediante la variable de entorno SCE_CORE_KEYRING."
                )
                continue
            try:
                CoreSecretService(keyring=runtime_keyring)
            except UserError as error:
                record.keyring_runtime_status = "invalid"
                record.keyring_runtime_message = str(error)
                continue
            record.keyring_runtime_status = "ready"
            if source == "environment":
                record.keyring_runtime_message = (
                    "SCE está usando el keyring proveniente de la variable de entorno "
                    "SCE_CORE_KEYRING. El valor guardado en base de datos queda como "
                    "respaldo y no se usa mientras exista la variable."
                )
            else:
                record.keyring_runtime_message = (
                    "SCE está usando el keyring guardado en base de datos."
                )

    def action_validate_keyring(self):
        self.ensure_one()
        runtime_keyring, source = CoreSecretService.resolve_runtime_keyring(
            env=self.env, environ=os.environ
        )
        if not runtime_keyring:
            raise UserError(
                "No hay keyring operativo. Configurá SCE Core Keyring o la variable de entorno SCE_CORE_KEYRING."
            )
        CoreSecretService(keyring=runtime_keyring)
        source_label = (
            "variable de entorno"
            if source == "environment"
            else "base de datos"
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Keyring válido",
                "message": f"SCE puede usar el keyring operativo desde {source_label}.",
                "type": "success",
                "sticky": False,
            },
        }
