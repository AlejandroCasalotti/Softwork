from odoo import models, fields, api

class ReglaCosto(models.Model):
    _name = 'coste.proveedor.regla'
    _description = 'Regla de Costo Proveedor'
    
    name = fields.Char('Nombre Regla', required=True)
    
    linea_ids = fields.One2many(
        'coste.proveedor.linea', 
        'regla_id', 
        string='Líneas de Regla'
    )
    
    # Campos calculados para vista
    descuento_total = fields.Float(
        string='Descuento Total %', 
        compute='_compute_totales',
        store=True
    )
    tarifa_total = fields.Float(
        string='Tarifa Total €', 
        compute='_compute_totales',
        store=True
    )
    
    @api.depends('linea_ids.porcentaje_descuento', 'linea_ids.tarifa_extra')
    def _compute_totales(self):
        for record in self:
            record.descuento_total = sum(record.linea_ids.mapped('porcentaje_descuento'))
            record.tarifa_total = sum(record.linea_ids.mapped('tarifa_extra'))


class ReglaCostoLinea(models.Model):
    _name = 'coste.proveedor.linea'
    _description = 'Línea Regla Costo'
    
    regla_id = fields.Many2one('coste.proveedor.regla', 'Regla')
    descripcion = fields.Char('Descripción')
    porcentaje_descuento = fields.Float('Descuento %')
    tarifa_extra = fields.Float('Tarifa Extra €')
    secuencia = fields.Integer('Secuencia', default=10)