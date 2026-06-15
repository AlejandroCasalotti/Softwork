# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PaymentMulti(models.Model):
    _name = "payment.multi"
    _description = "Multi Pago"
    _order = "payment_date desc, id desc"

    name = fields.Char(string="N° Recibo", required=True, default="/", copy=False)
    partner_id = fields.Many2one("res.partner", string="Proveedor/Cliente", required=True)
    payment_date = fields.Date(string="Fecha", required=True, default=fields.Date.context_today)

    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )

    payment_type = fields.Selection(
        [("inbound", "Entrada"), ("outbound", "Salida")],
        string="Tipo de pago",
        required=True,
    )

    payment_ids = fields.Many2many(
        "account.payment",
        "payment_multi_payment_rel",
        "multi_id",
        "payment_id",
        string="Pagos origen",
        readonly=True,
    )

    line_ids = fields.One2many("payment.multi.line", "multi_id", string="Detalle", copy=False)

    total_amount = fields.Monetary(string="TOTAL PAGADO", currency_field="currency_id", compute="_compute_total", store=True)

    state = fields.Selection(
        [("draft", "Borrador"), ("posted", "Contabilizado")],
        default="draft",
        required=True,
    )

    @api.depends("line_ids.amount", "currency_id")
    def _compute_total(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped("amount"))

    @api.model
    def _get_payment_type_from_payment(self, payment):
        # account.payment uses payment_type: inbound/outbound
        return payment.payment_type

    @api.model
    def _create_from_payments(self, payments):
        payments = payments.sorted(lambda p: p.id)
        if not payments:
            raise UserError(_("No hay pagos seleccionados."))

        partner = payments[0].partner_id
        if not partner:
            raise UserError(_("Todos los pagos deben tener un Proveedor/Cliente.") )

        payment_type = self._get_payment_type_from_payment(payments[0])
        currency = payments[0].currency_id or self.env.company.currency_id
        company = payments[0].company_id or self.env.company

        for p in payments:
            if not p.partner_id or p.partner_id != partner:
                raise UserError(_("Todos los pagos deben ser del mismo Proveedor/Cliente."))
            if self._get_payment_type_from_payment(p) != payment_type:
                raise UserError(_("Todos los pagos deben ser del mismo Tipo de pago."))
            if (p.currency_id or self.env.company.currency_id) != currency:
                raise UserError(_("Todos los pagos deben tener la misma moneda para crear el Multi Pago."))
            if (p.company_id or self.env.company) != company:
                raise UserError(_("Todos los pagos deben pertenecer a la misma compañía."))
            # Se permite `journal_id` (diario/método de pago) distinto entre pagos.


        multi = self.create(
            {
                "name": self.env["ir.sequence"].next_by_code("payment.multi") or "/",
                "partner_id": partner.id,
                "payment_date": fields.Date.context_today(self),
                "currency_id": currency.id,
                "company_id": company.id,
                "payment_type": payment_type,
            }
        )

        # Cargar líneas
        for p in payments:
            journal_name = p.journal_id.display_name if p.journal_id else ""
            memo = p.ref or p.communication or p.name or ""

            self.env["payment.multi.line"].create(
                {
                    "multi_id": multi.id,
                    "origin_payment_id": p.id,
                    "payment_date": p.payment_date,
                    "journal_id": p.journal_id.id if p.journal_id else False,
                    "memo": memo,
                    "amount": p.amount,
                    "currency_id": multi.currency_id.id,

                }
            )

        multi.payment_ids = [(6, 0, payments.ids)]
        return multi

    def action_print_receipt(self):
        self.ensure_one()
        return self.env.ref("payment_multi_lots_odoo19.action_report_payment_multi_receipt").report_action(self)


class PaymentMultiLine(models.Model):
    _name = "payment.multi.line"
    _description = "Detalle Multi Pago"
    _order = "payment_date asc, id asc"

    multi_id = fields.Many2one("payment.multi", string="Multi Pago", required=True, ondelete="cascade")
    origin_payment_id = fields.Many2one("account.payment", string="Pago origen", readonly=True)

    payment_date = fields.Date(string="Fecha")

    journal_id = fields.Many2one("account.journal", string="Diario (Metodo de pago)")
    memo = fields.Char(string="Descripción (Memo)")

    currency_id = fields.Many2one("res.currency", related="multi_id.currency_id", store=True, readonly=True)

    amount = fields.Monetary(string="Importe", currency_field="currency_id")