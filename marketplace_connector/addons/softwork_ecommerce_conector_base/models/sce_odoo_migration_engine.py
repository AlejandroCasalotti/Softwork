# -*- coding: utf-8 -*-
"""Motor genérico de migración remota Odoo → Odoo.

SCE actúa solo como orquestador: lee del Odoo origen y escribe en el Odoo destino
vía XML-RPC. No persiste datos del cliente; las cachés viven en memoria durante
la corrida y el checkpoint guarda únicamente IDs de avance.
"""
import logging
from datetime import timedelta

from markupsafe import Markup, escape

from odoo import api, fields, models
from odoo.exceptions import UserError

from .sce_migration_field_map import BASIC_FIELDS

_logger = logging.getLogger(__name__)

# Campos técnicos/sociales que nunca se migran.
SKIP_FIELDS = frozenset(
    {
        "id",
        "create_uid",
        "create_date",
        "write_uid",
        "write_date",
        "__last_update",
        "display_name",
        "message_ids",
        "message_follower_ids",
        "message_partner_ids",
        "message_main_attachment_id",
        "message_attachment_count",
        "message_has_error",
        "message_has_error_counter",
        "message_needaction",
        "message_needaction_counter",
        "message_is_follower",
        "website_message_ids",
        "activity_ids",
        "activity_state",
        "activity_user_id",
        "activity_type_id",
        "activity_date_deadline",
        "activity_summary",
        "activity_exception_decoration",
        "activity_exception_icon",
        "my_activity_date_deadline",
        "access_token",
        "access_url",
        "access_warning",
        "rating_ids",
    }
)

# Claves naturales para emparejar un registro del origen con su equivalente en
# el destino. Se evalúan en orden hasta encontrar coincidencia.
MATCH_KEYS = {
    "res.partner": (("vat",), ("email",), ("name",)),
    "res.partner.category": (("name",),),
    "res.users": (("login",),),
    "res.company": (("name",),),
    "res.country": (("code",),),
    "res.country.state": (("code", "country_id"),),
    "res.currency": (("name",),),
    "product.template": (("default_code",), ("barcode",), ("name",)),
    "product.product": (("default_code",), ("barcode",), ("name",)),
    "product.category": (("complete_name",), ("name",)),
    "product.public.category": (("name",),),
    "product.supplierinfo": (("partner_id", "product_tmpl_id"),),
    "product.attribute": (("name",),),
    "product.attribute.value": (("name", "attribute_id"),),
    "uom.uom": (("name",),),
    "uom.category": (("name",),),
    "account.tax": (("name", "type_tax_use"),),
    "account.tax.group": (("name",),),
    "account.account": (("code",),),
    "account.journal": (("code",), ("name",)),
    "account.payment.term": (("name",),),
    "account.move": (("name", "move_type"),),
    "account.payment": (("name",),),
    "account.move.line": (("move_id", "account_id", "name", "debit", "credit"),),
    "account.partial.reconcile": (("debit_move_id", "credit_move_id", "amount"),),
    "account.fiscal.position": (("name",),),
    "sale.order": (("name",),),
    "purchase.order": (("name",),),
    "stock.warehouse": (("code",), ("name",)),
    "stock.location": (("complete_name",), ("name",)),
    "stock.picking.type": (("name", "code"),),
    "crm.team": (("name",),),
    "pos.category": (("name",),),
    "ir.attachment": (("name", "res_model", "res_id"),),
    "product.pricelist": (("name",),),
}

