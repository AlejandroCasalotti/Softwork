"""Encrypted per-user pairing state. No messages, files or ERP copies stored."""
import json
import base64
from datetime import timedelta
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler
from urllib.error import HTTPError
from cryptography.fernet import Fernet
from odoo import api, fields, models, SUPERUSER_ID
from odoo.exceptions import UserError

SERVER='https://app.massiveconnector.com'


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


class MassiveSession(models.Model):
    _name='massive.assistant.session'
    _description='Acceso temporal Asistente Massive'
    _rec_name='user_id'
    user_id=fields.Many2one('res.users',required=True,ondelete='cascade',index=True)
    sealed=fields.Text(groups='base.group_no_one',copy=False)
    expires_at=fields.Datetime(required=True,index=True)
    _sql_constraints=[('user_unique','unique(user_id)','Existe una sesión para este usuario.')]

    @api.model
    def _cipher(self):
        params=self.env['ir.config_parameter'].sudo()
        # Store the small key in Odoo's private attachment storage/filestore;
        # the SQL parameter contains only its attachment ID, not the key.
        attachment_id=params.search([('key','=','massive_assistant.key_attachment')],limit=1).value
        if not attachment_id:
            self.env.cr.execute('SELECT pg_advisory_xact_lock(%s)',[649136625])
            attachment_id=params.search([('key','=','massive_assistant.key_attachment')],limit=1).value
            if not attachment_id:
                attachment=self.env['ir.attachment'].with_user(SUPERUSER_ID).sudo().create({'name':'Massive Assistant internal key','res_model':'ir.config_parameter','res_id':0,'public':False,'mimetype':'application/octet-stream','datas':base64.b64encode(Fernet.generate_key())})
                attachment_id=str(attachment.id);params.set_param('massive_assistant.key_attachment',attachment_id)
        try:
            attachment=self.env['ir.attachment'].sudo().browse(int(attachment_id)).exists()
            if not attachment or attachment.public or attachment.res_model!='ir.config_parameter' or attachment.res_id or attachment.file_size!=44 or attachment.name!='Massive Assistant internal key':raise ValueError
            return Fernet(base64.b64decode(attachment.datas))
        except Exception:raise UserError('No se pudo abrir la clave interna del asistente. Revisá la copia de filestore o volvé a configurar la vinculación con el administrador.') from None

    def _load(self):
        self.ensure_one()
        if self.expires_at<=fields.Datetime.now():raise UserError('La autorización venció. Volvé a conectar el asistente.')
        try:return json.loads(self._cipher().decrypt(self.sealed.encode()))
        except Exception:raise UserError('Volvé a conectar el asistente.') from None

    def _save(self,data):
        self.ensure_one();self.sudo().sealed=self._cipher().encrypt(json.dumps(data).encode()).decode()

    def _request(self,action,body=None,job=None):
        self.ensure_one();data=self._load()
        if action not in ('status','chat','result','revoke','upload','preview','confirm','cancel','operation','options','native-bind'):raise UserError('Acción no habilitada.')
        path='/extension/native/bind/' if action=='native-bind' else '/extension/api/'+action+'/'
        if job:
            from urllib.parse import urlencode
            if not isinstance(job,str) or len(job)>100:raise UserError('Identificador inválido.')
            path+='?'+urlencode({'job':job})
        encoded=None if body is None else json.dumps(body,allow_nan=False).encode()
        if encoded and len(encoded)>1500000:raise UserError('El archivo supera el límite permitido.')
        req=Request(SERVER+path,data=encoded,headers={'Authorization':'Bearer mcx_'+data['secret'],'Content-Type':'application/json','Accept':'application/json'})
        try:
            with build_opener(ProxyHandler({}),NoRedirect()).open(req,timeout=15) as response:
                raw=response.read(1500001)
                if len(raw)>1500000:raise ValueError
                result=json.loads(raw)
                if not isinstance(result,dict):raise ValueError
                return result
        except Exception:raise UserError('No se pudo completar la consulta. Revisá conexión, autorización, saldo y permisos. No repitas cambios sin consultar su estado.') from None

    @api.model
    def _cron_cleanup(self):
        self.sudo().search([('expires_at','<=',fields.Datetime.now())],limit=1000).unlink()
