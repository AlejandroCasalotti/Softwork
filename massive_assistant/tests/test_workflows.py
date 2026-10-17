"""Odoo 19 acceptance tests; run on a test database with sale_stock installed."""
import unittest
from odoo import release
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class WorkflowTests(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if release.version_info[0] != 19 or 'sale.order' not in cls.env or 'stock.picking' not in cls.env or 'warehouse_id' not in cls.env['sale.order']._fields:
            raise unittest.SkipTest('Requires Odoo 19 and sale_stock.')
        cls.gateway = cls.env['massive.assistant.gateway']
        cls.partner = cls.env['res.partner'].create({'name': 'Massive workflow test customer'})
        cls.product = cls.env['product.product'].create({'name': 'Massive workflow test product', 'type': 'consu', 'is_storable': True, 'list_price': 10})
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.env.company.id)], limit=1)
        if not cls.warehouse:
            raise unittest.SkipTest('Requires a warehouse in the test company.')

    def order(self):
        return self.env['sale.order'].create({'partner_id': self.partner.id, 'company_id': self.env.company.id,
            'warehouse_id': self.warehouse.id, 'order_line': [(0, 0, {'product_id': self.product.id,
                'name': self.product.name, 'product_uom_qty': 2, 'price_unit': 10})]})

    def test_confirm_rejects_stale_snapshot_then_confirms_and_cannot_replay(self):
        order = self.order()
        preview = self.gateway.workflow_preview('sale_confirm', self.env.company.id, order.id)
        self.assertIn('token', preview)
        order.order_line.price_unit = 12
        rejected = self.gateway.workflow_execute('sale_confirm', self.env.company.id, order.id, preview['token'])
        self.assertTrue(rejected['rejected']); self.assertEqual(order.state, 'draft')
        preview = self.gateway.workflow_preview('sale_confirm', self.env.company.id, order.id)
        result = self.gateway.workflow_execute('sale_confirm', self.env.company.id, order.id, preview['token'])
        self.assertEqual(result['state'], 'sale'); self.assertEqual(order.state, 'sale')
        self.assertTrue(self.gateway.workflow_execute('sale_confirm', self.env.company.id, order.id, preview['token'])['rejected'])

    def test_reserve_then_validate_only_when_full_stock_available(self):
        order = self.order(); order.action_confirm()
        picking = order.picking_ids.filtered(lambda p: p.picking_type_id.code == 'outgoing')
        self.assertEqual(len(picking), 1)
        preview = self.gateway.workflow_preview('delivery_validate', self.env.company.id, picking.id)
        self.assertTrue(preview['rejected']); self.assertNotEqual(picking.state, 'done')
        self.env['stock.quant']._update_available_quantity(self.product, self.warehouse.lot_stock_id, 2)
        preview = self.gateway.workflow_preview('delivery_reserve', self.env.company.id, picking.id)
        result = self.gateway.workflow_execute('delivery_reserve', self.env.company.id, picking.id, preview['token'])
        self.assertEqual(result['state'], 'assigned')
        preview = self.gateway.workflow_preview('delivery_validate', self.env.company.id, picking.id)
        result = self.gateway.workflow_execute('delivery_validate', self.env.company.id, picking.id, preview['token'])
        self.assertEqual(result['state'], 'done')
        self.assertEqual(picking.state, 'done')

    def test_extra_wizard_rolls_back_preliminary_mutations(self):
        from unittest.mock import patch
        order = self.order(); order.action_confirm()
        picking = order.picking_ids.filtered(lambda p: p.picking_type_id.code == 'outgoing')
        self.env['stock.quant']._update_available_quantity(self.product, self.warehouse.lot_stock_id, 2)
        picking.action_assign()
        preview = self.gateway.workflow_preview('delivery_validate', self.env.company.id, picking.id)
        picked_before = picking.move_ids.picked
        def wizard(record):
            record.write({'origin': 'must roll back'})
            return {'type': 'ir.actions.act_window'}
        original = picking.origin
        with patch.object(type(picking), 'button_validate', wizard):
            result = self.gateway.workflow_execute('delivery_validate', self.env.company.id, picking.id, preview['token'])
        self.assertTrue(result['rejected']); picking.invalidate_recordset()
        self.assertEqual(picking.origin, original); self.assertEqual(picking.move_ids.picked, picked_before)
        self.assertNotEqual(picking.state, 'done')

    def test_read_only_user_and_foreign_company_rejected(self):
        order = self.order()
        user = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'Massive read only', 'login': 'massive-workflow-read-only',
            'group_ids': [(6, 0, [self.env.ref('massive_assistant.group_massive_assistant_user').id])]})
        result = self.gateway.with_user(user).workflow_preview('sale_confirm', self.env.company.id, order.id)
        self.assertTrue(result['rejected'])
        company = self.env['res.company'].create({'name': 'Massive other test company'})
        result = self.gateway.with_user(user).workflow_preview('sale_confirm', company.id, order.id)
        self.assertTrue(result['rejected']); self.assertEqual(order.state, 'draft')
