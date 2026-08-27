import hashlib

from odoo import api, fields, models
from odoo.exceptions import UserError


class SceOAuthTransaction(models.Model):
    _name = "sce.oauth.transaction"
    _description = "SCE OAuth Transaction"
    _order = "create_date desc"

    state_hash = fields.Char(required=True, index=True, copy=False)
    tenant_id = fields.Many2one("sce.tenant", required=True, ondelete="cascade", index=True)
    user_id = fields.Many2one("res.users", required=True, ondelete="restrict", index=True)
    mercadolibre_account_id = fields.Many2one(
        "sce.mercadolibre.account", required=True, ondelete="cascade", index=True
    )
    code_verifier_secret_id = fields.Many2one("sce.secret", required=True, ondelete="restrict")
    expires_at = fields.Datetime(required=True, index=True)
    used_at = fields.Datetime(copy=False)
    status = fields.Selection(
        selection=[
            ("pending", "Pending"),
            ("used", "Used"),
            ("expired", "Expired"),
            ("cancelled", "Cancelled"),
        ],
        default="pending",
        required=True,
    )

    _state_hash_unique = models.Constraint(
        "UNIQUE(state_hash)",
        "El estado OAuth debe ser único.",
    )

    @api.model
    def hash_state(self, state):
        return hashlib.sha256(state.encode("utf-8")).hexdigest()

    def consume(self):
        self.ensure_one()
        if self.status != "pending":
            raise UserError("El estado OAuth ya fue utilizado o invalidado.")
        if fields.Datetime.now() >= self.expires_at:
            self.write({"status": "expired"})
            raise UserError("El estado OAuth expiró. Iniciá la conexión nuevamente.")
        self.write({"status": "used", "used_at": fields.Datetime.now()})
        return True
