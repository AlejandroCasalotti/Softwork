"""Publish a reviewed, normalized image to a specific website, never arbitrary files."""
import base64
import io
from odoo import api,models
from odoo.exceptions import UserError,AccessError


class MassiveImages(models.AbstractModel):
    _inherit='massive.assistant.gateway'

    @api.model
    def website_image_create(self,company_id,website_id,name,image_data,source_url=''):
        try:
            with self.env.cr.savepoint():
                env=self._business_env(company_id)
                if 'website' not in env:raise UserError('El módulo Sitio Web no está instalado.')
                if type(website_id) is not int or website_id<=0 or not isinstance(name,str) or not 1<=len(name)<=120 or not isinstance(image_data,str) or len(image_data)>5600000 or not isinstance(source_url,str) or len(source_url)>1000:
                    raise UserError('Datos de imagen inválidos.')
                website=env['website'].search([('id','=',website_id),('company_id','=',company_id)],limit=1)
                if not website:raise AccessError('Sitio no disponible para esta empresa.')
                website.check_access('write')
                env['ir.attachment'].check_access('create')
                raw=base64.b64decode(image_data,validate=True)
                if len(raw)>4*1024*1024:raise UserError('La imagen supera el tamaño admitido.')
                from PIL import Image
                with Image.open(io.BytesIO(raw)) as image:
                    if image.format!='JPEG' or image.width*image.height>20000000:raise UserError('La imagen no es un JPEG normalizado.')
                    image.verify()
                attachment=env['ir.attachment'].create({'name':name,'type':'binary','datas':image_data,
                    'mimetype':'image/jpeg','public':True,'website_id':website.id,'company_id':company_id,
                    'res_model':'website','res_id':website.id,'description':source_url})
                attachment.check_access('read')
                return {'id':attachment.id,'website_id':website.id,'public':attachment.public,'complete':True}
        except (UserError,AccessError) as error:return {'error':str(error)[:1000],'rejected':True}
        except (ValueError,TypeError,OSError):return {'error':'Imagen inválida. No se creó el archivo.','rejected':True}
