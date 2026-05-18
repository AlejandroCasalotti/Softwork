from odoo import api, fields, models


class ChangePriceLine(models.TransientModel):
    """One2many for align the products with new price"""
    _name = 'change.precio.line'
    _rec_name = 'product_id'
    _description = "Aumentar el precio en linea"

    mass_price_update_id = fields.Many2one('mass.price.update',
                                           string='Number',
                                           help='The related field from mass'
                                                'price update', )
    product_id = fields.Many2one(
        'product.supplierinfo', string='Product', required=True,
        domain="[('active', '=', True)]", help='Selected products will show')
    current_price = fields.Float(string='Current Price', digits='Product Price',
                                 related='product_id.price',
                                 help='The current Sales price supplier')
    new_price = fields.Float(string='New Price', digits='Product Price',
                             compute='_compute_new_price_cost',
                             help='Computing the new price based on the '
                                  'percentage')
    currency_id = fields.Many2one('res.currency',
                                  string='Currency',
                                  related='product_id.currency_id',
                                  help='The currency of the product')

    @api.depends('mass_price_update_id.apply_on',
                 'mass_price_update_id.change',
                 'mass_price_update_id.apply_type')
    def _compute_new_price_cost(self):
        """Compute new price"""
        for record in self:
            if record.mass_price_update_id.apply_type == 'add':
                percentage_num = 1 + record.mass_price_update_id.change
            else:
                percentage_num = 1 - record.mass_price_update_id.change
            if record.mass_price_update_id.apply_on == 'precio':
                record.new_price = record.current_price * percentage_num
            else:
                record.new_price = False