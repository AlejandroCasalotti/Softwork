import logging

from odoo import http
from odoo.exceptions import AccessError, UserError
from odoo.http import request

from ..services.mercadolibre_oauth import MercadoLibreOAuthService

_logger = logging.getLogger(__name__)


class SceConnectMercadoLibreOAuthController(http.Controller):
    @http.route(
        "/sce/connect/mercadolibre/start",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def start(self, account_id=None, **kwargs):
        try:
            account_id = int(account_id or 0)
            account = request.env["sce.mercadolibre.account"].browse(account_id)
            if not account.exists():
                raise AccessError("La cuenta MercadoLibre no existe o no pertenece al usuario.")
            url = MercadoLibreOAuthService(request.env).start(account)
            return request.redirect(url)
        except (AccessError, UserError) as error:
            _logger.warning("MercadoLibre OAuth start rejected: %s", error)
            return request.redirect("/sce/connect/mercadolibre/result?status=error")
        except Exception:
            _logger.exception("MercadoLibre OAuth start failed")
            return request.redirect("/sce/connect/mercadolibre/result?status=error")

    @http.route(
        "/sce/connect/mercadolibre/callback",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def callback(self, state=None, code=None, error=None, **kwargs):
        try:
            if error:
                transaction = self._validate_state(state)
                transaction.mercadolibre_account_id.sudo().write(
                    {"status": "error", "last_error": "MercadoLibre rechazó la autorización."}
                )
                transaction.consume()
                return request.redirect("/sce/connect/mercadolibre/result?status=error")
            MercadoLibreOAuthService(request.env).complete(state, code, request.env.user)
            return request.redirect("/sce/connect/mercadolibre/result?status=connected")
        except (AccessError, UserError) as error:
            _logger.warning("MercadoLibre OAuth callback rejected: %s", error)
            return request.redirect("/sce/connect/mercadolibre/result?status=error")
        except Exception:
            _logger.exception("MercadoLibre OAuth callback failed")
            return request.redirect("/sce/connect/mercadolibre/result?status=error")

    @http.route(
        "/sce/connect/mercadolibre/result",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
    def result(self, status=None, **kwargs):
        messages = {
            "connected": ("MercadoLibre conectado", "La cuenta del vendedor quedó conectada correctamente."),
            "error": ("No se pudo conectar MercadoLibre", "Revisá la cuenta y reintentá la autorización."),
            "auth_required": ("Autorización requerida", "MercadoLibre requiere autorización nuevamente."),
        }
        title, message = messages.get(status, messages["error"])
        html = (
            "<html><body style='font-family: sans-serif; padding: 24px;'>"
            f"<h2>{title}</h2><p>{message}</p><p><a href='/web'>Volver a SCE Connect</a></p>"
            "</body></html>"
        )
        return request.make_response(html, headers=[("Content-Type", "text/html; charset=utf-8")])

    @staticmethod
    def _validate_state(state):
        if not state:
            raise UserError("Falta el estado OAuth.")
        state_hash = request.env["sce.oauth.transaction"].hash_state(state)
        transaction = request.env["sce.oauth.transaction"].sudo().search(
            [("state_hash", "=", state_hash)], limit=1
        )
        if not transaction or transaction.user_id != request.env.user:
            raise AccessError("El estado OAuth no pertenece al usuario actual.")
        return transaction
