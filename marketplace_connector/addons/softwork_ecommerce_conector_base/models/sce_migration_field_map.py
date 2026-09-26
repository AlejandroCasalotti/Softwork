# -*- coding: utf-8 -*-
"""Mapeo de campos editable para la migración Odoo → Odoo.

Solo persiste metadatos de esquema (nombres y tipos de campo), nunca datos
de negocio del cliente.
"""
from odoo import api, fields, models

COMPATIBILITY = [
    ("ok", "Compatible"),
    ("required", "Requerido en destino"),
    ("relation", "Relación"),
    ("missing_target", "No existe en destino"),
    ("readonly", "Solo lectura / calculado"),
    ("lines", "Líneas (no soportado aún)"),
    ("technical", "Técnico"),
]

# Campos que casi siempre conviene migrar en una primera pasada.
BASIC_FIELDS = frozenset(
    {
        "name", "display_name", "default_code", "barcode", "email", "phone", "mobile",
        "vat", "street", "street2", "city", "zip", "is_company", "active", "ref",
        "list_price", "standard_price", "type", "description", "note", "code",
        "complete_name", "amount", "sequence", "comment", "website", "lang",
    }
)


class SceMigrationFieldMap(models.Model):
    _name = "sce.migration.field.map"
    _description = "Mapeo de campos de migración Odoo a Odoo"
    _order = "model_name, sequence, field_label"

    run_id = fields.Many2one(
        "sce.odoo.migration.run", required=True, ondelete="cascade", index=True
    )
    model_name = fields.Char(string="Modelo", required=True, index=True)
    model_label = fields.Char(string="Entidad")
    source_field = fields.Char(string="Campo origen", required=True)
    target_field = fields.Char(string="Campo destino")
    field_label = fields.Char(string="Descripción")
    field_type = fields.Char(string="Tipo")
    relation_model = fields.Char(string="Relacionado con")
    compatibility = fields.Selection(COMPATIBILITY, default="ok", required=True, index=True)
    is_required = fields.Boolean(string="Obligatorio", readonly=True)
    migrate = fields.Boolean(string="Migrar", default=True)
    sequence = fields.Integer(default=10)

    _field_map_unique = models.Constraint(
        "UNIQUE(run_id, model_name, source_field)",
        "Ese campo ya está mapeado para esta entidad.",
    )

    @api.depends("field_label", "source_field")
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.model_name}: {record.field_label or record.source_field}"
