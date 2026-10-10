# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.exceptions import UserError


class SceMlTestUserWizard(models.TransientModel):
    _name = "sce.ml.test.user.wizard"
    _description = "Usuarios de prueba Mercado Libre"

    account_id = fields.Many2one(
        "sce.account",
        string="Cuenta Mercado Libre Sandbox",
        required=True,
        domain="[('provider_type', '=', 'mercadolibre'), ('mode', '=', 'sandbox'), ('state', '=', 'connected')]",
    )
    site_id = fields.Char(string="Site ID", default="MLA", required=True)
    quantity = fields.Integer(string="Cantidad", default=1, required=True)
    description_prefix = fields.Char(string="Prefijo descriptivo", default="SCE Test")
    result_line_ids = fields.One2many("sce.ml.test.user.result", "wizard_id", string="Usuarios creados")

    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        if self.env.context.get("default_account_id"):
            values["account_id"] = self.env.context["default_account_id"]
        return values

    def action_create_users(self):
        self.ensure_one()
        if self.account_id.mode != "sandbox":
            raise UserError("Esta herramienta solo funciona con cuentas Mercado Libre Sandbox.")
        if not 1 <= self.quantity <= 10:
            raise UserError("La cantidad debe estar entre 1 y 10 usuarios por operación.")
        provider = self.env["sce.provider.factory"].get_provider(self.account_id)
        self.result_line_ids.unlink()
        values = []
        for index in range(self.quantity):
            result = provider.create_test_user(
                site_id=self.site_id.strip().upper(),
                description=f"{self.description_prefix or 'SCE Test'} {index + 1}",
            )
            values.append((0, 0, {
                "external_id": str(result.get("id") or ""),
                "nickname": result.get("nickname") or "",
                "email": result.get("email") or "",
                "password": result.get("password") or "",
                "site_status": result.get("site_status") or "",
                "status": "Creado",
            }))
        self.write({"result_line_ids": values})
        return {
            "type": "ir.actions.act_window",
            "name": "Usuarios de prueba Mercado Libre",
            "res_model": self._name,
            "view_mode": "form",
            "views": [(False, "form")],
            "res_id": self.id,
            "target": "current",
        }


class SceMlTestUserResult(models.TransientModel):
    _name = "sce.ml.test.user.result"
    _description = "Resultado de usuario de prueba Mercado Libre"
    _order = "id desc"

    wizard_id = fields.Many2one("sce.ml.test.user.wizard", required=True, ondelete="cascade")
    external_id = fields.Char(string="ID externo", readonly=True)
    nickname = fields.Char(string="Nickname", readonly=True)
    email = fields.Char(string="Email", readonly=True)
    password = fields.Char(string="Password", readonly=True)
    site_status = fields.Char(string="Site status", readonly=True)
    status = fields.Char(string="Estado", readonly=True)
