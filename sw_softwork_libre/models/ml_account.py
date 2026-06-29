# -*- coding: utf-8 -*-
import base64
import hashlib
import logging
import secrets
from urllib.parse import urlencode

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import requests
except Exception:  # pragma: no cover
    requests = None


class SwMlAccount(models.Model):
    _name = "sw.ml.account"
    _description = "Cuenta MercadoLibre"

    name = fields.Char(required=True, default="Cuenta MercadoLibre")
    active = fields.Boolean(default=True)

    site_id = fields.Selection(
        [("MLA", "Argentina (MLA)")],
        string="Sitio",
        default="MLA",
        required=True,
    )

    client_id = fields.Char(string="Client ID", required=True)
    client_secret = fields.Char(string="Client Secret", required=True)
    redirect_uri = fields.Char(string="Redirect URI", required=True)

    auth_code = fields.Char(string="Authorization Code")
    access_token = fields.Char(string="Access Token")
    refresh_token = fields.Char(string="Refresh Token")
    token_type = fields.Char(string="Token Type")
    token_expires_at = fields.Datetime(string="Token Expira")
    seller_id = fields.Char(string="Seller ID")

    oauth_url = fields.Char(string="OAuth URL", compute="_compute_oauth_url")
    pkce_code_verifier = fields.Char(string="PKCE Code Verifier")

    def _build_pkce_pair(self):
        verifier = secrets.token_urlsafe(64)[:96]
        challenge = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode("utf-8")).digest()
        ).decode("utf-8").rstrip("=")
        return verifier, challenge

    @api.depends("client_id", "redirect_uri")
    def _compute_oauth_url(self):
        base = "https://auth.mercadolibre.com.ar/authorization"
        for rec in self:
            if rec.client_id and rec.redirect_uri:
                params = urlencode({
                    "response_type": "code",
                    "client_id": rec.client_id,
                    "redirect_uri": rec.redirect_uri,
                })
                rec.oauth_url = f"{base}?{params}"
            else:
                rec.oauth_url = False

    def action_build_oauth_url(self):
        self.ensure_one()
        if not self.client_id or not self.redirect_uri:
            raise UserError("Debes completar Client ID y Redirect URI.")
        verifier, challenge = self._build_pkce_pair()
        self.pkce_code_verifier = verifier
        params = urlencode({
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        })
        self.oauth_url = f"https://auth.mercadolibre.com.ar/authorization?{params}"
        return self.oauth_url

    def _check_requests(self):
        if not requests:
            raise UserError("La librería Python 'requests' no está disponible en el entorno Odoo.")

    def _ml_request(self, method, endpoint, payload=None, params=None, with_auth=True):
        self.ensure_one()
        self._check_requests()

        headers = {"Content-Type": "application/json"}
        if with_auth:
            if not self.access_token:
                raise UserError("No hay access token configurado.")
            headers["Authorization"] = f"Bearer {self.access_token}"

        url = endpoint if endpoint.startswith("http") else f"https://api.mercadolibre.com{endpoint}"
        response = requests.request(method=method, url=url, json=payload, params=params, headers=headers, timeout=30)
        if response.status_code >= 400:
            raise UserError(f"Error MercadoLibre {response.status_code}: {response.text}")
        if not response.text:
            return {}
        return response.json()

    def action_exchange_code(self):
        for rec in self:
            rec._check_requests()
            if not rec.auth_code:
                raise UserError("Debes informar Authorization Code.")

            if not rec.pkce_code_verifier:
                raise UserError("Falta PKCE code_verifier. Debes volver a autorizar desde el botón Autorizar.")
            payload = {
                "grant_type": "authorization_code",
                "client_id": rec.client_id,
                "client_secret": rec.client_secret,
                "code": rec.auth_code,
                "redirect_uri": rec.redirect_uri,
                "code_verifier": rec.pkce_code_verifier,
            }
            data = rec._ml_request("POST", "/oauth/token", payload=payload, with_auth=False)
            rec._write_token_data(data)
            rec.pkce_code_verifier = False
        return True

    def action_refresh_token(self):
        for rec in self:
            rec._check_requests()
            if not rec.refresh_token:
                raise UserError("No hay refresh token para actualizar.")

            payload = {
                "grant_type": "refresh_token",
                "client_id": rec.client_id,
                "client_secret": rec.client_secret,
                "refresh_token": rec.refresh_token,
            }
            data = rec._ml_request("POST", "/oauth/token", payload=payload, with_auth=False)
            rec._write_token_data(data)
        return True

    def _write_token_data(self, data):
        self.ensure_one()
        expires_in = int(data.get("expires_in", 0) or 0)
        vals = {
            "access_token": data.get("access_token"),
            "refresh_token": data.get("refresh_token"),
            "token_type": data.get("token_type"),
        }
        if expires_in:
            vals["token_expires_at"] = fields.Datetime.now() + fields.DateUtils.to_timedelta(seconds=expires_in)
        self.write(vals)

        try:
            me = self._ml_request("GET", "/users/me")
            self.seller_id = str(me.get("id") or "")
        except Exception as err:
            _logger.warning("No se pudo obtener seller_id: %s", err)

    @api.model
    def cron_refresh_tokens(self):
        accounts = self.search([("active", "=", True), ("refresh_token", "!=", False)])
        for acc in accounts:
            try:
                acc.action_refresh_token()
            except Exception as err:
                _logger.exception("Error refrescando token ML en cuenta %s: %s", acc.display_name, err)