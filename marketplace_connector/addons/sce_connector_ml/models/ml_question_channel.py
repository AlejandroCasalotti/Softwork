# -*- coding: utf-8 -*-
import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


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

    _sql_constraints = [
        (
            "uniq_account_question",
            "UNIQUE(account_id, ml_question_id)",
            "Ya existe un seguimiento para esta pregunta de Mercado Libre.",
        ),
    ]

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
            exists = self.sudo().search_count(
                [("account_id", "=", account.id), ("ml_question_id", "=", question_id)]
            )
            if exists:
                continue
            self._create_channel_for_question(account, question)

    def _create_channel_for_question(self, account, question):
        item_id = str((question.get("item_id") or "")).strip()
        item_title = ""
        item = question.get("item") if isinstance(question.get("item"), dict) else {}
        if item:
            item_title = item.get("title") or ""
        if not item_title and item_id:
            try:
                item_data = self.env["sce.provider.factory"].get_provider(account).get_item(item_id) or {}
                item_title = (item_data.get("item") or {}).get("title") or item_id
            except Exception:
                item_title = item_id
        buyer_nickname = ""
        from_data = question.get("from") if isinstance(question.get("from"), dict) else {}
        buyer_nickname = from_data.get("nickname") or str(from_data.get("id") or "comprador")
        question_text = question.get("text") or ""
        question_date = question.get("date_created") or ""

        channel_name = f"ML: {item_title or item_id} - {buyer_nickname}"[:120]
        remote_channel_id = account.create_remote_discuss_channel(channel_name)

        body = (
            "<p>🛒 <b>Pregunta de Mercado Libre</b></p>"
            f"<p>Publicación: {item_title or '-'} ({item_id})<br/>"
            f"Comprador: {buyer_nickname}<br/>"
            f"Fecha: {question_date}</p>"
            f"<p>\"{question_text}\"</p>"
            "<p>💬 Respondé este mensaje en este mismo canal.<br/>"
            "Tu respuesta se enviará automáticamente a Mercado Libre.</p>"
        )
        last_message_id = account.post_remote_discuss_message(remote_channel_id, body) or 0

        self.sudo().create(
            {
                "account_id": account.id,
                "ml_question_id": str(question.get("id")),
                "item_id": item_id,
                "remote_channel_id": remote_channel_id,
                "last_message_id": last_message_id,
                "state": "pending",
            }
        )

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
            return

        provider = self._get_provider(account)
        provider.answer_question(self.ml_question_id, reply_text)

        confirmation = (
            "<p>✅ Respuesta enviada a Mercado Libre correctamente.<br/>"
            "Este canal se archivará automáticamente.</p>"
        )
        account.post_remote_discuss_message(self.remote_channel_id, confirmation)
        account.archive_remote_discuss_channel(self.remote_channel_id)

        self.write(
            {
                "state": "answered",
                "answered_date": fields.Datetime.now(),
                "last_message_id": reply.get("id") or self.last_message_id,
            }
        )

    @staticmethod
    def _plain_text(html_body):
        import re

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
