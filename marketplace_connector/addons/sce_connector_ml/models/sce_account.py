from odoo import api, fields, models
from odoo.exceptions import UserError


class SceAccount(models.Model):
    _inherit = "sce.account"

    ml_connection_status = fields.Selection(
        [
            ("disconnected", "Desconectado"),
            ("connecting", "Conectando"),
            ("connected", "Conectado"),
            ("syncing", "Sincronizando"),
            ("auth_required", "Necesita autorización"),
            ("error", "Con problemas"),
        ],
        compute="_compute_ml_dashboard",
    )
    ml_status_message = fields.Char(compute="_compute_ml_dashboard")
    ml_seller_nickname = fields.Char(compute="_compute_ml_dashboard")
    ml_site_id = fields.Char(compute="_compute_ml_dashboard")
    ml_publication_count = fields.Integer(compute="_compute_ml_dashboard")
    ml_publication_synced_count = fields.Integer(compute="_compute_ml_dashboard")
    ml_publication_problem_count = fields.Integer(compute="_compute_ml_dashboard")
    ml_running_sync_jobs = fields.Integer(compute="_compute_ml_dashboard")

    def _get_mercadolibre_identity(self):
        self.ensure_one()
        return self.env["sce.mercadolibre.account"].sudo().search(
            [("account_id", "=", self.id)],
            limit=1,
        )

    def _sync_mercadolibre_runtime_state(self, identity=None, last_error=None):
        for account in self.filtered(lambda record: record.provider_type == "mercadolibre"):
            current_identity = (
                identity
                if identity and identity.account_id == account
                else account._get_mercadolibre_identity()
            )
            identity_status = current_identity.status if current_identity else "disconnected"
            values = {
                "external_user_id": current_identity.seller_user_id if current_identity else False,
                "external_account_ref": current_identity.seller_nickname if current_identity else False,
                "token_expires_at": current_identity.expires_at if current_identity else False,
            }
            if identity_status == "connected":
                values.update({"state": "connected", "last_error": False})
            elif identity_status == "auth_pending":
                values.update({"state": "draft", "last_error": False})
            elif identity_status in ("auth_required", "error"):
                values.update(
                    {
                        "state": "error",
                        "last_error": last_error
                        or current_identity.last_error
                        or "Mercado Libre necesita que vuelvas a autorizar la conexión.",
                    }
                )
            else:
                values.update({"state": "draft", "last_error": last_error or False})
            account.sudo().write(values)
        return True

    @api.depends(
        "state",
        "last_error",
        "external_user_id",
        "external_account_ref",
        "last_sync",
        "job_ids.state",
    )
    def _compute_ml_dashboard(self):
        Publication = self.env["marketplace.publication"].sudo()
        mercadolibre_accounts = self.filtered(
            lambda account: account.provider_type == "mercadolibre"
        )
        publication_map = {account.id: Publication.browse() for account in mercadolibre_accounts}
        if mercadolibre_accounts:
            for publication in Publication.search(
                [("account_id", "in", mercadolibre_accounts.ids)]
            ):
                publication_map[publication.account_id.id] |= publication
            identity_map = {
                identity.account_id.id: identity
                for identity in self.env["sce.mercadolibre.account"].sudo().search(
                    [("account_id", "in", mercadolibre_accounts.ids)]
                )
            }
        else:
            identity_map = {}

        for account in self:
            if account.provider_type != "mercadolibre":
                account.ml_connection_status = False
                account.ml_status_message = False
                account.ml_seller_nickname = False
                account.ml_site_id = False
                account.ml_publication_count = 0
                account.ml_publication_synced_count = 0
                account.ml_publication_problem_count = 0
                account.ml_running_sync_jobs = 0
                continue

            identity = identity_map.get(account.id)
            publications = publication_map.get(account.id, Publication.browse())
            running_jobs = account.job_ids.filtered(lambda job: job.state in ("queued", "running"))

            account.ml_seller_nickname = identity.seller_nickname if identity else False
            account.ml_site_id = identity.site_id if identity else False
            account.ml_publication_count = len(publications)
            account.ml_publication_synced_count = len(
                publications.filtered(lambda publication: publication.external_id and not publication.error_message)
            )
            account.ml_publication_problem_count = len(
                publications.filtered(lambda publication: bool(publication.error_message))
            )
            account.ml_running_sync_jobs = len(running_jobs)

            identity_status = identity.status if identity else "disconnected"
            if running_jobs and account.state == "connected":
                account.ml_connection_status = "syncing"
                account.ml_status_message = "Mercado Libre está sincronizando la cuenta."
            elif identity_status == "connected" and account.state == "connected":
                account.ml_connection_status = "connected"
                account.ml_status_message = "La cuenta está lista para sincronizar productos, precios, stock y ventas."
            elif identity_status == "auth_pending":
                account.ml_connection_status = "connecting"
                account.ml_status_message = "Completá la autorización en Mercado Libre para terminar la conexión."
            elif identity_status == "auth_required":
                account.ml_connection_status = "auth_required"
                account.ml_status_message = (
                    account.last_error
                    or identity.last_error
                    or "Mercado Libre necesita que vuelvas a autorizar la conexión."
                )
            elif account.state == "error" or identity_status == "error":
                account.ml_connection_status = "error"
                account.ml_status_message = (
                    account.last_error
                    or identity.last_error
                    or "Hay problemas con la sincronización de Mercado Libre."
                )
            else:
                account.ml_connection_status = "disconnected"
                account.ml_status_message = "Conectá tu cuenta para comenzar a sincronizar tu negocio."

    def action_open_oauth_url(self):
        self.ensure_one()
        from ..services.mercadolibre_oauth_service import MercadoLibreOAuthService

        return {
            "type": "ir.actions.act_url",
            "url": MercadoLibreOAuthService(self.env).start(self),
            "target": "self",
        }

    def action_start_onboarding_connection(self):
        self.ensure_one()
        if self.provider_type == "mercadolibre":
            return self.action_open_oauth_url()
        return super().action_start_onboarding_connection()

    def action_reconnect_mercadolibre(self):
        self.ensure_one()
        if self.provider_type != "mercadolibre":
            raise UserError("La reconexión está disponible solo para Mercado Libre.")
        return self.action_open_oauth_url()

    def action_refresh_token(self):
        for account in self.filtered(lambda record: record.provider_type == "mercadolibre"):
            from ..services.mercadolibre_token_service import MercadoLibreTokenService

            token_service = MercadoLibreTokenService(self.env)
            identity = token_service.refresh(token_service._identity(account))
            account._sync_mercadolibre_runtime_state(identity=identity)
        return True

    def action_disconnect_mercadolibre(self):
        for account in self.filtered(lambda record: record.provider_type == "mercadolibre"):
            from ..services.mercadolibre_token_service import MercadoLibreTokenService

            MercadoLibreTokenService(self.env).disconnect(account)
        return True

    def action_sync_now(self):
        self.ensure_one()
        if self.provider_type != "mercadolibre":
            raise UserError("La sincronización manual está disponible para Mercado Libre.")
        if self.ml_connection_status not in ("connected", "syncing"):
            raise UserError("Autorizá la cuenta de Mercado Libre antes de sincronizar.")

        publication_service = self.env["marketplace.publication.service"]
        publications = self.env["marketplace.publication"].search(
            [("account_id", "=", self.id), ("external_id", "!=", False)]
        )
        created_jobs = self.env["sce.job"]
        sync_counts = {"productos": 0, "precios": 0, "stock": 0, "ventas": 0}

        for publication in publications:
            created_jobs |= publication_service.enqueue(publication, "sync")
            sync_counts["productos"] += 1
            if self.sync_prices:
                created_jobs |= publication_service.enqueue(publication, "update_price")
                sync_counts["precios"] += 1
            if self.sync_stock:
                created_jobs |= publication_service.enqueue(publication, "update_stock")
                sync_counts["stock"] += 1

        if self.sync_orders:
            pending_orders_job = self.env["sce.job"].search(
                [
                    ("account_id", "=", self.id),
                    ("job_type", "=", "import_orders"),
                    ("state", "in", ["queued", "running"]),
                ],
                limit=1,
            )
            if pending_orders_job:
                created_jobs |= pending_orders_job
            else:
                created_jobs |= self.env["sce.job"].create(
                    {
                        "name": "Sync Ventas - %s" % self.display_name,
                        "account_id": self.id,
                        "job_type": "import_orders",
                        "payload_json": "{}",
                    }
                )
            sync_counts["ventas"] = 1

        if not created_jobs:
            raise UserError("Todavía no hay publicaciones ni ventas pendientes para sincronizar.")

        self.write({"last_sync": fields.Datetime.now(), "last_error": False})
        lines = [
            f"Productos: {sync_counts['productos']}",
            f"Precios: {sync_counts['precios']}",
            f"Stock: {sync_counts['stock']}",
            f"Ventas: {sync_counts['ventas']}",
        ]
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Sincronización iniciada",
                "message": "\n".join(lines),
                "type": "success",
                "sticky": False,
            },
        }
