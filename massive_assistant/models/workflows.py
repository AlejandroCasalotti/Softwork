"""Reviewed business transitions, checked and executed in one Odoo transaction."""
import hashlib
import json
from odoo import api, models, release
from odoo.exceptions import AccessError, UserError


class MassiveWorkflows(models.AbstractModel):
    _inherit = 'massive.assistant.gateway'

    def _workflow_record(self, action, company_id, record_id, lock=False):
        if release.version_info[0] != 19:
            raise UserError('Estas operaciones requieren el bridge validado para Odoo 19.')
        if not self.env.user.has_group('massive_assistant.group_massive_assistant_user'):
            raise AccessError('Usuario no autorizado para Massive Connector.')
        if action not in ('sale_confirm', 'delivery_reserve', 'delivery_validate'):
            raise UserError('Operación no habilitada.')
        if any(type(v) is not int or v <= 0 for v in (company_id, record_id)):
            raise UserError('Identificadores inválidos.')
        if company_id not in self.env.user.company_ids.ids:
            raise AccessError('Empresa no autorizada.')
        model = 'sale.order' if action == 'sale_confirm' else 'stock.picking'
        if model not in self.env:
            raise UserError('Instalá Ventas e Inventario según la operación solicitada.')
        # Drop caller flags that could bypass sanity checks or backorder handling.
        records = self.env[model].with_context({
            'allowed_company_ids': [company_id], 'lang': self.env.user.lang,
            'tz': self.env.user.tz, 'send_email': False,
        })
        record = records.search([('id', '=', record_id), ('company_id', '=', company_id)], limit=1)
        if not record:
            raise AccessError('Documento no disponible para esta empresa.')
        record.check_access('write')
        if lock:
            # IDs are already checked through ACL/rules. SQL only locks, never reads ERP data.
            if model == 'sale.order':
                self.env.cr.execute('SELECT id FROM sale_order WHERE id = %s FOR UPDATE NOWAIT', [record_id])
                self.env.cr.execute('SELECT id FROM sale_order_line WHERE order_id = %s ORDER BY id FOR UPDATE NOWAIT', [record_id])
            else:
                self.env.cr.execute('SELECT id FROM stock_picking WHERE id = %s FOR UPDATE NOWAIT', [record_id])
                self.env.cr.execute('SELECT id FROM stock_move WHERE picking_id = %s ORDER BY id FOR UPDATE NOWAIT', [record_id])
                self.env.cr.execute('SELECT id FROM stock_move_line WHERE picking_id = %s ORDER BY id FOR UPDATE NOWAIT', [record_id])
            self.env.invalidate_all()
            record = records.search([('id', '=', record_id), ('company_id', '=', company_id)], limit=1)
            if not record:
                raise AccessError('El documento ya no está disponible.')
            record.check_access('write')
        return record

    def _workflow_snapshot(self, action, record):
        if action == 'sale_confirm':
            if record.state not in ('draft', 'sent'):
                raise UserError('Solo se confirma una cotización en borrador o enviada.')
            lines = record.order_line.sorted('id')
            if not lines or len(lines) > 100:
                raise UserError('La cotización debe contener entre una y cien líneas.')
            lines.check_access('read')
            data = record.read(['name', 'state', 'company_id', 'partner_id', 'partner_shipping_id',
                'partner_invoice_id', 'pricelist_id', 'currency_id', 'amount_total', 'amount_tax',
                'payment_term_id', 'fiscal_position_id', 'write_date'])[0]
            detail = lines.read(['product_id', 'name', 'product_uom_qty', 'product_uom_id',
                'price_unit', 'discount', 'tax_ids', 'display_type', 'write_date'])
            rows = [{'code': str(l['id']), 'name': l['name'], 'quantity': l['product_uom_qty'],
                     'price': l['price_unit'], 'scope': 'Cotización ' + record.name} for l in detail]
            extra = {'customer': record.partner_id.display_name, 'currency': record.currency_id.name,
                     'notice': 'Confirma el pedido por un total de %s %s, impuestos incluidos. Puede generar entregas, reservas y automatizaciones configuradas en Odoo. No crea facturas ni registra pagos.' % (record.amount_total, record.currency_id.name)}
        else:
            if record.state in ('draft', 'done', 'cancel') or record.picking_type_id.code != 'outgoing':
                raise UserError('Elegí una entrega a cliente confirmada y pendiente, no una recepción o transferencia interna.')
            moves = record.move_ids.filtered(lambda m: m.state not in ('done', 'cancel')).sorted('id')
            if not moves or len(moves) > 100 or len(record.move_line_ids) > 500:
                raise UserError('La entrega está vacía o supera el tamaño permitido.')
            moves.check_access('read'); record.move_line_ids.check_access('read')
            if action == 'delivery_validate':
                if record.state != 'assigned' or any(m.state != 'assigned' or m.product_uom.compare(m.quantity, m.product_uom_qty) != 0 for m in moves):
                    raise UserError('Falta reservar toda la cantidad de esta entrega. Reservá disponibilidad primero. Las entregas parciales se revisan en Odoo.')
                if any(m.product_uom_qty <= 0 for m in moves):
                    raise UserError('Revisá las cantidades de la entrega en Odoo.')
                # Native checks verify required lots/serials without skipping anything.
                record._sanity_check()
            data = record.read(['name', 'state', 'partner_id', 'company_id', 'location_id',
                'location_dest_id', 'picking_type_id', 'scheduled_date', 'write_date'])[0]
            detail = moves.read(['product_id', 'product_uom_qty', 'product_uom', 'quantity',
                'picked', 'state', 'location_id', 'location_dest_id', 'write_date'])
            data['move_lines'] = record.move_line_ids.sorted('id').read([
                'product_id', 'quantity', 'product_uom_id', 'lot_id', 'lot_name', 'package_id',
                'result_package_id', 'owner_id', 'location_id', 'location_dest_id', 'picked', 'write_date'])
            rows = [{'code': str(m.id), 'name': m.product_id.display_name,
                     'quantity': m.product_uom_qty, 'reserved': m.quantity,
                     'scope': m.product_uom.display_name} for m in moves]
            extra = {'notice': ('Reserva stock disponible para esta entrega; puede quedar parcialmente reservada. No valida ni mueve stock físico.' if action == 'delivery_reserve' else
                'Valida la entrega COMPLETA con las cantidades y lotes ya reservados. Descuenta stock y puede generar valoración contable y notificaciones configuradas en Odoo. Confirmá únicamente si representa la entrega física real. No factura ni registra pagos.')}
        snapshot = {'document': data, 'lines': detail, 'action': action}
        token = hashlib.sha256(json.dumps(snapshot, sort_keys=True, default=str).encode()).hexdigest()
        return {'kind': action, 'company': record.company_id.display_name,
                'document': record.name, 'rows': rows, 'errors': [], **extra}, token

    @api.model
    def workflow_preview(self, action, company_id, record_id):
        try:
            record = self._workflow_record(action, company_id, record_id)
            preview, token = self._workflow_snapshot(action, record)
            return {'preview': preview, 'token': token}
        except (UserError, AccessError) as error:
            return {'error': str(error)[:1000], 'rejected': True}

    @api.model
    def workflow_execute(self, action, company_id, record_id, expected_token):
        try:
            with self.env.cr.savepoint():
                return self._workflow_execute(action, company_id, record_id, expected_token)
        except (UserError, AccessError) as error:
            # The savepoint rolls back even a native wizard's preliminary changes.
            return {'error': str(error)[:1000], 'rejected': True}

    def _workflow_execute(self, action, company_id, record_id, expected_token):
        record = self._workflow_record(action, company_id, record_id, lock=True)
        _, token = self._workflow_snapshot(action, record)
        if not isinstance(expected_token, str) or token != expected_token:
            raise UserError('El documento cambió desde la propuesta. Prepará otra revisión.')
        if action == 'sale_confirm':
            record.action_confirm()
            if record.state != 'sale':
                raise UserError('Odoo no confirmó el pedido; se revierte la operación.')
        elif action == 'delivery_reserve':
            record.action_assign()
        else:
            record.move_ids.filtered(lambda m: m.state not in ('done', 'cancel')).write({'picked': True})
            record.button_validate()
            if record.state != 'done':
                # An installed module can return an extra wizard. Roll back all changes.
                raise UserError('Odoo requiere una revisión adicional. Completala desde la entrega en Odoo.')
        return {'id': record.id, 'state': record.state, 'action': action, 'complete': True}
