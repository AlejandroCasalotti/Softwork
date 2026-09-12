from odoo.exceptions import UserError

from .errors import ApiError


class RemoteCompanyContextResolver:
    """Build a validated Odoo JSON-2 product context for one remote company."""

    def __init__(self, connection, connection_service):
        self.connection = connection
        self.connection_service = connection_service

    def resolve(self):
        company_id = self.connection.external_company_id
        if not company_id:
            return None

        context = self.connection_service.remote_company_context()
        if not isinstance(context, dict):
            raise ApiError("Odoo remoto devolvió un contexto de empresa inválido.")
        allowed_company_ids = context.get("allowed_company_ids")
        if not isinstance(allowed_company_ids, list):
            raise ApiError("Odoo remoto no devolvió compañías permitidas válidas.")

        try:
            company_id = int(company_id)
            allowed_company_ids = {int(allowed_id) for allowed_id in allowed_company_ids}
        except (TypeError, ValueError):
            raise ApiError("Odoo remoto devolvió compañías permitidas inválidas.")

        if company_id not in allowed_company_ids:
            raise UserError(
                "La empresa remota configurada no está disponible para el usuario técnico de esta conexión."
            )
        return {
            "allowed_company_ids": [company_id],
            "company_id": company_id,
        }