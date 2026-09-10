from odoo import models


class SceAccount(models.Model):
    _inherit = "sce.account"

    def action_open_oauth_url(self):
        self.ensure_one()
        from ..services.mercadolibre_oauth_service import MercadoLibreOAuthService

        return {"type": "ir.actions.act_url", "url": MercadoLibreOAuthService(self.env).start(self), "target": "self"}

    def action_start_onboarding_connection(self):
        self.ensure_one()
        if self.provider_type == "mercadolibre":
            return self.action_open_oauth_url()
        return super().action_start_onboarding_connection()

    def action_refresh_token(self):
        for account in self.filtered(lambda record: record.provider_type == "mercadolibre"):
            from ..services.mercadolibre_token_service import MercadoLibreTokenService

            MercadoLibreTokenService(self.env).refresh(
                MercadoLibreTokenService(self.env)._identity(account)
            )
        return True

    def action_disconnect_mercadolibre(self):
        for account in self:
            from ..services.mercadolibre_token_service import MercadoLibreTokenService

            MercadoLibreTokenService(self.env).disconnect(account)
        return True