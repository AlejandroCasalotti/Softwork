# -*- coding: utf-8 -*-
import json
from urllib.parse import urlencode

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
    oauth_url = fields.Char(string="OAuth URL", compute="_compute_oauth_url")
    last_connection_check = fields.Datetime()
    last_error = fields.Text()
    job_ids = fields.One2many("sce.job", "account_id", string="Jobs")
    jobs_done_count = fields.Integer(compute="_compute_job_metrics")
    jobs_failed_count = fields.Integer(compute="_compute_job_metrics")
    avg_duration_ms = fields.Float(compute="_compute_job_metrics")

    @api.depends("client_id", "redirect_uri", "connector_id.provider_type")
    def _compute_oauth_url(self):
        for rec in self:
            if rec.connector_id.provider_type == "mercadolibre" and rec.client_id and rec.redirect_uri:
                params = urlencode(
                    {
                        "response_type": "code",
                        "client_id": rec.client_id,
                        "redirect_uri": rec.redirect_uri,
                    }
                )
                rec.oauth_url = f"https://auth.mercadolibre.com.ar/authorization?{params}"
            else:
                rec.oauth_url = False

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

    def action_exchange_code(self):
        for rec in self:
            if rec.connector_id.provider_type != "mercadolibre":
                raise UserError("Token exchange solo está disponible para MercadoLibre.")
            if not rec.auth_code:
                raise UserError("Debes informar Authorization Code.")
            provider = rec.env["sce.provider.factory"].get_provider(rec)
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
                    }
                )
                rec._sync_credentials_blob()
            rec.env["sce.log.service"].log(
                name="Token exchanged",
                message=f"Token exchange executed for {rec.display_name}",
                level="INFO",
                account=rec,
                connector=rec.connector_id,
                details_json=json.dumps(result),
            )
        return True

    def action_refresh_token(self):
        for rec in self:
            if rec.connector_id.provider_type != "mercadolibre":
                raise UserError("Token refresh solo está disponible para MercadoLibre.")
            if not rec.refresh_token:
                raise UserError("No hay refresh token configurado.")
            provider = rec.env["sce.provider.factory"].get_provider(rec)
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
                    }
                )
                rec._sync_credentials_blob()
            rec.env["sce.log.service"].log(
                name="Token refreshed",
                message=f"Token refresh executed for {rec.display_name}",
                level="INFO",
                account=rec,
                connector=rec.connector_id,
                details_json=json.dumps(result),
            )
        return True

    @api.model
    def cron_refresh_provider_tokens(self):
        accounts = self.search(
            [
                ("active", "=", True),
                ("connector_id.provider_type", "=", "mercadolibre"),
                ("refresh_token", "!=", False),
            ]
        )
        for acc in accounts:
            try:
                acc.action_refresh_token()
            except Exception as err:
                acc.last_error = str(err)
                acc.state = "error"

    def cron_health_check(self):
        accounts = self.search([("active", "=", True)])
        log_service = self.env["sce.log.service"]
        for acc in accounts:
            try:
                acc.last_connection_check = fields.Datetime.now()
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