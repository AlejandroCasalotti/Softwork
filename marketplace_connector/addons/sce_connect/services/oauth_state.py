import hashlib
import secrets
from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError


class OAuthStateService:
    STATE_TTL_MINUTES = 10

    def __init__(self, env):
        self.env = env

    @staticmethod
    def _challenge(verifier):
        import base64

        return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")

    def create(self, tenant, account, user):
        if account.tenant_id != tenant:
            raise AccessError("La cuenta de MercadoLibre no pertenece al tenant seleccionado.")
        state = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(64)
        secret = self.env["sce.secret"].sudo().create(
            {
                "name": f"OAuth PKCE verifier {account.name}",
                "tenant_id": tenant.id,
                "secret_type": "oauth_pkce_verifier",
            }
        )
        secret.with_context(sce_backend_secret_access=True).set_value(verifier)
        transaction = self.env["sce.oauth.transaction"].sudo().create(
            {
                "state_hash": hashlib.sha256(state.encode()).hexdigest(),
                "tenant_id": tenant.id,
                "user_id": user.id,
                "mercadolibre_account_id": account.id,
                "code_verifier_secret_id": secret.id,
                "expires_at": fields.Datetime.now() + timedelta(minutes=self.STATE_TTL_MINUTES),
            }
        )
        account.sudo().write({"status": "auth_pending", "last_error": False})
        return state, self._challenge(verifier), transaction

    def validate_and_consume(self, state, user, expected_tenant=None):
        if not state:
            raise UserError("Falta el estado OAuth.")
        state_hash = hashlib.sha256(state.encode()).hexdigest()
        transaction = self.env["sce.oauth.transaction"].sudo().search(
            [("state_hash", "=", state_hash)], limit=1
        )
        if not transaction:
            raise UserError("El estado OAuth no es válido o ya expiró.")
        # Never disclose which check failed: user and tenant mismatches share one generic error.
        if transaction.user_id.id != user.id:
            raise AccessError("El estado OAuth no es válido para el contexto actual.")
        if expected_tenant is not None and transaction.tenant_id.id != expected_tenant.id:
            raise AccessError("El estado OAuth no es válido para el contexto actual.")
        transaction.consume()
        return transaction
