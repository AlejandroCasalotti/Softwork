# -*- coding: utf-8 -*-
import logging
from datetime import timedelta

from odoo import fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import requests
except Exception:  # pragma: no cover
    requests = None


class MlAccount(models.Model):
    _name = "ml.account"
    _description = "Cuenta MercadoLibre"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(required=True, tracking=True)
    client_id = fields.Char(required=True)
    client_secret = fields.Char(required=True)
    redirect_uri = fields.Char(required=True)

    access_token = fields.Text()
    refresh_token = fields.Text()
    token_expires_at = fields.Datetime()

    seller_id = fields.Char(readonly=True)
    country = fields.Selection(
        [("AR", "Argentina"), ("MX", "México"), ("BR", "Brasil"), ("CL", "Chile"), ("CO", "Colombia")],
        default="AR",
        required=True,
    )
    active = fields.Boolean(default=True)

    def _check_requests(self):
        if not requests:
            raise UserError("La librería 'requests' no está disponible en este entorno.")

    def _site_code(self):
        self.ensure_one()
        return {
            "AR": "MLA",
            "MX": "MLM",
            "BR": "MLB",
            "CL": "MLC",
            "CO": "MCO",
        }.get(self.country, "MLA")

    def _build_auth_url(self):
        self.ensure_one()
        return (
            "https://auth.mercadolibre.com/authorization"
            f"?response_type=code&client_id={self.client_id}&redirect_uri={self.redirect_uri}"
        )

    def action_open_auth_url(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": self._build_auth_url(),
            "target": "new",
        }

    def action_exchange_code(self):
        self.ensure_one()
        code = self.env.context.get("ml_auth_code")
        if not code:
            raise UserError("Debes pasar el auth code en contexto como 'ml_auth_code'.")
        self._check_requests()
        payload = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
        }
        data = self._token_request(payload)
        self._write_token_data(data)
        return True

    def _token_request(self, payload):
        self.ensure_one()
        self._check_requests()
        response = requests.post("https://api.mercadolibre.com/oauth/token", json=payload, timeout=60)
        if response.status_code >= 300:
            raise UserError(f"Error OAuth ML ({response.status_code}): {response.text}")
        return response.json()

    def _write_token_data(self, data):
        self.ensure_one()
        expires_in = int(data.get("expires_in", 0) or 0)
        vals = {
            "access_token": data.get("access_token"),
            "refresh_token": data.get("refresh_token") or self.refresh_token,
        }
        if expires_in:
            vals["token_expires_at"] = fields.Datetime.now() + timedelta(seconds=expires_in)
        self.write(vals)
        self._fetch_seller()

    def _fetch_seller(self):
        self.ensure_one()
        if not self.access_token:
            return
        me = self.ml_request("GET", "/users/me")
        self.seller_id = str(me.get("id") or "")

    def refresh_access_token(self):
        self.ensure_one()
        if not self.refresh_token:
            raise UserError("No hay refresh token.")
        payload = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
        }
        data = self._token_request(payload)
        self._write_token_data(data)
        return True

    def _ensure_valid_token(self):
        self.ensure_one()
        if not self.access_token:
            raise UserError("No hay access token configurado.")
        if self.token_expires_at and self.token_expires_at <= fields.Datetime.now():
            self.refresh_access_token()

    def ml_request(self, method, endpoint, payload=None, params=None):
        self.ensure_one()
        self._check_requests()
        self._ensure_valid_token()

        url = endpoint if endpoint.startswith("http") else f"https://api.mercadolibre.com{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=payload,
            params=params,
            timeout=120,
        )
        if response.status_code >= 300:
            self.env["ml.log"].create({
                "account_id": self.id,
                "level": "error",
                "message": f"HTTP {response.status_code}",
                "detail": response.text,
            })
            raise UserError(f"Error MercadoLibre ({response.status_code}): {response.text}")

        data = response.json() if response.text else {}
        self.env["ml.log"].create({
            "account_id": self.id,
            "level": "info",
            "message": f"{method} {endpoint}",
            "detail": str(data)[:4000],
        })
        return data

    @classmethod
    def cron_refresh_tokens(cls, env):
        accounts = env["ml.account"].search([("active", "=", True), ("refresh_token", "!=", False)])
        for account in accounts:
            try:
                account.refresh_access_token()
            except Exception as err:
                _logger.exception("Error al refrescar token en %s: %s", account.display_name, err)
                env["ml.log"].create({
                    "account_id": account.id,
                    "level": "error",
                    "message": "Error refresh token",
                    "detail": str(err),
                })