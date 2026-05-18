# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero


class IncreasePriceWizard(models.TransientModel):
    _name = 'increase.price.wizard'
    _description = 'Wizard para aumentar precio de proveedores'

    # Campos del wizard
    percentage = fields.Float(
        string='Porcentaje de aumento (%)',
        required=True,
        help='Porcentaje a aumentar. Ejemplo: 10 para aumentar 10%',
        default=0.0,
    )
    
    apply_to_current_price = fields.Boolean(
        string='Aplicar sobre precio actual',
        default=True,
        help='Si está marcado, el aumento se aplica sobre el precio actual. '
             'Si no está marcado, se establece el nuevo precio directamente.',
    )
    
    supplier_info_ids = fields.Many2many(
        'product.supplierinfo',
        string='Productos de proveedores seleccionados',
        readonly=True,
    )
    
    # Campos calculados para previsualización
    items_preview = fields.One2many(
        'increase.price.wizard.line',
        'wizard_id',
        string='Previsualización de cambios',
        readonly=True,
    )

    @api.model
    def default_get(self, fields_list):
        """Sobrescribir para obtener los registros seleccionados."""
        res = super(IncreasePriceWizard, self).default_get(fields_list)
        
        # Obtener los IDs del contexto
        active_ids = self.env.context.get('active_ids', [])
        
        if active_ids:
            res['supplier_info_ids'] = [(6, 0, active_ids)]
            # Crear previsualización
            self._create_preview(active_ids, res)
        
        return res

    def _create_preview(self, supplier_info_ids, res):
        """Crea las líneas de previsualización."""
        # Limpiar líneas anteriores
        res.setdefault('items_preview', [])
        
        supplier_infos = self.env['product.supplierinfo'].browse(supplier_info_ids)
        
        # Guardar para crear las líneas después
        res['_preview_supplier_infos'] = supplier_infos.ids

    @api.onchange('percentage', 'apply_to_current_price')
    def _onchange_percentage(self):
        """Actualiza la previsualización cuando cambia el porcentaje."""
        if self.percentage < 0:
            return {
                'warning': {
                    'title': 'Porcentaje inválido',
                    'message': 'El porcentaje no puede ser negativo.',
                }
            }
        
        self._update_preview()

    def _update_preview(self):
        """Actualiza las líneas de previsualización."""
        self.ensure_one()
        
        # Limpiar líneas existentes
        self.items_preview.unlink()
        
        if not self.supplier_info_ids or self.percentage == 0:
            return
        
        # Crear nuevas líneas de previsualización
        preview_lines = []
        
        for supplier_info in self.supplier_info_ids:
            current_price = supplier_info.price
            
            if self.apply_to_current_price:
                # Calcular nuevo precio con el aumento
                new_price = current_price * (1 + self.percentage / 100)
            else:
                # El porcentaje representa el nuevo precio directamente
                new_price = self.percentage
            
            preview_lines.append((0, 0, {
                'wizard_id': self.id,
                'supplier_info_id': supplier_info.id,
                'product_name': supplier_info.product_id.name,
                'partner_name': supplier_info.name.name,
                'current_price': current_price,
                'new_price': new_price,
            }))
        
        self.items_preview = preview_lines

    def action_apply_increase(self):
        """Aplica el aumento de precio a todos los proveedores seleccionados."""
        self.ensure_one()
        
        if not self.supplier_info_ids:
            raise UserError('No hay productos de proveedores seleccionados.')
        
        if self.percentage < 0:
            raise UserError('El porcentaje no puede ser negativo.')
        
        # Actualizar los precios
        for supplier_info in self.supplier_info_ids:
            current_price = supplier_info.price
            
            if self.apply_to_current_price:
                # Calcular nuevo precio con el aumento
                new_price = current_price * (1 + self.percentage / 100)
            else:
                # El porcentaje representa el nuevo precio directamente
                new_price = self.percentage
            
            supplier_info.write({
                'price': new_price,
            })
        
        # Mostrar mensaje de éxito
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Precios actualizados',
                'message': f'Se ha aplicado el aumento del {self.percentage}% a '
                           f'{len(self.supplier_info_ids)} proveedor(es).',
                'sticky': False,
                'type': 'success',
            }
        }


class IncreasePriceWizardLine(models.TransientModel):
    _name = 'increase.price.wizard.line'
    _description = 'Líneas de previsualización del wizard'

    wizard_id = fields.Many2one(
        'increase.price.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )
    
    supplier_info_id = fields.Many2one(
        'product.supplierinfo',
        string='Supplier Info',
        required=True,
    )
    
    product_name = fields.Char(
        string='Producto',
        required=True,
    )
    
    partner_name = fields.Char(
        string='Proveedor',
        required=True,
    )
    
    current_price = fields.Float(
        string='Precio actual',
        required=True,
        digits='Product Price',
    )
    
    new_price = fields.Float(
        string='Nuevo precio',
        required=True,
        digits='Product Price',
    )
    
    price_difference = fields.Float(
        string='Diferencia',
        compute='_compute_price_difference',
        digits='Product Price',
    )
    
    percentage_change = fields.Float(
        string='% Cambio',
        compute='_compute_percentage_change',
    )

    @api.depends('current_price', 'new_price')
    def _compute_price_difference(self):
        for line in self:
            line.price_difference = line.new_price - line.current_price

    @api.depends('current_price', 'new_price')
    def _compute_percentage_change(self):
        for line in self:
            if line.current_price:
                line.percentage_change = (
                    (line.new_price - line.current_price) / line.current_price * 100
                )
            else:
                line.percentage_change = 0.0