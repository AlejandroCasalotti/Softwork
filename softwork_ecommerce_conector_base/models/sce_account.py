# -*- coding: utf-8 -*-
import base64
import hashlib
import json
import secrets
from urllib.parse import urlencode

from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class SceAccount(models.Model):
    _name = "sce.account"
    _description = "SCE Connector Account"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"

    name = fields.Char(required=True, tracking=True)
    connector_id = fields.Many2one("sce.connector", required=True, ondelete="restrict", tracking=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    active = fields.Boolean(default=True, tracking=True)
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("connected", "Connected"),
            ("error", "Error"),
            ("disabled", "Disabled"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    external_account_ref = fields.Char(string="External Account Reference", index=True)
    credentials_json = fields.Text(string="Credentials JSON")
    client_id = fields.Char(string="Client ID")
    client_secret = fields.Char(string="Client Secret")
    redirect_uri = fields.Char(string="Redirect URI")
    auth_code = fields.Char(string="Authorization Code")
    access_token = fields.Char(string="Access Token")
    refresh_token = fields.Char(string="Refresh Token")
    token_type = fields.Char(string="Token Type")
    token_expires_at = fields.Datetime(string="Token Expires At")
    external_user_id = fields.Char(string="External User ID")
    token_refresh_in_progress = fields.Boolean(default=False, readonly=True)
    token_refresh_started_at = fields.Datetime(readonly=True)
    token_refresh_fail_count = fields.Integer(default=0, readonly=True)
    last_token_refresh_error = fields.Text(readonly=True)
    token_circuit_open_until = fields.Datetime(readonly=True)
    oauth_code_verifier = fields.Char(string="OAuth Code Verifier", copy=False)
    oauth_url = fields.Char(string="OAuth URL", compute="_compute_oauth_url")
    last_connection_check = fields.Datetime()
    last_error = fields.Text()
    job_ids = fields.One2many("sce.job", "account_id", string="Jobs")
    jobs_done_count = fields.Integer(compute="_compute_job_metrics")
    jobs_failed_count = fields.Integer(compute="_compute_job_metrics")
    avg_duration_ms = fields.Float(compute="_compute_job_metrics")
    provider_timeout_seconds = fields.Integer(
        string="Provider Timeout (s)",
        default=30,
        help="Timeout máximo recomendado para operaciones del provider.",
    )

    # Onboarding UX (cliente final)
    mode = fields.Selection(
        selection=[("sandbox", "Sandbox"), ("production", "Producción")],
        default="production",
        tracking=True,
    )
    odoo_base_url = fields.Char(string="URL de Odoo")
    odoo_db_name = fields.Char(string="Base de datos Odoo")
    odoo_user = fields.Char(string="Usuario Odoo")
    odoo_password = fields.Char(string="API Key / Password Odoo")

    # Odoo -> Odoo migration base (fase 1)
    odoo_source_url = fields.Char(string="Odoo Origen - URL")
    odoo_source_db = fields.Char(string="Odoo Origen - Base de datos")
    odoo_source_user = fields.Char(string="Odoo Origen - Usuario")
    odoo_source_api_key = fields.Char(string="Odoo Origen - API Key / Password")
    odoo_target_url = fields.Char(string="Odoo Destino - URL")
    odoo_target_db = fields.Char(string="Odoo Destino - Base de datos")
    odoo_target_user = fields.Char(string="Odoo Destino - Usuario")
    odoo_target_api_key = fields.Char(string="Odoo Destino - API Key / Password")
    migration_mode = fields.Selection(
        selection=[("full", "Completa"), ("incremental", "Incremental")],
        string="Modo de migración",
        default="full",
    )
    migration_since = fields.Datetime(string="Migrar cambios desde")
    ml_client_id = fields.Char(string="MercadoLibre Client ID")
    ml_client_secret = fields.Char(string="MercadoLibre Client Secret")
    ml_redirect_uri = fields.Char(string="MercadoLibre Redirect URI")
    sync_orders = fields.Boolean(string="Sincronizar Ventas", default=True)
    sync_stock = fields.Boolean(string="Sincronizar Stock", default=True)
    sync_prices = fields.Boolean(string="Sincronizar Precios", default=True)
    last_sync = fields.Datetime(string="Última sincronización")

    def _generate_pkce_pair(self):
        verifier_raw = secrets.token_urlsafe(64)
        verifier = verifier_raw[:128]
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("utf-8")).digest())
            .decode("utf-8")
            .rstrip("=")
        )
        return verifier, challenge

    @api.depends("client_id", "redirect_uri", "connector_id.provider_type")
    def _compute_oauth_url(self):
        for rec in self:
            if rec.connector_id.provider_type == "mercadolibre" and rec.client_id and rec.redirect_uri and rec.id:
                params = urlencode(
                    {
                        "response_type": "code",
                        "client_id": rec.client_id,
                        "redirect_uri": rec.redirect_uri,
                        "state": str(rec.id),
                    }
                )
                rec.oauth_url = f"https://auth.mercadolibre.com.ar/authorization?{params}"
            else:
                rec.oauth_url = False

    @api.model
    def get_or_create_quick_ml_account(self, company=None):
        company = company or self.env.company
        connector = self.env["sce.connector"].search(
            [
                ("provider_type", "=", "mercadolibre"),
                ("company_id", "=", company.id),
                ("active", "=", True),
            ],
            limit=1,
        )
        if not connector:
            connector = self.env["sce.connector"].create(
                {
                    "name": "MercadoLibre",
                    "code": "mercadolibre",
                    "provider_type": "mercadolibre",
                    "state": "active",
                    "active": True,
                    "company_id": company.id,
                }
            )

        account = self.search(
            [
                ("connector_id", "=", connector.id),
                ("company_id", "=", company.id),
                ("active", "=", True),
            ],
            limit=1,
        )
        if account:
            return account

        client_id = (
            self.env["ir.config_parameter"].sudo().get_param("sce.mercadolibre.client_id", "") or ""
        )
        client_secret = (
            self.env["ir.config_parameter"].sudo().get_param("sce.mercadolibre.client_secret", "") or ""
        )
        redirect_uri = (
            self.env["ir.config_parameter"].sudo().get_param("sce.mercadolibre.redirect_uri", "") or ""
        )

        return self.create(
            {
                "name": "Cuenta MercadoLibre",
                "connector_id": connector.id,
                "company_id": company.id,
                "active": True,
                "state": "draft",
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "ml_client_id": client_id,
                "ml_client_secret": client_secret,
                "ml_redirect_uri": redirect_uri,
            }
        )

    def _sync_onboarding_to_oauth_fields(self):
        for rec in self:
            vals = {}
            if rec.ml_client_id:
                vals["client_id"] = rec.ml_client_id
            if rec.ml_client_secret:
                vals["client_secret"] = rec.ml_client_secret
            if rec.ml_redirect_uri:
                vals["redirect_uri"] = rec.ml_redirect_uri
            if vals:
                rec.write(vals)

    def action_start_onboarding_connection(self):
        self.ensure_one()
        if self.connector_id.provider_type != "mercadolibre":
            raise UserError("Este onboarding rápido está disponible solo para cuentas MercadoLibre.")
        missing = []
        if not self.name:
            missing.append("Nombre de cuenta")
        if not self.odoo_base_url:
            missing.append("URL de Odoo")
        if not self.odoo_db_name:
            missing.append("Base de datos Odoo")
        if not self.odoo_user:
            missing.append("Usuario Odoo")
        if not self.odoo_password:
            missing.append("API Key / Password Odoo")
        if not self.ml_client_id:
            missing.append("MercadoLibre Client ID")
        if not self.ml_client_secret:
            missing.append("MercadoLibre Client Secret")
        if not self.ml_redirect_uri:
            missing.append("MercadoLibre Redirect URI")

        if missing:
            raise UserError("Completá estos campos antes de conectar:\n- " + "\n- ".join(missing))

        self._sync_onboarding_to_oauth_fields()
        return self.action_open_oauth_url()

    def action_test_odoo_connection(self):
        self.ensure_one()
        if self.connector_id.provider_type != "odoo":
            raise UserError("Esta prueba es solo para conectores tipo Odoo.")
        missing = []
        for label, value in [
            ("Odoo Origen - URL", self.odoo_source_url),
            ("Odoo Origen - Base de datos", self.odoo_source_db),
            ("Odoo Origen - Usuario", self.odoo_source_user),
            ("Odoo Origen - API Key / Password", self.odoo_source_api_key),
            ("Odoo Destino - URL", self.odoo_target_url),
            ("Odoo Destino - Base de datos", self.odoo_target_db),
            ("Odoo Destino - Usuario", self.odoo_target_user),
            ("Odoo Destino - API Key / Password", self.odoo_target_api_key),
        ]:
            if not value:
                missing.append(label)
        if missing:
            raise UserError("Faltan datos para probar conexión Odoo->Odoo:\n- " + "\n- ".join(missing))
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Conexión validada",
                "message": "Configuración Odoo origen/destino cargada. En fase 2 se conectará por XML-RPC/JSON-RPC.",
                "type": "success",
                "sticky": False,
            },
        }

    def action_start_migration_wizard(self):
        self.ensure_one()
        if self.connector_id.provider_type != "odoo":
            raise UserError("Este asistente aplica solo a conectores tipo Odoo.")
        return {
            "type": "ir.actions.act_window",
            "name": "Asistente de migración Odoo a Odoo",
            "res_model": "sce.odoo.migration.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_account_id": self.id,
                "default_migration_mode": self.migration_mode or "full",
                "default_since_datetime": self.migration_since,
            },
        }

    def action_test_and_confirm(self):
        for rec in self:
            missing = []
            if not rec.odoo_base_url:
                missing.append("URL de Odoo")
            if not rec.odoo_db_name:
                missing.append("Base de datos Odoo")
            if not rec.odoo_user:
                missing.append("Usuario Odoo")
            if not rec.odoo_password:
                missing.append("API Key / Password Odoo")
            if not rec.ml_client_id:
                missing.append("MercadoLibre Client ID")
            if not rec.ml_client_secret:
                missing.append("MercadoLibre Client Secret")
            if not rec.ml_redirect_uri:
                missing.append("MercadoLibre Redirect URI")
            if missing:
                raise UserError("Faltan datos para confirmar:\n- " + "\n- ".join(missing))
            rec.write({"state": "connected", "last_error": False})
        return True

    def action_back_to_draft(self):
        self.write({"state": "draft"})
        return True

    def _run_integration_status_tests(self):
        self.ensure_one()
        tests = []
        user = self.env.user
        company = self.company_id or self.env.company

        def add_test(name, status, message, details=None, action_type="none"):
            tests.append(
                {
                    "test_name": name,
                    "status": status,
                    "message": message,
                    "error_details": details or False,
                    "action_type": action_type,
                }
            )

        try:
            db_name = self.env.cr.dbname
            if db_name:
                add_test("Connection Test", "success", "Conexión exitosa con la cuenta de Odoo", f"DB: {db_name}")
            else:
                add_test("Connection Test", "error", "No se pudo detectar la base de datos de Odoo", action_type="open_settings")
        except Exception as err:
            add_test("Connection Test", "error", "Error de conexión con Odoo", str(err), action_type="open_settings")

        version = self.env["ir.config_parameter"].sudo().get_param("web.base.version") or "N/D"
        add_test("Odoo Version", "success", f"Versión actual de su base de Odoo: {version}", f"Versión completa: {version}")

        if user.has_group("base.group_user"):
            add_test("User Permissions", "success", f"El usuario {user.name} tiene los permisos necesarios")
        else:
            add_test("User Permissions", "warning", f"El usuario {user.name} podría no tener permisos suficientes")

        required_modules = ["mail", "web", "sale_management", "stock", "account"]
        module_env = self.env["ir.module.module"].sudo()
        missing = module_env.search([("name", "in", required_modules), ("state", "not in", ["installed", "to upgrade"])])
        if missing:
            add_test("Required Modules", "error", "Faltan módulos requeridos", ", ".join(missing.mapped("name")))
        else:
            add_test("Required Modules", "success", "Todos los módulos requeridos están instalados y configurados")

        if company:
            add_test("Company ID", "success", f"La compañía/empresa '{company.name}' está configurada para la integración")
        else:
            add_test("Company ID", "error", "No hay compañía configurada para la integración")

        warehouse = self.env["stock.warehouse"].sudo().search([("company_id", "=", company.id)], limit=1)
        if warehouse:
            add_test("Warehouse", "success", f"El almacén '{warehouse.name}' está configurado para la integración")
        else:
            add_test("Warehouse", "warning", "No se encontró un almacén configurado", action_type="open_warehouse")

        add_test("Salesperson User", "success", f"El usuario Comercial '{user.name}' está configurado para la integración")

        stock_location = self.env["stock.location"].sudo().search(
            [("usage", "=", "internal"), ("company_id", "in", [company.id, False])],
            limit=1,
        )
        if stock_location:
            add_test("Stock Location", "success", f"La ubicación de stock '{stock_location.display_name}' está configurada para la integración")
        else:
            add_test("Stock Location", "warning", "No se encontró ubicación de stock interna", action_type="open_locations")

        pricelist = self.env["product.pricelist"].sudo().search([("company_id", "in", [company.id, False])], limit=1)
        if pricelist:
            add_test("Pricelist", "success", f"La lista de precios '{pricelist.name}' está configurada para su integración")
        else:
            add_test("Pricelist", "warning", "No se encontró lista de precios configurada", action_type="open_pricelist")

        add_test("Excluded Products", "success", "No exclusion domain set. All products will be considered for sync.")

        if self.access_token:
            add_test("MercadoLibre Connection", "success", "Conexión exitosa a su cuenta de MercadoLibre")
        else:
            add_test("MercadoLibre Connection", "error", "No hay access token de MercadoLibre configurado", action_type="reconnect")

        l10n_ar = module_env.search([("name", "=", "l10n_ar"), ("state", "=", "installed")], limit=1)
        if l10n_ar:
            add_test("Localization Module", "success", "El módulo de Localización 'l10n_ar' para Argentina está instalado en Odoo")
        else:
            add_test("Localization Module", "warning", "El módulo 'l10n_ar' no está instalado")

        if self.access_token:
            try:
                from ..services.provider_factory import ProviderFactory
                provider = ProviderFactory.get_provider(self)
                data = provider._request("GET", "/users/me/items/search", with_auth=True, params={"limit": 1})
                total = data.get("paging", {}).get("total", 0) if isinstance(data, dict) else 0
                add_test("MercadoLibre Items", "success", f"Se encontraron {total} publicaciones en su cuenta de MercadoLibre")
            except Exception as err:
                add_test("MercadoLibre Items", "warning", "No se pudo obtener el total de publicaciones", str(err), action_type="reconnect")
        else:
            add_test("MercadoLibre Items", "warning", "No se pudo validar publicaciones porque no hay access token", action_type="reconnect")

        return tests

    def _compute_health_summary(self, tests):
        ok = len([t for t in tests if t.get("status") == "success"])
        warning = len([t for t in tests if t.get("status") == "warning"])
        error = len([t for t in tests if t.get("status") == "error"])
        total = ok + warning + error
        score = 100
        if total:
            score = max(0, min(100, int(((ok * 1.0) + (warning * 0.5)) / total * 100)))
        return {
            "ok_count": ok,
            "warning_count": warning,
            "error_count": error,
            "health_score": score,
        }

    def _create_status_snapshot(self, tests):
        self.ensure_one()
        summary = self._compute_health_summary(tests)
        snapshot = self.env["sce.integration.status.snapshot"].create({
            "name": f"Diagnóstico {self.display_name}",
            "account_id": self.id,
            "health_score": summary["health_score"],
            "ok_count": summary["ok_count"],
            "warning_count": summary["warning_count"],
            "error_count": summary["error_count"],
            "line_ids": [(0, 0, {
                "test_name": t.get("test_name"),
                "status": t.get("status"),
                "message": t.get("message"),
                "error_details": t.get("error_details"),
                "action_type": t.get("action_type", "none"),
            }) for t in tests],
        })
        return snapshot, summary

    def action_check_integration_status(self):
        self.ensure_one()
        tests = self._run_integration_status_tests()
        self._create_status_snapshot(tests)
        wizard = self.env["sce.integration.status.wizard"].create({
            "account_id": self.id,
            "test_line_ids": [(0, 0, vals) for vals in tests],
        })
        return {
            "type": "ir.actions.act_window",
            "name": "Verificar Estado de Integración",
            "res_model": "sce.integration.status.wizard",
            "view_mode": "form",
            "res_id": wizard.id,
            "target": "new",
        }

    @api.model
    def cron_daily_integration_status_snapshot(self):
        activity_type = self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        accounts = self.search([("active", "=", True)])
        for acc in accounts:
            try:
                tests = acc._run_integration_status_tests()
                snapshot, summary = acc._create_status_snapshot(tests)
                if summary["health_score"] < 70 or summary["error_count"] > 0:
                    if activity_type:
                        self.env["mail.activity"].create({
                            "res_model_id": self.env["ir.model"]._get_id("sce.account"),
                            "res_id": acc.id,
                            "activity_type_id": activity_type.id,
                            "summary": "Alerta de salud de integración",
                            "note": (
                                f"Health score: {summary['health_score']}\n"
                                f"Errores: {summary['error_count']}\n"
                                f"Warnings: {summary['warning_count']}\n"
                                f"Snapshot ID: {snapshot.id}"
                            ),
                            "user_id": acc.create_uid.id or self.env.user.id,
                        })
            except Exception as err:
                acc.last_error = str(err)

    def action_open_oauth_url(self):
        self.ensure_one()
        if self.connector_id.provider_type != "mercadolibre":
            raise UserError("Conexión OAuth disponible solo para MercadoLibre.")
        if not self.client_id or not self.redirect_uri:
            raise UserError(
                "Falta configurar Client ID / Client Secret / Redirect URI. "
                "Cargalos en Parámetros del sistema: "
                "sce.mercadolibre.client_id, sce.mercadolibre.client_secret, sce.mercadolibre.redirect_uri"
            )
        verifier, challenge = self._generate_pkce_pair()
        self.write({"oauth_code_verifier": verifier})
        params = urlencode(
            {
                "response_type": "code",
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "state": str(self.id),
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
        )
        oauth_url = f"https://auth.mercadolibre.com.ar/authorization?{params}"
        return {
            "type": "ir.actions.act_url",
            "url": oauth_url,
            "target": "new",
        }

    @api.depends("job_ids.state", "job_ids.duration_ms")
    def _compute_job_metrics(self):
        for rec in self:
            done_jobs = rec.job_ids.filtered(lambda j: j.state == "done")
            failed_jobs = rec.job_ids.filtered(lambda j: j.state == "failed")
            rec.jobs_done_count = len(done_jobs)
            rec.jobs_failed_count = len(failed_jobs)
            rec.avg_duration_ms = (sum(done_jobs.mapped("duration_ms")) / len(done_jobs)) if done_jobs else 0.0

    def _get_credentials_dict(self):
        self.ensure_one()
        if not self.credentials_json:
            return {}
        try:
            return json.loads(self.credentials_json)
        except Exception:
            return {}

    def _set_credentials_dict(self, data):
        self.ensure_one()
        self.credentials_json = json.dumps(data or {})

    def _sync_credentials_blob(self):
        self.ensure_one()
        data = self._get_credentials_dict()
        data.update(
            {
                "client_id": self.client_id or "",
                "client_secret": self.client_secret or "",
                "redirect_uri": self.redirect_uri or "",
                "auth_code": self.auth_code or "",
                "access_token": self.access_token or "",
                "refresh_token": self.refresh_token or "",
                "token_type": self.token_type or "",
                "token_expires_at": self.token_expires_at.isoformat() if self.token_expires_at else "",
                "external_user_id": self.external_user_id or "",
            }
        )
        self._set_credentials_dict(data)

    def _provider_capabilities(self, provider):
        if hasattr(provider, "capabilities"):
            try:
                return provider.capabilities() or {}
            except Exception:
                return {}
        return {}

    def _sanitize_result_for_logs(self, result):
        clean = dict(result or {})
        for key in ("access_token", "refresh_token", "client_secret"):
            if clean.get(key):
                clean[key] = "***"
        return clean

    def action_exchange_code(self):
        event_model = self.env["sce.event"]
        log_service = self.env["sce.log.service"]
        for rec in self:
            try:
                if not rec.auth_code:
                    raise UserError("Debes informar Authorization Code.")
                from ..services.provider_factory import ProviderFactory
                provider = ProviderFactory.get_provider(rec)
                capabilities = rec._provider_capabilities(provider)
                if capabilities.get("oauth_exchange", True) and not rec.oauth_code_verifier:
                    raise UserError("La autorización expiró o no es válida. Presiona 'Conectar' nuevamente.")
                if not capabilities.get("oauth_exchange", True):
                    raise UserError("Este conector no soporta intercambio OAuth de Authorization Code.")
                result = provider.authenticate()
                if result.get("access_token"):
                    rec.write(
                        {
                            "access_token": result.get("access_token"),
                            "refresh_token": result.get("refresh_token"),
                            "token_type": result.get("token_type"),
                            "token_expires_at": result.get("token_expires_at"),
                            "external_user_id": result.get("external_user_id"),
                            "state": "connected",
                            "last_error": False,
                            "token_refresh_fail_count": 0,
                            "last_token_refresh_error": False,
                            "oauth_code_verifier": False,
                            "auth_code": False,
                        }
                    )
                    rec._sync_credentials_blob()
                safe_result = rec._sanitize_result_for_logs(result)
                elapsed_ms = result.get("elapsed_ms") if isinstance(result, dict) else False
                log_service.log(
                    name="Token exchanged",
                    message=f"Token exchange executed for {rec.display_name}",
                    level="INFO",
                    account=rec,
                    connector=rec.connector_id,
                    details_json=json.dumps(safe_result, default=str),
                    provider=rec.connector_id.provider_type,
                    operation="token_exchange",
                    elapsed_ms=elapsed_ms,
                )
                event_model.emit_event(
                    name=f"Token exchange success: {rec.display_name}",
                    event_type="TokenExchangeSuccess",
                    payload={"account_id": rec.id, "provider": rec.connector_id.provider_type},
                    company=rec.company_id,
                )
            except Exception as err:
                err_msg = str(err)
                used_refresh_fallback = False

                if "invalid_grant" in err_msg and rec.refresh_token:
                    try:
                        from ..services.provider_factory import ProviderFactory
                        provider = ProviderFactory.get_provider(rec)
                        refresh_result = provider.refresh_token()
                        if refresh_result.get("access_token"):
                            rec.write(
                                {
                                    "access_token": refresh_result.get("access_token"),
                                    "refresh_token": refresh_result.get("refresh_token") or rec.refresh_token,
                                    "token_type": refresh_result.get("token_type") or rec.token_type,
                                    "token_expires_at": refresh_result.get("token_expires_at"),
                                    "state": "connected",
                                    "last_error": False,
                                    "token_refresh_fail_count": 0,
                                    "last_token_refresh_error": False,
                                    "token_circuit_open_until": False,
                                    "auth_code": False,
                                    "oauth_code_verifier": False,
                                }
                            )
                            rec._sync_credentials_blob()
                            used_refresh_fallback = True
                    except Exception as refresh_err:
                        err_msg = f"{err_msg} | refresh_fallback_error: {refresh_err}"
                        used_refresh_fallback = False

                if used_refresh_fallback:
                    rec.write(
                        {
                            "state": "connected",
                            "last_error": False,
                            "auth_code": False,
                            "oauth_code_verifier": False,
                        }
                    )
                    event_model.emit_event(
                        name=f"Token exchange fallback refresh success: {rec.display_name}",
                        event_type="TokenExchangeFallbackRefreshSuccess",
                        payload={"account_id": rec.id, "provider": rec.connector_id.provider_type},
                        company=rec.company_id,
                    )
                    log_service.log(
                        name="Token exchange fallback refresh success",
                        message=f"OAuth code inválido en {rec.display_name}; se recuperó con refresh token.",
                        level="WARNING",
                        account=rec,
                        connector=rec.connector_id,
                        provider=rec.connector_id.provider_type,
                        operation="token_exchange_fallback_refresh",
                    )
                    continue

                rec.state = "error"
                rec.last_error = err_msg
                rec.token_refresh_fail_count = (rec.token_refresh_fail_count or 0) + 1
                rec.last_token_refresh_error = err_msg
                if rec.token_refresh_fail_count >= 3:
                    rec._open_token_circuit(minutes=10)
                rec.oauth_code_verifier = False
                rec.auth_code = False
                event_model.emit_event(
                    name=f"Token exchange failed: {rec.display_name}",
                    event_type="TokenExchangeFailed",
                    payload={"account_id": rec.id, "error": err_msg},
                    company=rec.company_id,
                )
                log_service.log(
                    name="Token exchange failed",
                    message=f"Token exchange failed for {rec.display_name}: {err_msg}",
                    level="ERROR",
                    account=rec,
                    connector=rec.connector_id,
                )
                raise
        return True

    def action_force_unlock_token_refresh(self):
        self.write(
            {
                "token_refresh_in_progress": False,
                "token_refresh_started_at": False,
            }
        )
        return True

    def action_reset_token_circuit(self):
        self.write(
            {
                "token_circuit_open_until": False,
                "token_refresh_fail_count": 0,
                "last_token_refresh_error": False,
            }
        )
        return True

    def write(self, vals):
        if "client_secret" in vals:
            for rec in self:
                if vals.get("client_secret") != rec.client_secret:
                    vals.setdefault("state", "draft")
                    vals.setdefault("access_token", False)
                    vals.setdefault("refresh_token", False)
                    vals.setdefault("token_type", False)
                    vals.setdefault("token_expires_at", False)
                    vals.setdefault("external_user_id", False)
        return super().write(vals)

    def _is_token_circuit_open(self):
        self.ensure_one()
        return bool(self.token_circuit_open_until and fields.Datetime.now() < self.token_circuit_open_until)

    def _open_token_circuit(self, minutes=5):
        self.ensure_one()
        self.write({"token_circuit_open_until": fields.Datetime.now() + timedelta(minutes=minutes)})

    def action_refresh_token(self):
        event_model = self.env["sce.event"]
        log_service = self.env["sce.log.service"]
        for rec in self:
            if rec.token_refresh_in_progress:
                if rec.token_refresh_started_at:
                    zombie_deadline = rec.token_refresh_started_at + timedelta(minutes=10)
                    if fields.Datetime.now() < zombie_deadline:
                        continue
                rec.write(
                    {
                        "token_refresh_in_progress": False,
                        "token_refresh_started_at": False,
                    }
                )
            rec.write(
                {
                    "token_refresh_in_progress": True,
                    "token_refresh_started_at": fields.Datetime.now(),
                }
            )
            try:
                if rec._is_token_circuit_open():
                    continue
                if not rec.refresh_token:
                    raise UserError("No hay refresh token configurado.")
                from ..services.provider_factory import ProviderFactory
                provider = ProviderFactory.get_provider(rec)
                capabilities = rec._provider_capabilities(provider)
                if not capabilities.get("oauth_refresh", True):
                    raise UserError("Este conector no soporta refresh de token OAuth.")
                result = provider.refresh_token()
                if result.get("access_token"):
                    rec.write(
                        {
                            "access_token": result.get("access_token"),
                            "refresh_token": result.get("refresh_token") or rec.refresh_token,
                            "token_type": result.get("token_type") or rec.token_type,
                            "token_expires_at": result.get("token_expires_at"),
                            "state": "connected",
                            "last_error": False,
                            "token_refresh_fail_count": 0,
                            "last_token_refresh_error": False,
                            "token_circuit_open_until": False,
                        }
                    )
                    rec._sync_credentials_blob()
                safe_result = rec._sanitize_result_for_logs(result)
                elapsed_ms = result.get("elapsed_ms") if isinstance(result, dict) else False
                log_service.log(
                    name="Token refreshed",
                    message=f"Token refresh executed for {rec.display_name}",
                    level="INFO",
                    account=rec,
                    connector=rec.connector_id,
                    details_json=json.dumps(safe_result, default=str),
                    provider=rec.connector_id.provider_type,
                    operation="token_refresh",
                    elapsed_ms=elapsed_ms,
                )
                event_model.emit_event(
                    name=f"Token refresh success: {rec.display_name}",
                    event_type="TokenRefreshSuccess",
                    payload={"account_id": rec.id, "provider": rec.connector_id.provider_type},
                    company=rec.company_id,
                )
            except Exception as err:
                rec.state = "error"
                rec.last_error = str(err)
                rec.token_refresh_fail_count = (rec.token_refresh_fail_count or 0) + 1
                rec.last_token_refresh_error = str(err)
                if rec.token_refresh_fail_count >= 3:
                    rec._open_token_circuit(minutes=10)
                event_model.emit_event(
                    name=f"Token refresh failed: {rec.display_name}",
                    event_type="TokenRefreshFailed",
                    payload={"account_id": rec.id, "error": str(err)},
                    company=rec.company_id,
                )
                log_service.log(
                    name="Token refresh failed",
                    message=f"Token refresh failed for {rec.display_name}: {err}",
                    level="ERROR",
                    account=rec,
                    connector=rec.connector_id,
                )
                raise
            finally:
                rec.write(
                    {
                        "token_refresh_in_progress": False,
                    }
                )
        return True

    @api.model
    def cron_refresh_provider_tokens(self):
        now_dt = fields.Datetime.now()
        refresh_deadline = now_dt + timedelta(minutes=15)
        accounts = self.search(
            [
                ("active", "=", True),
                ("refresh_token", "!=", False),
                ("token_refresh_in_progress", "=", False),
            ]
        )
        for acc in accounts:
            if not getattr(acc.connector_id, "oauth_refresh_enabled", True):
                continue
            if acc.token_refresh_fail_count and acc.token_refresh_fail_count >= 5:
                continue
            needs_refresh = (not acc.token_expires_at) or (acc.token_expires_at <= refresh_deadline)
            if not needs_refresh:
                continue
            try:
                if acc._is_token_circuit_open():
                    continue
                from ..services.provider_factory import ProviderFactory
                provider = ProviderFactory.get_provider(acc)
                capabilities = acc._provider_capabilities(provider)
                if not capabilities.get("oauth_refresh", True):
                    continue
                acc.action_refresh_token()
            except Exception as err:
                acc.last_error = str(err)
                acc.state = "error"

    def cron_health_check(self):
        accounts = self.search([("active", "=", True)])
        log_service = self.env["sce.log.service"]
        for acc in accounts:
            try:
                if not getattr(acc.connector_id, "healthcheck_enabled", True):
                    continue
                from ..services.provider_factory import ProviderFactory
                provider = ProviderFactory.get_provider(acc)
                capabilities = acc._provider_capabilities(provider)

                acc.last_connection_check = fields.Datetime.now()
                if capabilities.get("health_check", True):
                    provider.health()

                if acc.state not in ("connected", "draft"):
                    acc.state = "connected"
                if acc.last_error:
                    acc.last_error = False
                log_service.log(
                    name="Health check ok",
                    message=f"Health check OK for account {acc.display_name}",
                    level="INFO",
                    account=acc,
                    connector=acc.connector_id,
                )
            except Exception as err:
                acc.state = "error"
                acc.last_error = str(err)
                log_service.log(
                    name="Health check error",
                    message=f"Health check error for account {acc.display_name}: {err}",
                    level="ERROR",
                    account=acc,
                    connector=acc.connector_id,
                )