"""Small explicit compatibility bridge. Never exposes arbitrary model/method execution."""
from odoo import api, models
from odoo.exceptions import AccessError, UserError


class MassiveGateway(models.AbstractModel):
    _name='massive.assistant.gateway'
    _description='Herramientas explícitas de Massive Connector'

    @api.model
    def contextual_price(self,product_id,pricelist_id,company_id):
        if not self.env.user.has_group('massive_assistant.group_massive_assistant_user'):raise AccessError('Usuario no autorizado para Massive Connector.')
        if any(type(v) is not int or v<=0 for v in (product_id,pricelist_id,company_id)):raise UserError('Identificadores inválidos.')
        if company_id not in self.env.user.company_ids.ids:raise AccessError('Empresa no autorizada.')
        ctx={'allowed_company_ids':[company_id]}
        product=self.env['product.product'].with_context(**ctx).search([('id','=',product_id),'|',('company_id','=',False),('company_id','=',company_id)],limit=1)
        pricelist=self.env['product.pricelist'].with_context(**ctx).search([('id','=',pricelist_id),'|',('company_id','=',False),('company_id','=',company_id)],limit=1)
        if not product or not pricelist:raise AccessError('Producto o lista no disponibles.')
        return pricelist._get_product_price(product,quantity=1.0)
