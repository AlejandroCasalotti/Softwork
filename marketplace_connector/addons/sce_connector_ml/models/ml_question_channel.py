# -*- coding: utf-8 -*-
import logging
import re
from datetime import datetime, timedelta

from markupsafe import Markup, escape

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


def _format_ml_date(raw):
    """Convierte la fecha ISO8601 de ML (con nanosegundos) a dd/mm/YYYY HH:MM."""
    text = str(raw or "").strip()
    match = re.match(
        r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(\.\d+)?([+-]\d{2}:\d{2}|Z)?$", text
    )
    if not match:
        return text
    base, frac, tz = match.groups()
    frac = frac[:7] if frac else ""  # punto + hasta 6 dígitos (microsegundos)
    tz = "+00:00" if tz == "Z" else (tz or "")
    try:
        dt = datetime.fromisoformat(base + frac + tz)
        return dt.strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return text


class MlQuestionChannel(models.Model):
    """Seguimiento liviano de preguntas de Mercado Libre reenviadas al Discuss del cliente.

    No se almacena el contenido de la pregunta/respuesta: solo lo indispensable para
    correlacionar el canal remoto de Discuss con la pregunta de Mercado Libre.
    """

    _name = "ml.question.channel"
    _description = "Puente Pregunta ML <-> Discuss remoto"
    _order = "create_date desc"

    account_id = fields.Many2one("sce.account", required=True, ondelete="cascade", index=True)
    ml_question_id = fields.Char(string="ID Pregunta ML", required=True, index=True)
    item_id = fields.Char(string="ID Publicación ML")
    remote_channel_id = fields.Integer(string="ID Canal Discuss remoto", required=True)
    last_message_id = fields.Integer(string="Último mensaje remoto visto", default=0)
    state = fields.Selection(
        [("pending", "Pendiente"), ("answered", "Respondida")],
        default="pending",
        required=True,
        index=True,
    )
    answered_date = fields.Datetime(string="Fecha de respuesta")

    @api.constrains("account_id", "ml_question_id")
    def _check_unique_account_question(self):
        for record in self:
            if not record.account_id or not record.ml_question_id:
                continue
            duplicates = self.search_count(
                [
                    ("account_id", "=", record.account_id.id),
                    ("ml_question_id", "=", record.ml_question_id),
                    ("id", "!=", record.id),
                ]
            )
            if duplicates:
                raise ValidationError(
                    "Ya existe un seguimiento para esta pregunta de Mercado Libre."
                )

    @api.model
    def _get_provider(self, account):
        return self.env["sce.provider.factory"].get_provider(account)

    @api.model
    def cron_sync_ml_questions(self):
        """Busca preguntas nuevas en ML y crea el canal de Discuss remoto correspondiente."""
        accounts = self.env["sce.account"].sudo().search(
            [
                ("provider_type", "=", "mercadolibre"),
                ("state", "=", "connected"),
                ("sync_ml_questions", "=", True),
            ]
        )
        for account in accounts:
            try:
                self._sync_account_questions(account)
            except Exception:
                _logger.exception("Error sincronizando preguntas ML para la cuenta %s", account.display_name)

    def _sync_account_questions(self, account):
        provider = self._get_provider(account)
        response = provider.get_questions(status="UNANSWERED") or {}
        questions = response.get("items") or []
        for question in questions:
            question_id = str(question.get("id") or "").strip()
            if not question_id:
                continue
            existing = self.sudo().search(
                [("account_id", "=", account.id), ("ml_question_id", "=", question_id)],
                limit=1,
            )
            if existing:
                if not existing.last_message_id:
                    try:
                        existing._post_question_body(question)
                    except Exception:
                        _logger.exception(
                            "Error recuperando el mensaje de la pregunta ML %s (cuenta %s)",
                            question_id,
                            account.display_name,
                        )
                continue
            try:
                self._create_channel_for_question(account, question)
            except Exception:
                _logger.exception(
                    "Error creando canal Discuss para la pregunta ML %s (cuenta %s)",
                    question_id,
                    account.display_name,
                )

    def _create_channel_for_question(self, account, question):
        item_id, item_title, buyer_nickname = self._get_question_details(account, question)
        question_id = str(question.get("id"))

        channel_name = f"ML: {item_title or item_id} - {buyer_nickname}"[:120]
        remote_channel_id = account.create_remote_discuss_channel(channel_name)

        # Se guarda apenas se crea el canal remoto (efecto ya irreversible) para
        # que una falla posterior no dispare la creación de un canal duplicado
        # en el próximo ciclo del cron.
        record = self.sudo().create(
            {
                "account_id": account.id,
                "ml_question_id": question_id,
                "item_id": item_id,
                "remote_channel_id": remote_channel_id,
                "last_message_id": 0,
                "state": "pending",
            }
        )
        self.env.cr.commit()
        record._post_question_body(question)

    def _get_question_details(self, account, question):
        item_id = str(question.get("item_id") or "").strip()
        item = question.get("item") if isinstance(question.get("item"), dict) else {}
        item_title = item.get("title") or ""
        if not item_title and item_id:
            try:
                item_data = self._get_provider(account).get_item(item_id) or {}
                item_title = (item_data.get("item") or {}).get("title") or item_id
            except Exception:
                item_title = item_id
        from_data = question.get("from") if isinstance(question.get("from"), dict) else {}
        buyer_nickname = from_data.get("nickname") or str(from_data.get("id") or "comprador")
        return item_id, item_title, buyer_nickname

    def _post_question_body(self, question):
        self.ensure_one()
        item_id, item_title, buyer_nickname = self._get_question_details(self.account_id, question)
        question_text = question.get("text") or ""
        question_date = _format_ml_date(question.get("date_created"))
        body = Markup(
            "<p>🛒 <b>Pregunta de Mercado Libre</b></p>"
            "<p>Publicación: {item_title} ({item_id})<br/>"
            "Comprador: {buyer_nickname}<br/>"
            "Fecha: {question_date}</p>"
            "<p>\"{question_text}\"</p>"
            "<p>💬 Respondé este mensaje en este mismo canal.<br/>"
            "Tu respuesta se enviará automáticamente a Mercado Libre.</p>"
        ).format(
            item_title=escape(item_title or "-"),
            item_id=escape(item_id),
            buyer_nickname=escape(buyer_nickname),
            question_date=escape(question_date),
            question_text=escape(question_text),
        )
        last_message_id = self.account_id.post_remote_discuss_message(self.remote_channel_id, body) or 0
        self.last_message_id = last_message_id
        self.env.cr.commit()

    @api.model
    def cron_check_ml_question_replies(self):
        """Revisa los canales pendientes y reenvía la primera respuesta del vendedor a Mercado Libre."""
        pending = self.sudo().search([("state", "=", "pending")])
        for record in pending:
            try:
                record._check_reply()
            except Exception:
                _logger.exception(
                    "Error revisando respuestas del canal Discuss %s (cuenta %s)",
                    record.remote_channel_id,
                    record.account_id.display_name,
                )

    def _check_reply(self):
        self.ensure_one()
        account = self.account_id
        messages = account.fetch_remote_discuss_messages(self.remote_channel_id, after_id=self.last_message_id)
        if not messages:
            return
        messages = sorted(messages, key=lambda m: m.get("id") or 0)
        reply = messages[0]
        reply_text = self._plain_text(reply.get("body") or "")
        if not reply_text:
            self.last_message_id = reply.get("id") or self.last_message_id
            self.env.cr.commit()
            return

        provider = self._get_provider(account)
        provider.answer_question(self.ml_question_id, reply_text)

        # La respuesta ya se envió a ML (efecto irreversible): se persiste
        # antes de los pasos best-effort de confirmación/archivado, para no
        # reenviarla si algo falla más adelante.
        self.write(
            {
                "state": "answered",
                "answered_date": fields.Datetime.now(),
                "last_message_id": reply.get("id") or self.last_message_id,
            }
        )
        self.env.cr.commit()

        try:
            confirmation = Markup(
                "<p>✅ Respuesta enviada a Mercado Libre correctamente.<br/>"
                "Este canal se archivará automáticamente.</p>"
            )
            account.post_remote_discuss_message(self.remote_channel_id, confirmation)
            account.archive_remote_discuss_channel(self.remote_channel_id)
        except Exception:
            _logger.exception(
                "Error confirmando/archivando el canal Discuss %s tras responder a ML",
                self.remote_channel_id,
            )

    @staticmethod
    def _plain_text(html_body):
        text = re.sub(r"<[^>]+>", " ", html_body or "")
        return " ".join(text.split()).strip()

    @api.model
    def cron_cleanup_ml_question_channels(self):
        """Elimina canales ya respondidos más allá del período de retención configurado."""
        answered = self.sudo().search([("state", "=", "answered"), ("answered_date", "!=", False)])
        for record in answered:
            retention_days = record.account_id.ml_question_retention_days or 30
            deadline = fields.Datetime.now() - timedelta(days=retention_days)
            if record.answered_date and record.answered_date <= deadline:
                try:
                    record.account_id.unlink_remote_discuss_channel(record.remote_channel_id)
                except Exception:
                    _logger.exception(
                        "Error eliminando canal Discuss remoto %s (cuenta %s)",
                        record.remote_channel_id,
                        record.account_id.display_name,
                    )
                record.unlink()