# Orden de migración: las dependencias van primero.
MIGRATION_ENTITIES = (
    ("sync_product_categories", "product.category", "migrated_product_categories"),
    ("sync_product_web_categories", "product.public.category", "migrated_product_web_categories"),
    ("sync_taxes", "account.tax", "migrated_taxes"),
    ("sync_partners", "res.partner", "migrated_partners"),
    ("sync_products", "product.template", "migrated_products"),
    ("sync_product_suppliers", "product.supplierinfo", "migrated_product_suppliers"),
    ("sync_stock_warehouses", "stock.warehouse", "migrated_warehouses"),
    ("sync_stock_locations", "stock.location", "migrated_locations"),
    ("sync_sales", "sale.order", "migrated_sales"),
    ("sync_purchases", "purchase.order", "migrated_purchases"),
    ("sync_invoices", "account.move", "migrated_invoices"),
    ("sync_payments", "account.payment", "migrated_payments"),
    ("sync_reconciliations", "account.partial.reconcile", "migrated_reconciliations"),
    ("sync_documents", "ir.attachment", "migrated_documents"),
)

MAX_RELATION_DEPTH = 3

# Modelos con campos binarios: lotes chicos para no agotar memoria ni el RPC.
MODEL_BATCH_LIMITS = {"ir.attachment": 20}

# Documentos que se migran junto con sus líneas: (campo o2m, modelo hijo, campo padre).
CHILD_LINES = {
    "sale.order": ("order_line", "sale.order.line", "order_id"),
    "purchase.order": ("order_line", "purchase.order.line", "order_id"),
    "account.move": ("invoice_line_ids", "account.move.line", "move_id"),
}

# Campos de línea que el destino recalcula o que romperían la creación.
LINE_SKIP_FIELDS = frozenset(
    {
        "move_id", "order_id", "company_id", "currency_id", "state",
        "invoice_id", "parent_state", "date", "move_name", "journal_id",
        "debit", "credit", "balance", "amount_currency", "reconciled",
        "full_reconcile_id", "matched_debit_ids", "matched_credit_ids",
        "tax_repartition_line_id", "tax_line_id", "tax_base_amount",
        "qty_invoiced", "qty_delivered", "qty_to_invoice", "invoice_lines",
        "invoice_status", "untaxed_amount_invoiced", "untaxed_amount_to_invoice",
    }
)


