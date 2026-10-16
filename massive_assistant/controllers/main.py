import hashlib
import json
import re
import secrets
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from odoo import http, fields
from odoo.http import request
from odoo.exceptions import AccessDenied, UserError
from ..models.session import SERVER


def user_guard():
    if request.env.user.share or not request.env.user.has_group('massive_assistant.group_massive_assistant_user'):raise AccessDenied()
    return request.env.user


def origin_guard():
    origin=request.httprequest.headers.get('Origin','')
    expected=request.httprequest.host_url.rstrip('/')
    if origin!=expected or not origin.startswith('https://'):raise AccessDenied()


class MassiveAssistant(http.Controller):
    @http.route('/massive_assistant/panel',type='http',auth='user',methods=['GET'])
    def panel(self,**kwargs):
        user_guard()
        content=(Path(__file__).resolve().parents[1]/'static/src/panel.html').read_text()
        return request.make_response(content,headers=[('Content-Type','text/html; charset=utf-8'),('Cache-Control','no-store'),('X-Frame-Options','SAMEORIGIN'),('X-Content-Type-Options','nosniff')])

    @http.route('/massive_assistant/api',type='jsonrpc',auth='user',methods=['POST'],csrf=False)
    def api(self,action='',data=None):
        user=user_guard();origin_guard()
        if not isinstance(data,dict) or len(json.dumps(data))>1500000:raise UserError('Solicitud inválida.')
        sessions=request.env['massive.assistant.session'].sudo()
        session=sessions.search([('user_id','=',user.id)],limit=1)
        if action=='visible':
            try:design=session._request('status',job='design').get('design',{}) if session else {}
            except UserError:design={}
            return {'visible':True,'design':design}
        if action=='pair':
            key=data.get('api_key','')
            if not isinstance(key,str) or not 8<=len(key)<=512 or any(ord(c)<=32 or ord(c)>126 for c in key):raise UserError('Ingresá tu propia clave API de Odoo, no tu contraseña.')
            if session:
                try:session._request('revoke',{})
                except UserError:pass
                session.unlink()
            secret=secrets.token_urlsafe(32);challenge=hashlib.sha256(secret.encode()).hexdigest()
            base=request.env['ir.config_parameter'].sudo().get_param('web.base.url','').rstrip('/')
            parsed=urlsplit(base)
            if parsed.scheme!='https' or not parsed.hostname or parsed.path or parsed.query or parsed.fragment:raise UserError('Configurá web.base.url con la URL raíz HTTPS pública de Odoo.')
            session=sessions.create({'user_id':user.id,'expires_at':fields.Datetime.now()+timedelta(minutes=15)})
            session._save({'secret':secret,'pending_key':key,'pending':True,'login':user.login,'uid':user.id})
            return {'url':SERVER+'/extension/connect/?'+urlencode({'challenge':challenge,'native_uid':user.id,'origin':base,'database':request.db})}
        if not session:raise UserError('Conectá primero tu cuenta de Massive Connector.')
        saved=session._load()
        if action=='finish':
            if not saved.get('pending'):raise UserError('Este acceso ya está vinculado.')
            result=session._request('native-bind',{'api_key':saved['pending_key'],'uid':user.id,'login':user.login})
            session.expires_at=fields.Datetime.now()+timedelta(seconds=min(result['expires_in'],28800))
            saved.pop('pending_key',None);saved['pending']=False;saved['access_id']=result['access_id'];session._save(saved)
            return {'bound':True}
        if action=='disconnect':
            try:session._request('revoke',{})
            except UserError:pass
            session.unlink();return {'disconnected':True}
        if saved.get('pending'):raise UserError('Completá la vinculación en Massive Connector y luego presioná Completar vinculación.')
        if saved.get('uid')!=user.id:raise AccessDenied()
        if action in ('status','result','operation','options'):
            result=session._request(action,job=data.get('job','design' if action=='status' else None))
            if action=='status':
                if result.get('access_id')!=saved.get('access_id'):raise AccessDenied()
                result['native']=True
            return result
        if action not in ('chat','upload','preview','confirm','cancel'):raise UserError('Acción no habilitada.')
        data={**data,'access_id':saved['access_id']}
        return session._request(action,data)
