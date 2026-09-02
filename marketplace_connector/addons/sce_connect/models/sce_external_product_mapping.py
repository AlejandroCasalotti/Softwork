from odoo import fields, models


class SceExternalProductMapping(models.Model):
    _name = "sce.external.product.mapping"
    _description = "SCE Connect External Product Identity Mapping"
    _order = "external_model, external_id"

    tenant_id = fields.Many2one(
        "sce.tenant", related="external_connection_id.tenant_id", store=True, index=True, readonly=True
    )
    external_connection_id = fields.Many2one(
        "sce.external.connection", required=True, ondelete="cascade", index=True
    )
    external_model = fields.Char(required=True, index=True, help="Modelo Odoo externo, p. ej. product.template.")
    external_id = fields.Integer(required=True, index=True, help="ID numérico del registro en el Odoo externo.")
    external_write_date = fields.Datetime(help="Último write_date leído del registro externo.")
    parent_mapping_id = fields.Many2one(
        "sce.external.product.mapping", ondelete="cascade", index=True,
        help="Mapping del product.template al que pertenece esta variante.",
    )

    # Solo reconciliación/caché de diagnóstico. Nunca identidad.
    name = fields.Char()
    default_code = fields.Char(index=True)
    barcode = fields.Char(index=True)
    list_price = fields.Float()
    standard_price = fields.Float()
    active = fields.Boolean(default=True)

    missing_fields_json = fields.Text(help="Campos solicitados no disponibles en el Odoo externo.")
    last_synced_at = fields.Datetime(readonly=True)

    _uniq_external_identity = models.Constraint(
        "UNIQUE(external_connection_id, external_model, external_id)",
        "Ya existe un mapping para este registro externo.",
    )
