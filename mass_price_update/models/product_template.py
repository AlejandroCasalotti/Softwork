# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def action_mass_supplier_price_update(self):
        """Abre el wizard para actualización masiva"""
        return {
            'name': _('Actualizar Precio Proveedor Masivo'),
            'type': 'ir.actions.act_window',
            'res_model': 'mass.supplier.price.update',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_tmpl_ids': self.ids,
            }
        }

class MassSupplierPriceUpdate(models.TransientModel):
    _name = 'mass.supplier.price.update'
    _description = 'Actualización Masiva Precio Proveedor'

    product_tmpl_ids = fields.Many2many(
        'product.template', 
        'mass_supplier_price_template_rel19', 
        'wizard_id', 'template_id', 
        string='Plantillas de Producto'
    )
    
    update_type = fields.Selection([
        ('fixed', 'Valor Fijo'),
        ('percentage', 'Porcentaje'),
        ('percentage_increase', 'Incremento %'),
        ('percentage_decrease', 'Decremento %'),
    ], string='Tipo de Actualización', default='fixed', required=True)
    
    new_price = fields.Monetary('Nuevo Precio', required=True, currency_field='currency_id')
    percentage = fields.Float('Porcentaje (%)')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    
    apply_on_variants = fields.Boolean('Aplicar a todas las variantes', default=True)
    update_all_variants = fields.Boolean(
        'Actualizar TODAS las variantes (incluso sin precio)', 
        default=False
    )
    dry_run = fields.Boolean('Vista previa (no aplicar)', default=False)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('active_model') == 'product.template':
            res['product_tmpl_ids'] = [(6, 0, self.env.context.get('active_ids', []))]
        return res

    def action_apply_price_update(self):
        """Aplica la actualización de precios"""
        self.ensure_one()
        
        if self.dry_run:
            return self._preview_update()
            
        products = self._get_products_to_update()
        
        if not products:
            raise UserError(_('No hay productos para actualizar.'))
        
        updated = 0
        errors = []
        
        for product in products:
            try:
                old_price = product.standard_price
                new_price = self._calculate_new_price(product.standard_price)
                
                product.with_context({
                    'no_variant_tracking': True,
                    'skip_grace_period': True
                }).standard_price = new_price
                updated += 1
                
            except Exception as e:
                errors.append(f"{product.name}: {str(e)}")
        
        return self._show_result(updated, errors)

    def _preview_update(self):
        """Muestra vista previa de la actualización"""
        products = self._get_products_to_update()
        preview_lines = []
        
        for product in products[:20]:  # Solo primeros 20
            old_price = product.standard_price
            new_price = self._calculate_new_price(old_price)
            preview_lines.append({
                'name': product.name,
                'old_price': old_price,
                'new_price': new_price,
                'difference': new_price - old_price
            })
        
        return {
            'name': _('Vista Previa - Actualización Precios'),
            'type': 'ir.actions.act_window',
            'res_model': 'mass.price.preview',
            'view_mode': 'tree',
            'target': 'new',
            'context': {'default_lines': preview_lines}
        }

    def _get_products_to_update(self):
        """Obtiene los productos a actualizar"""
        products = self.env['product.product']
        
        for template in self.product_tmpl_ids:
            if self.apply_on_variants:
                variants = template.product_variant_ids
                if not self.update_all_variants:
                    variants = variants.filtered(lambda p: p.standard_price > 0)
                products |= variants
            else:
                main_variant = template.product_variant_id
                if main_variant:
                    products |= main_variant
        
        return products

    def _calculate_new_price(self, old_price):
        """Calcula el nuevo precio según el tipo de actualización"""
        if self.update_type == 'fixed':
            return self.new_price
        elif self.update_type == 'percentage':
            return old_price * (self.percentage / 100)
        elif self.update_type == 'percentage_increase':
            return old_price * (1 + self.percentage / 100)
        elif self.update_type == 'percentage_decrease':
            return old_price * (1 - self.percentage / 100)
        raise UserError(_('Tipo de actualización no válido'))

    def _show_result(self, updated, errors):
        """Muestra resultado de la operación"""
        message = f'✅ Actualizados <strong>{updated}</strong> productos correctamente.'
        if errors:
            message += f'<br>❌ Errores: <strong>{len(errors)}</strong> productos no actualizados.'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Actualización Completada'),
                'message': message,
                'type': 'success' if not errors else 'warning',
                'sticky': True,
            }
        }