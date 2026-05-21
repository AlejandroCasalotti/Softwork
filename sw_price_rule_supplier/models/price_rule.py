# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class PriceRuleSupplier(models.Model):
    _name = 'price.rule.supplier'
    _description = 'Regla de Costo Proveedor'
    _order = 'name'

    name = fields.Char(string='Nombre de Regla', required=True)
    active = fields.Boolean(string='Activa', default=True)
    line_ids = fields.One2many(
        'price.rule.supplier.line', 'rule_id',
        string='Líneas', copy=True
    )

    total_discount = fields.Float(
        string='Total Descuento (%)',
        compute='_compute_total',
        store=True
    )
    total_tariff = fields.Float(
        string='Total Tarifa Extra',
        compute='_compute_total',
        store=True
    )

    @api.depends('line_ids.discount', 'line_ids.tariff_extra')
    def _compute_total(self):
        for rule in self:
            total_disc = total_tariff = 0.0
            for line in rule.line_ids:
                total_disc += line.discount or 0.0
                total_tariff += line.tariff_extra or 0.0
            rule.total_discount = total_disc
            rule.total_tariff = total_tariff

    def _register_hook(self):
        super()._register_hook()
        self._create_menu_and_view()

    def _create_menu_and_view(self):
        """Crea menú y vista heredada automáticamente"""
        # Crear acción
        action = self.env['ir.actions.act_window'].search([
            ('name', '=', 'Reglas de Costo'),
        ], limit=1)

        if not action:
            action = self.env['ir.actions.act_window'].create({
                'name': 'Reglas de Costo',
                'res_model': 'price.rule.supplier',
                'view_mode': 'list,form',
            })
            _logger.info('Acción creada')

        # Crear menú
        menu = self.env['ir.ui.menu'].search([
            ('name', '=', 'Reglas de Costo'),
        ], limit=1)

        if not menu:
            # Buscar menú de configuración de compras
            parent_menu = self.env['ir.ui.menu'].search([
                ('name', '=', 'Configuration'),
                ('parent_path', 'like', '%purchase%'),
            ], limit=1)

            if parent_menu:
                self.env['ir.ui.menu'].create({
                    'name': 'Reglas de Costo',
                    'action': f'ir.actions.act_window,{action.id}',
                    'parent_id': parent_menu.id,
                })
                _logger.info('Menú creado')

        # Crear vista heredada
        view = self.env['ir.ui.view'].search([
            ('name', '=', 'product.supplierinfo.price.rule'),
        ], limit=1)

        if not view:
            # Buscar vista original
            original = self.env['ir.ui.view'].search([
                ('model', '=', 'product.supplierinfo'),
                ('type', '=', 'form'),
                ('inherit_id', '=', False),
            ], limit=1)

            if original:
                self.env['ir.ui.view'].create({
                    'name': 'product.supplierinfo.price.rule',
                    'model': 'product.supplierinfo',
                    'inherit_id': original.id,
                    'arch': '''
                        <xpath expr="//field[@name='price']" position="after">
                            <field name="price_rule_id"/>
                            <field name="net_price" readonly="1"/>
                        </xpath>
                    ''',
                    'active': True,
                })
                _logger.info('Vista heredada creada')

        return True


class PriceRuleSupplierLine(models.Model):
    _name = 'price.rule.supplier.line'
    _description = 'Línea de Regla de Costo'
    _order = 'sequence'

    rule_id = fields.Many2one(
        'price.rule.supplier',
        string='Regla',
        required=True,
        ondelete='cascade'
    )
    sequence = fields.Integer(string='#', default=10)
    description = fields.Char(string='Descripción', required=True)
    discount = fields.Float(string='Descuento %', default=0.0)
    tariff_extra = fields.Float(string='Tarifa Extra', default=0.0)


class ProductSupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    price_rule_id = fields.Many2one(
        'price.rule.supplier',
        string='Regla de Costo'
    )

    net_price = fields.Float(
        string='Precio Neto',
        compute='_compute_net_price',
        digits='Product Price'
    )

    @api.depends('price', 'price_rule_id', 'price_rule_id.line_ids')
    def _compute_net_price(self):
        for record in self:
            if not record.price_rule_id or not record.price_rule_id.line_ids:
                record.net_price = record.price
                continue

            current_price = record.price
            lines = record.price_rule_id.line_ids.sorted(key='sequence')

            for line in lines:
                if line.discount:
                    current_price = current_price - (current_price * line.discount / 100)
                if line.tariff_extra:
                    current_price = current_price + line.tariff_extra

            record.net_price = round(current_price, 2)