class SceOdooMigrationEngine(models.Model):
    _inherit = "sce.odoo.migration.run"

    field_map_ids = fields.One2many(
        "sce.migration.field.map", "run_id", string="Mapeo de campos"
    )
    field_map_analyzed = fields.Boolean(default=False, readonly=True, copy=False)
    field_map_count = fields.Integer(compute="_compute_field_map_count")
    field_map_selected_count = fields.Integer(compute="_compute_field_map_count")

    def _compute_field_map_count(self):
        for record in self:
            lines = record.field_map_ids
            record.field_map_count = len(lines)
            record.field_map_selected_count = len(lines.filtered("migrate"))

    # --- Contexto de corrida (solo en memoria, nada se persiste en SCE) ---

    def _build_migration_context(self, src_uid, src_rpc, dst_uid, dst_rpc):
        self.ensure_one()
        account = self.account_id
        return {
            "src": {
                "rpc": src_rpc,
                "db": account.odoo_source_db,
                "uid": src_uid,
                "pwd": account.odoo_source_api_key,
            },
            "dst": {
                "rpc": dst_rpc,
                "db": account.odoo_target_db,
                "uid": dst_uid,
                "pwd": account.odoo_target_api_key,
            },
            "fields_cache": {},
            "relation_cache": {},
            "unresolved": {},
        }

    def _call(self, ctx, side, model, method, *args, **kwargs):
        conn = ctx[side]
        return self._rpc_call(conn["rpc"], conn["db"], conn["uid"], conn["pwd"], model, method, *args, **kwargs)

    def _cached_fields(self, ctx, side, model):
        """fields_get cacheado por corrida: evita una llamada RPC por registro."""
        key = (side, model)
        cache = ctx["fields_cache"]
        if key not in cache:
            conn = ctx[side]
            try:
                cache[key] = self._rpc_call(
                    conn["rpc"],
                    conn["db"],
                    conn["uid"],
                    conn["pwd"],
                    model,
                    "fields_get",
                    [],
                    attributes=["type", "readonly", "required", "relation", "string"],
                ) or {}
            except Exception:
                cache[key] = {}
        return cache[key]

    def _model_exists(self, ctx, side, model):
        return bool(self._cached_fields(ctx, side, model))

    # --- Resolución de relaciones por clave natural ---

    def _extract_id(self, value):
        if isinstance(value, (list, tuple)) and value:
            return value[0]
        if isinstance(value, dict):
            return value.get("id")
        if isinstance(value, int):
            return value
        return False

    def _match_domain_for(self, ctx, model, src_record, keys, depth):
        domain = []
        for key in keys:
            if key not in src_record:
                return None
            value = src_record.get(key)
            if value in (False, None, ""):
                return None
            if isinstance(value, (list, tuple, dict)):
                src_fields = self._cached_fields(ctx, "src", model)
                comodel = (src_fields.get(key) or {}).get("relation")
                if not comodel:
                    return None
                resolved = self._resolve_relation(ctx, comodel, value, depth + 1)
                if not resolved:
                    return None
                domain.append((key, "=", resolved))
            else:
                domain.append((key, "=", value))
        return domain

    def _resolve_relation(self, ctx, model, src_value, depth=0):
        """Traduce un many2one del origen al ID equivalente en el destino.

        Nunca copia el ID de origen: eso apuntaría a un registro distinto.
        """
        if not model or depth > MAX_RELATION_DEPTH:
            return False
        src_id = self._extract_id(src_value)
        if not src_id:
            return False

        cache_key = (model, src_id)
        if cache_key in ctx["relation_cache"]:
            return ctx["relation_cache"][cache_key]

        result = False
        keys_sets = MATCH_KEYS.get(model) or (("name",),)
        needed = sorted({field for keys in keys_sets for field in keys})
        src_fields = self._cached_fields(ctx, "src", model)
        readable = [field for field in needed if field in src_fields]

        if readable:
            try:
                records = self._call(ctx, "src", model, "read", [src_id], fields=readable)
            except Exception:
                records = []
            src_record = records[0] if records else {}
            dst_fields = self._cached_fields(ctx, "dst", model)
            for keys in keys_sets:
                if any(key not in dst_fields for key in keys):
                    continue
                domain = self._match_domain_for(ctx, model, src_record, keys, depth)
                if not domain:
                    continue
                try:
                    found = self._call(ctx, "dst", model, "search", domain, limit=1)
                except Exception:
                    found = []
                if found:
                    result = found[0]
                    break

        if not result:
            ctx["unresolved"][model] = ctx["unresolved"].get(model, 0) + 1
        ctx["relation_cache"][cache_key] = result
        return result

    # --- Preparación de valores ---

    def _get_allowed_fields(self, model):
        """Campos habilitados por el usuario, o None si esa entidad no fue mapeada."""
        lines = self.field_map_ids.filtered(lambda line: line.model_name == model)
        if not self.field_map_analyzed:
            return None
        return {line.source_field for line in lines if line.migrate}

    def _prepare_remote_vals(self, ctx, model, src_vals, dst_fields, allowed=None):
        vals = {}
        for fname, fdef in dst_fields.items():
            if fname in SKIP_FIELDS or fdef.get("readonly"):
                continue
            if fname not in src_vals:
                continue
            if allowed is not None and fname not in allowed:
                continue

            ftype = fdef.get("type")
            value = src_vals.get(fname)

            if ftype == "one2many":
                continue

            if value in (False, None):
                if ftype not in ("many2one", "many2many"):
                    vals[fname] = value
                continue

            if ftype == "many2one":
                resolved = self._resolve_relation(ctx, fdef.get("relation"), value)
                if resolved:
                    vals[fname] = resolved
            elif ftype == "many2many":
                comodel = fdef.get("relation")
                resolved_ids = []
                for item in value if isinstance(value, (list, tuple)) else []:
                    target_id = self._resolve_relation(ctx, comodel, item)
                    if target_id:
                        resolved_ids.append(target_id)
                if resolved_ids:
                    vals[fname] = [(6, 0, resolved_ids)]
            else:
                vals[fname] = value
        return vals

    def _find_existing_target(self, ctx, model, src_vals, dst_fields):
        for keys in MATCH_KEYS.get(model) or (("name",),):
            if any(key not in dst_fields for key in keys):
                continue
            domain = self._match_domain_for(ctx, model, src_vals, keys, 0)
            if not domain:
                continue
            try:
                found = self._call(ctx, "dst", model, "search", domain, limit=1)
            except Exception:
                found = []
            if found:
                return found[0]
        return False

    # --- Motor genérico ---

    def _iter_model_batches(self, model, ids_list):
        size = max(1, int(self.batch_size or 100))
        limit = MODEL_BATCH_LIMITS.get(model)
        if limit:
            size = min(size, limit)
        for start in range(0, len(ids_list), size):
            yield ids_list[start:start + size]

    def _sync_remote_model(self, ctx, model, counter_field, cp):
        """Migra un modelo completo de origen a destino con mapeo dinámico."""
        self.ensure_one()
        errors = []

        if not self._model_exists(ctx, "src", model) or not self._model_exists(ctx, "dst", model):
            _logger.info("Migración: se omite %s (no existe en origen o destino)", model)
            return errors

        src_fields = self._cached_fields(ctx, "src", model)
        dst_fields = self._cached_fields(ctx, "dst", model)
        allowed = self._get_allowed_fields(model)
        if allowed is not None and not allowed:
            return errors

        readable = [
            name
            for name in dst_fields
            if name in src_fields
            and name not in SKIP_FIELDS
            and src_fields[name].get("type") != "one2many"
            and (allowed is None or name in allowed)
        ]
        # Las claves naturales se leen siempre: se usan para no duplicar en destino.
        for keys in MATCH_KEYS.get(model) or (("name",),):
            for key in keys:
                if key in src_fields and key not in readable:
                    readable.append(key)
        if not readable:
            return errors

        try:
            source_ids = self._call(ctx, "src", model, "search", self._build_since_domain())
        except Exception as err:
            errors.append({"model": model, "id": False, "error": str(err)})
            return errors

        checkpoint_key = f"{model}_last_id"
        last_id = cp.get(checkpoint_key, 0)
        pending = [rid for rid in sorted(source_ids) if rid > last_id]
        migrated = 0

        for batch in self._iter_model_batches(model, pending):
            try:
                records = self._call(ctx, "src", model, "read", batch, fields=readable)
            except Exception as err:
                errors.append({"model": model, "id": False, "error": str(err)})
                if not self.continue_on_error:
                    raise
                continue

            for src_vals in records:
                record_id = src_vals.get("id")

                def _process(_rid, _vals=src_vals):
                    write_vals = self._prepare_remote_vals(ctx, model, _vals, dst_fields, allowed)
                    if not write_vals:
                        return
                    existing = self._find_existing_target(ctx, model, _vals, dst_fields)
                    if existing:
                        # Las líneas no se reescriben: evitaría duplicarlas o borrar ajustes del destino.
                        self._call(ctx, "dst", model, "write", existing, write_vals)
                    else:
                        line_commands = self._build_child_lines(ctx, model, _rid)
                        if line_commands:
                            write_vals[CHILD_LINES[model][0]] = line_commands
                        self._call(ctx, "dst", model, "create", write_vals)

                if self._safe_process_record(_process, record_id, cp, checkpoint_key, errors, model):
                    migrated += 1

        if migrated and counter_field in self._fields:
            self[counter_field] = (self[counter_field] or 0) + migrated
        return errors

    def _build_child_lines(self, ctx, model, parent_src_id):
        """Arma los comandos (0, 0, vals) de las líneas de un documento."""
        config = CHILD_LINES.get(model)
        if not config:
            return []
        o2m_field, line_model, parent_field = config
        if not self._model_exists(ctx, "src", line_model) or not self._model_exists(ctx, "dst", line_model):
            return []

        src_line_fields = self._cached_fields(ctx, "src", line_model)
        dst_line_fields = self._cached_fields(ctx, "dst", line_model)
        allowed_lines = self._get_allowed_fields(line_model)

        readable = [
            name
            for name in dst_line_fields
            if name in src_line_fields
            and name not in SKIP_FIELDS
            and name not in LINE_SKIP_FIELDS
            and src_line_fields[name].get("type") != "one2many"
            and (allowed_lines is None or name in allowed_lines)
        ]
        if not readable:
            return []

        try:
            line_ids = self._call(
                ctx, "src", line_model, "search", [(parent_field, "=", parent_src_id)]
            )
            if not line_ids:
                return []
            src_lines = self._call(ctx, "src", line_model, "read", line_ids, fields=readable)
        except Exception:
            _logger.warning("No se pudieron leer las líneas de %s (documento %s)", line_model, parent_src_id)
            return []

        commands = []
        for src_line in src_lines:
            line_vals = self._prepare_remote_vals(
                ctx, line_model, src_line, dst_line_fields, allowed_lines
            )
            for skipped in LINE_SKIP_FIELDS:
                line_vals.pop(skipped, None)
            if line_vals:
                commands.append((0, 0, line_vals))
        return commands

    def _iter_selected_entities(self):
        for toggle, model, counter in MIGRATION_ENTITIES:
            if toggle in self._fields and self[toggle]:
                yield model, counter

    def _iter_selected_line_models(self):
        """Modelos de línea de los documentos seleccionados."""
        for model, _counter in self._iter_selected_entities():
            config = CHILD_LINES.get(model)
            if config:
                yield model, config[1]

    # --- Análisis de campos (Etapa B) ---

    def _classify_field(self, fname, src_def, dst_def):
        """Devuelve (compatibilidad, migrar_por_defecto) para un campo del origen."""
        if fname in SKIP_FIELDS:
            return "technical", False
        if not dst_def:
            return "missing_target", False
        if dst_def.get("readonly"):
            return "readonly", False
        if dst_def.get("type") == "one2many":
            return "lines", False
        if dst_def.get("required"):
            return "required", True
        if dst_def.get("type") in ("many2one", "many2many"):
            return "relation", True
        return "ok", True

    def action_analyze_fields(self):
        """Introspecciona origen y destino y arma el mapeo editable."""
        self.ensure_one()
        entities = list(self._iter_selected_entities())
        if not entities:
            raise UserError("Seleccioná al menos una entidad para migrar antes de analizar campos.")

        src_uid, src_rpc, dst_uid, dst_rpc = self._validate_source_target_connections()
        ctx = self._build_migration_context(src_uid, src_rpc, dst_uid, dst_rpc)

        self.field_map_ids.unlink()
        entity_labels = dict(
            (model, label)
            for label, model in [
                ("Contactos", "res.partner"),
                ("Productos", "product.template"),
                ("Categorías de producto", "product.category"),
                ("Categorías web", "product.public.category"),
                ("Proveedores de producto", "product.supplierinfo"),
                ("Impuestos", "account.tax"),
                ("Ventas", "sale.order"),
                ("Compras", "purchase.order"),
                ("Facturas", "account.move"),
                ("Pagos", "account.payment"),
                ("Conciliaciones", "account.partial.reconcile"),
                ("Documentos", "ir.attachment"),
                ("Almacenes", "stock.warehouse"),
                ("Ubicaciones", "stock.location"),
            ]
        )

        lines = []
        skipped_models = []
        analyzed = [(model, entity_labels.get(model, model)) for model, _counter in entities]
        for parent_model, line_model in self._iter_selected_line_models():
            parent_label = entity_labels.get(parent_model, parent_model)
            analyzed.append((line_model, f"{parent_label} (líneas)"))

        for model, label in analyzed:
            src_fields = self._cached_fields(ctx, "src", model)
            dst_fields = self._cached_fields(ctx, "dst", model)
            if not src_fields or not dst_fields:
                skipped_models.append(model)
                continue

            is_line_model = model in {config[1] for config in CHILD_LINES.values()}
            for fname, src_def in sorted(src_fields.items()):
                if is_line_model and fname in LINE_SKIP_FIELDS:
                    continue
                dst_def = dst_fields.get(fname)
                compatibility, migrate = self._classify_field(fname, src_def, dst_def)
                if compatibility == "technical":
                    continue
                lines.append(
                    {
                        "run_id": self.id,
                        "model_name": model,
                        "model_label": label,
                        "source_field": fname,
                        "target_field": fname if dst_def else False,
                        "field_label": src_def.get("string") or fname,
                        "field_type": (dst_def or src_def).get("type"),
                        "relation_model": (dst_def or src_def).get("relation") or False,
                        "compatibility": compatibility,
                        "is_required": bool((dst_def or {}).get("required")),
                        "migrate": migrate,
                        "sequence": 5 if fname in ("name", "default_code") else 10,
                    }
                )

        if lines:
            self.env["sce.migration.field.map"].create(lines)
        self.field_map_analyzed = True

        message = f"Se analizaron {len(lines)} campos en {len(analyzed) - len(skipped_models)} entidades."
        if skipped_models:
            message += f" Sin equivalente en origen/destino: {', '.join(skipped_models)}."
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Análisis de campos completado",
                "message": message,
                "type": "success",
                "sticky": False,
            },
        }

    def action_field_map_select_recommended(self):
        self.ensure_one()
        for line in self.field_map_ids:
            line.migrate = line.compatibility in ("ok", "required", "relation")
        return True

    def action_field_map_select_basic(self):
        self.ensure_one()
        for line in self.field_map_ids:
            line.migrate = line.compatibility == "required" or (
                line.compatibility in ("ok", "relation") and line.source_field in BASIC_FIELDS
            )
        return True

    def action_field_map_select_none(self):
        self.ensure_one()
        self.field_map_ids.filtered(lambda line: not line.is_required).migrate = False
        return True

    def action_preview_remote_sample(self):
        """Muestra hasta tres registros remotos en una notificación; no los persiste en SCE."""
        self.ensure_one()
        entities = list(self._iter_selected_entities())
        if not entities:
            raise UserError("Seleccioná entidades y analizá los campos antes de pedir la vista previa.")
        if not self.field_map_ids:
            raise UserError("Primero presioná 'Analizar campos'.")

        src_uid, src_rpc, dst_uid, dst_rpc = self._validate_source_target_connections()
        ctx = self._build_migration_context(src_uid, src_rpc, dst_uid, dst_rpc)
        output = ["Muestra remota de origen (máximo 3 registros, solo lectura):"]
        remaining = 3
        secret_tokens = ("password", "secret", "token", "api_key", "private_key")
        for model, _counter in entities:
            if remaining <= 0:
                break
            selected = self.field_map_ids.filtered(
                lambda line: line.model_name == model and line.migrate
            )
            src_fields = self._cached_fields(ctx, "src", model)
            field_names = [
                line.source_field
                for line in selected
                if line.source_field in src_fields
                and src_fields[line.source_field].get("type") not in ("binary", "one2many")
                and not any(token in line.source_field.lower() for token in secret_tokens)
            ][:6]
            if not field_names:
                continue
            try:
                ids = self._call(ctx, "src", model, "search", self._build_since_domain(), limit=remaining)
                if not ids:
                    continue
                samples = self._call(ctx, "src", model, "read", ids[:remaining], fields=field_names)
            except Exception as error:
                output.append(f"{model}: no se pudo leer la muestra ({error}).")
                continue
            output.append(f"\n{model}:")
            for sample in samples:
                values = []
                for field_name in field_names:
                    value = sample.get(field_name)
                    if isinstance(value, (list, tuple)):
                        value = value[1] if len(value) > 1 else (value[0] if value else False)
                    text = str(value if value not in (None, False) else "")
                    if len(text) > 80:
                        text = text[:77] + "..."
                    values.append(f"{field_name}={text}")
                output.append("  " + " | ".join(values))
                remaining -= 1
        if remaining == 3:
            output.append("No se encontraron registros para mostrar.")
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Vista previa remota",
                "message": Markup("<pre style='white-space:pre-wrap; margin:0'>%s</pre>")
                % escape("\n".join(output)),
                "type": "info",
                "sticky": True,
            },
        }

    def _check_required_fields_mapped(self):
        """Avisa antes de ejecutar si falta mapear un campo obligatorio del destino."""
        self.ensure_one()
        if self.field_map_analyzed and not self.field_map_ids.filtered("migrate"):
            raise UserError(
                "No hay campos seleccionados para migrar. Marcá al menos un campo o volvé a analizar el mapeo."
            )
        missing = self.field_map_ids.filtered(
            lambda line: line.is_required and not line.migrate
        )
        if missing:
            detail = "\n".join(
                f"- {line.model_label or line.model_name}: {line.field_label or line.source_field}"
                for line in missing[:15]
            )
            raise UserError(
                "Hay campos obligatorios en el Odoo destino que quedaron sin migrar.\n"
                "La migración fallaría al crear los registros:\n\n" + detail
            )

    # --- Reutilización y retención de metadatos (SaaS) ---

    def action_reuse_previous_field_map(self):
        """Copia el mapeo de la última migración analizada de la misma cuenta."""
        self.ensure_one()
        previous = self.search(
            [
                ("account_id", "=", self.account_id.id),
                ("id", "!=", self.id),
                ("field_map_ids", "!=", False),
            ],
            order="create_date desc",
            limit=1,
        )
        if not previous:
            raise UserError(
                "No hay una migración anterior con mapeo analizado para esta cuenta.\n"
                "Usá 'Analizar campos' para generarlo."
            )

        self.field_map_ids.unlink()
        self.env["sce.migration.field.map"].create(
            [
                {
                    "run_id": self.id,
                    "model_name": line.model_name,
                    "model_label": line.model_label,
                    "source_field": line.source_field,
                    "target_field": line.target_field,
                    "field_label": line.field_label,
                    "field_type": line.field_type,
                    "relation_model": line.relation_model,
                    "compatibility": line.compatibility,
                    "is_required": line.is_required,
                    "migrate": line.migrate,
                    "sequence": line.sequence,
                }
                for line in previous.field_map_ids
            ]
        )
        self.field_map_analyzed = True
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Mapeo reutilizado",
                "message": f"Se copiaron {len(previous.field_map_ids)} campos desde «{previous.name}».",
                "type": "success",
                "sticky": False,
            },
        }

    @api.model
    def cron_cleanup_migration_field_maps(self):
        """Purga el mapeo de migraciones terminadas.

        Son metadatos de esquema regenerables con 'Analizar campos': borrarlos no
        pierde información del cliente y evita que la base de SCE crezca sin límite.
        """
        days = int(
            self.env["ir.config_parameter"].sudo().get_param("sce.migration.field_map_retention_days", 30)
        )
        deadline = fields.Datetime.now() - timedelta(days=max(1, days))
        stale_runs = self.search(
            [
                ("state", "in", ("done", "failed")),
                ("finished_at", "!=", False),
                ("finished_at", "<=", deadline),
                ("field_map_ids", "!=", False),
            ]
        )
        removed = 0
        for run in stale_runs:
            removed += len(run.field_map_ids)
            run.field_map_ids.unlink()
        if removed:
            _logger.info("Migración: se purgaron %s líneas de mapeo de %s corridas", removed, len(stale_runs))
        return removed
