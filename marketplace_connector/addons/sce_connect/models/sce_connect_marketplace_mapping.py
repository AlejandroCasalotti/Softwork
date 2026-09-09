from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SceConnectMarketplaceMapping(models.Model):
    _name = "sce.connect.marketplace.mapping"
    _description = "SCE Connect Marketplace Identity Mapping"
    _order = "tenant_id, marketplace_account_id, marketplace_item_id, marketplace_variation_id, id"

    tenant_id = fields.Many2one("sce.tenant", required=True, ondelete="cascade", index=True)
    external_connection_id = fields.Many2one(
        "sce.external.connection", required=True, ondelete="cascade", index=True
    )
    external_product_mapping_id = fields.Many2one(
        "sce.external.product.mapping", required=True, ondelete="cascade", index=True
    )
    marketplace_account_id = fields.Many2one(
        "sce.account", required=True, ondelete="restrict", index=True
    )
    marketplace_item_id = fields.Char(required=True, index=True)
    marketplace_variation_id = fields.Char(index=True)
    sku = fields.Char(index=True)
    active = fields.Boolean(default=True)
    mapping_status = fields.Selection(
        [
            ("draft", "Draft"),
            ("verified", "Verified"),
            ("conflict", "Conflict"),
            ("inactive", "Inactive"),
        ],
        default="draft",
        required=True,
        index=True,
    )
    verified_at = fields.Datetime(readonly=True)
    last_stock_source = fields.Integer(string="Último stock origen", readonly=True, copy=False)
    last_stock_sent = fields.Integer(string="Último stock enviado", readonly=True, copy=False)
    last_stock_sync_at = fields.Datetime(string="Última sincronización de stock", readonly=True, copy=False)
    last_stock_error = fields.Text(string="Último error de stock", readonly=True, copy=False)

    _external_product_account_unique = models.Constraint(
        "UNIQUE(external_product_mapping_id, marketplace_account_id)",
        "El producto externo ya está relacionado con esta cuenta marketplace.",
    )

    def init(self):
        self.env.cr.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS sce_connect_marketplace_mapping_simple_uniq
            ON sce_connect_marketplace_mapping (marketplace_account_id, marketplace_item_id)
            WHERE marketplace_variation_id IS NULL
            """
        )
        self.env.cr.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS sce_connect_marketplace_mapping_variation_uniq
            ON sce_connect_marketplace_mapping
                (marketplace_account_id, marketplace_item_id, marketplace_variation_id)
            WHERE marketplace_variation_id IS NOT NULL
            """
        )

    @api.constrains(
        "tenant_id",
        "external_connection_id",
        "external_product_mapping_id",
        "marketplace_account_id",
    )
    def _check_identity_scope(self):
        for mapping in self:
            connection = mapping.external_connection_id
            product_mapping = mapping.external_product_mapping_id
            marketplace_account = mapping.marketplace_account_id
            connect_account = marketplace_account.connect_mercadolibre_account_id

            if connection.tenant_id != mapping.tenant_id:
                raise ValidationError("La conexión Odoo externa debe pertenecer al tenant del mapping.")
            if product_mapping.external_connection_id != connection:
                raise ValidationError("El producto externo debe pertenecer a la conexión Odoo indicada.")
            if product_mapping.external_model != "product.product":
                raise ValidationError("El mapping Connect marketplace requiere una variante product.product externa.")
            if marketplace_account.provider_type != "mercadolibre":
                raise ValidationError("La cuenta marketplace debe ser de tipo MercadoLibre.")
            if not connect_account:
                raise ValidationError("La cuenta marketplace debe vincular una cuenta MercadoLibre Connect.")
            if connect_account.tenant_id != mapping.tenant_id:
                raise ValidationError("La cuenta MercadoLibre Connect debe pertenecer al tenant del mapping.")

    def action_sync_stock(self):
        self.ensure_one()
        result = self.env["sce.connect.stock.service"].sync_mapping(self)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Stock Connect",
                "message": (
                    "Stock origen: %(source)s | Stock enviado: %(sent)s%(skipped)s"
                ) % {
                    "source": result.get("source_stock", self.last_stock_source),
                    "sent": result.get("available_quantity", self.last_stock_sent),
                    "skipped": " | Sin cambios" if result.get("skipped") else "",
                },
                "type": "success",
                "sticky": False,
            },
        }

    @api.model
    def cron_enqueue_stock_sync(self):
        mappings = self.search(
            [
                ("active", "=", True),
                ("mapping_status", "=", "verified"),
                ("marketplace_item_id", "!=", False),
            ],
            limit=100,
            order="id asc",
        )
        service = self.env["sce.connect.stock.service"]
        for mapping in mappings:
            service.enqueue_mapping(mapping)