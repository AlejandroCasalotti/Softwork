"""General business records, native ACLs and reviewed form actions. Odoo 19."""
import hashlib
import json
import math
import re
from datetime import date, datetime
from lxml import etree
from odoo import api, models, release
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import SQL

SECRET = re.compile(r'password|passwd|token|secret|credential|session|cookie|api_key|private_key|access_key', re.I)
TECHNICAL = ('ir.', 'base.', 'web.', 'auth.', 'bus.', 'mail.', 'discuss.', 'res.users',
             'res.groups', 'res.config', 'res.company', 'res.currency', 'res.lang', 'res.country',
             'res.bank', 'res.partner.bank', 'massive.', 'mcp.', 'iap.', 'payment.provider')
TYPES = {'char','text','selection','integer','float','monetary','boolean','date','datetime','many2one','many2many','one2many'}
DIRECTORY = {
    'res.users': {'id','name','login','active','company_id','company_ids','partner_id'},
    'res.company': {'id','name','currency_id','partner_id'},
    'res.currency': {'id','name','symbol','rounding','active'},
    'res.lang': {'id','name','code','active'},
    'res.country': {'id','name','code'},
    'res.country.state': {'id','name','code','country_id'},
}


class MassiveBusiness(models.AbstractModel):
    _inherit = 'massive.assistant.gateway'

    def _business_env(self, company_id):
        if release.version_info[0] != 19:
            raise UserError('Las herramientas generales requieren Massive Assistant actualizado para Odoo 19.')
        if not self.env.user.has_group('massive_assistant.group_massive_assistant_user'):
            raise AccessError('Usuario no autorizado para Massive Assistant.')
        if type(company_id) is not int or company_id <= 0 or company_id not in self.env.user.company_ids.ids:
            raise AccessError('Empresa no autorizada.')
        return self.with_context({'allowed_company_ids':[company_id], 'lang':self.env.user.lang, 'tz':self.env.user.tz}).env

    def _business_model(self, env, name):
        if not isinstance(name,str) or not re.fullmatch(r'[a-zA-Z_][a-zA-Z0-9_.]{0,99}',name) or name.startswith(TECHNICAL) and name not in DIRECTORY or SECRET.search(name) or name not in env:
            raise UserError('Elegí un modelo de negocio. La configuración técnica, seguridad y credenciales se administran en Odoo.')
        model=env[name]
        if model._abstract or model._transient:
            raise UserError('Este modelo requiere una herramienta especializada o un asistente de Odoo.')
        return model

    def _business_scope(self, model, company_id):
        if 'company_id' in model._fields and getattr(model._fields['company_id'],'comodel_name',None)=='res.company':
            return ['|',('company_id','=',False),('company_id','=',company_id)]
        if 'company_ids' in model._fields and getattr(model._fields['company_ids'],'comodel_name',None)=='res.company':
            return [('company_ids','in',[company_id])]
        return []  # No company field means shared model; record rules still apply.

    def _business_fields(self, model):
        info=model.fields_get(attributes=['string','type','required','readonly','relation','selection','store'])
        return {k:v for k,v in info.items() if not k.startswith('_') and not SECRET.search(k)
                and (model._name not in DIRECTORY or k in DIRECTORY[model._name])
                and v.get('type') in TYPES and k not in ('create_uid','write_uid','create_date','write_date')}

    def _business_record(self, model, company_id, record_id, operation, lock=False):
        if type(record_id) is not int or record_id<=0:
            raise UserError('Identificador de registro inválido.')
        model=model.with_context(active_model=model._name,active_id=record_id,active_ids=[record_id])
        record=model.search([('id','=',record_id)]+self._business_scope(model,company_id),limit=1)
        if not record:
            raise AccessError('Registro no disponible para este usuario y empresa.')
        record.check_access(operation)
        if lock:
            # Table is registry-owned, never supplied by a caller. IDs passed separately.
            env=model.env
            env.cr.execute(SQL('SELECT id FROM %s WHERE id = %s FOR UPDATE NOWAIT',SQL.identifier(model._table),record_id))
            env.invalidate_all()
            record=model.search([('id','=',record_id)]+self._business_scope(model,company_id),limit=1)
            if not record:raise AccessError('El registro ya no está disponible.')
            record.check_access(operation)
        return record

    def _business_actions(self, record):
        try:
            arch=record.get_view(view_type='form')['arch']
            root=etree.fromstring(arch.encode(),etree.XMLParser(resolve_entities=False,no_network=True))
        except (AccessError,UserError,KeyError,etree.XMLSyntaxError):
            return []
        actions={}
        for button in root.iter('button'):
            if any(ancestor.tag=='field' for ancestor in button.iterancestors()):continue
            if button.get('invisible','').strip() in ('1','True','true'):continue
            name=button.get('name','')
            if button.get('type')!='object' or not re.fullmatch(r'(action|button)_[a-zA-Z0-9_]{1,90}',name) or SECRET.search(name) or re.search(r'install|uninstall|upgrade|execute|python|server_action|database',name,re.I):
                continue
            groups=button.get('groups','').split(',')
            positive=[g.strip() for g in groups if g.strip() and not g.strip().startswith('!')]
            negative=[g.strip()[1:] for g in groups if g.strip().startswith('!')]
            if (positive and not any(record.env.user.has_group(g) for g in positive)) or any(record.env.user.has_group(g) for g in negative):
                continue
            if not callable(getattr(record,name,None)) or getattr(getattr(record,name),'_api_private',False):
                continue
            actions[name]={'method':name,'label':button.get('string') or name,
                           'condition':button.get('invisible',''),'confirmation':button.get('confirm','')}
        return list(actions.values())

    def _business_snapshot(self, record, lock=False):
        fields=self._business_fields(record)
        scalar=[k for k,v in fields.items() if v.get('store') and v['type'] not in ('one2many','many2many')]
        if len(scalar)>250:
            raise UserError('Registro demasiado complejo para una propuesta general. Usá una herramienta especializada.')
        result=record.read(list(dict.fromkeys(['display_name']+(['write_date'] if 'write_date' in record._fields else [])+scalar)))[0]
        # Include direct child contents so a quotation line edit invalidates its proposal.
        children={}
        for key,spec in fields.items():
            if spec['type'] not in ('one2many','many2many') or not spec.get('store'):
                continue
            if spec.get('relation','').startswith(TECHNICAL) or SECRET.search(spec.get('relation','')):continue
            rows=record[key]
            if len(rows)>100:raise UserError('El registro tiene demasiadas relaciones para una propuesta completa.')
            rows.check_access('read')
            if lock and rows and rows._auto:
                record.env.cr.execute(SQL('SELECT id FROM %s WHERE id = ANY(%s) ORDER BY id FOR UPDATE NOWAIT',SQL.identifier(rows._table),rows.ids))
                rows.invalidate_recordset()
            child_fields=self._business_fields(rows)
            names=[k for k,v in child_fields.items() if v.get('store') and v['type'] not in ('one2many','many2many')]
            children[key]=rows.sorted('id').read(list(dict.fromkeys(['display_name']+(['write_date'] if 'write_date' in rows._fields else [])+names)))
        result['relations']=children
        serialized=json.dumps(result,sort_keys=True,default=str)
        if len(serialized)>150000:raise UserError('El registro supera el tamaño de revisión. Usá una herramienta especializada.')
        return hashlib.sha256(serialized.encode()).hexdigest(),result

    def _business_values(self, model, company_id, values):
        if not isinstance(values,dict) or not 1<=len(values)<=20:
            raise UserError('Indicá entre uno y veinte campos explícitos por registro.')
        schema=self._business_fields(model);result={}
        for name,value in values.items():
            field=schema.get(name)
            if not field or name in ('id','display_name','state','company_id','company_ids') or field.get('readonly') or not model._fields[name].store:
                raise UserError('Campo no editable de forma general: '+str(name))
            kind=field['type']
            if kind in ('char','text','date','datetime','selection'):
                if value is not False and (not isinstance(value,str) or len(value)>5000):raise UserError('Texto de campo inválido.')
                if kind=='selection' and value is not False and value not in dict(field.get('selection') or []):raise UserError('Opción no válida.')
                if kind in ('date','datetime') and value is not False:
                    try:datetime.strptime(value,'%Y-%m-%d' if kind=='date' else '%Y-%m-%d %H:%M:%S')
                    except ValueError:raise UserError('Fecha inválida; las horas deben indicarse en UTC.') from None
            elif kind=='boolean':
                if type(value) is not bool:raise UserError('Campo booleano inválido.')
            elif kind in ('integer','float','monetary'):
                if type(value) not in (int,float) or not math.isfinite(value) or abs(value)>10**12 or kind=='integer' and type(value) is not int:raise UserError('Número inválido.')
            elif kind in ('many2one','many2many'):
                ids=([value] if value is not False else []) if kind=='many2one' else value
                if not isinstance(ids,list) or len(ids)>50 or any(type(v) is not int or v<=0 for v in ids) or len(set(ids))!=len(ids):raise UserError('Relación inválida.')
                related=model.env[field['relation']]
                matches=related.search([('id','in',ids)]+self._business_scope(related,company_id))
                if set(matches.ids)!=set(ids):raise AccessError('Un registro relacionado no está disponible para esta empresa.')
                matches.check_access('read')
                if kind=='many2many':value=[(6,0,ids)]
            else:
                raise UserError('Las líneas anidadas requieren crear/editar sus registros de línea o una herramienta especializada.')
            result[name]=value
        return result

    @api.model
    def assistant_capabilities(self, company_id):
        try:
            env=self._business_env(company_id)
            access={}
            for name in ('product.product','sale.order','purchase.order','stock.picking','account.move','website.page'):
                access[name]={op:env[name].has_access(op) if name in env else False for op in ('read','create','write','unlink')}
            return {'uid':env.uid,'user':env.user.display_name,'company_id':company_id,'access':access,'bridge_version':2}
        except (UserError,AccessError) as error:return {'error':str(error)[:1000],'rejected':True}

    @api.model
    def assistant_discover(self, company_id, model='', query='', offset=0, record_id=0):
        try:
            env=self._business_env(company_id)
            if not isinstance(query,str) or len(query)>80 or type(offset) is not int or not 0<=offset<=10000:raise UserError('Consulta inválida.')
            if model:
                records=self._business_model(env,model);records.check_access('read')
                record=self._business_record(records,company_id,record_id,'read') if record_id else records
                return {'model':model,'fields':self._business_fields(records),
                    'access':{op:record.has_access(op) and (model not in DIRECTORY or op=='read') for op in ('read','create','write','unlink')},
                    'actions':self._business_actions(record) if record_id and model not in DIRECTORY and record.has_access('write') else [],
                    'company_field':'company_id' if 'company_id' in records._fields else 'company_ids' if 'company_ids' in records._fields else None,
                    'note':'Permisos reales del usuario API. Las acciones visibles pueden requerir otro estado o un asistente nativo.'}
            names=[]
            for name in sorted(env.registry.models):
                if query.lower() not in name.lower():continue
                try:
                    records=self._business_model(env,name)
                    if records.has_access('read'):names.append({'model':name,'label':str(records._description)})
                except (UserError,AccessError):continue
                if len(names)>offset+50:break
            return {'models':names[offset:offset+50],'has_more':len(names)>offset+50,'next_offset':offset+50 if len(names)>offset+50 else None}
        except (UserError,AccessError) as error:return {'error':str(error)[:1000],'rejected':True}

    def _business_plan(self, env, company_id, model, operation, record_id, values, action, lock=False):
        records=self._business_model(env,model)
        if model in DIRECTORY:raise UserError('Los directorios técnicos solo admiten consultas de sus campos públicos.')
        if not records._auto:raise UserError('Un informe de solo lectura no admite cambios.')
        if operation not in ('create','update','delete','action'):raise UserError('Operación no habilitada.')
        if not isinstance(action,str) or not isinstance(values,dict):raise UserError('Argumentos inválidos.')
        records.check_access('read')
        record=None;token='';snapshot={}
        if operation=='create':
            if record_id or action:raise UserError('Crear no requiere registro anterior ni acción.')
            records.check_access('create')
        else:
            record=self._business_record(records,company_id,record_id,'unlink' if operation=='delete' else 'write',lock)
            token,snapshot=self._business_snapshot(record,lock)
        if operation=='delete':
            if values or action:raise UserError('Eliminar no acepta campos ni otra acción.')
            normalized={}
            rows=[{'field':'Eliminar registro y relaciones dependientes según Odoo','old':json.dumps(snapshot,ensure_ascii=False,default=str),'new':'ELIMINAR','scope':record.display_name}]
        elif operation=='action':
            if values:raise UserError('Una acción no acepta cambios de campos adicionales.')
            actions={v['method']:v for v in self._business_actions(record)}
            if action not in actions:raise UserError('La acción no está disponible en el formulario autorizado del usuario.')
            if model=='stock.picking':raise UserError('Para reservas y entregas usá las herramientas especializadas, que verifican cantidades y lotes.')
            if model=='sale.order' and action=='action_confirm':raise UserError('Usá la herramienta especializada de confirmar venta.')
            rows=[{'field':'Acción de Odoo','old':str(snapshot.get('state','')),'new':actions[action]['label'],'scope':record.display_name}]
            rows.append({'field':'Documento completo para revisar (datos actuales)','old':json.dumps(snapshot,ensure_ascii=False,default=str),'new':actions[action]['confirmation'],'scope':record.display_name})
            normalized={}
        else:
            if action:raise UserError('La edición de campos no ejecuta acciones.')
            normalized=self._business_values(records,company_id,values)
            rows=[{'field':self._business_fields(records)[k]['string'],'old':json.dumps(snapshot.get(k),default=str,ensure_ascii=False),'new':json.dumps(values[k],ensure_ascii=False),'scope':record.display_name if record else model} for k in normalized]
            if operation=='create' and 'company_id' in records._fields:normalized['company_id']=company_id
        token=hashlib.sha256(json.dumps({'snapshot':token,'model':model,'operation':operation,'values':normalized,'action':action,'uid':env.uid,'company_id':company_id},sort_keys=True,default=str).encode()).hexdigest()
        preview={'kind':'business_record','company':env['res.company'].browse(company_id).display_name,'document':record.display_name if record else model,
            'rows':rows,'errors':[],'notice':'Operación nativa de Odoo con los permisos de tu usuario. Puede disparar automatizaciones, correos, documentos relacionados o efectos contables según la configuración. Revisá campos, acción y empresa; no se ejecuta hasta confirmar. No se fuerza el estado mediante edición de campos.'}
        shared=record and (not ('company_id' in records._fields or 'company_ids' in records._fields) or 'company_id' in records._fields and not record.company_id or 'company_ids' in records._fields and len(record.company_ids)>1)
        if shared:
            preview['notice']='REGISTRO COMPARTIDO: el cambio o eliminación afecta a todas las empresas que usan este registro, no solo a la seleccionada. '+preview['notice']
            for row in rows:row['scope']='Registro compartido entre empresas: '+record.display_name
        return records,record,normalized,preview,token

    @api.model
    def business_preview(self, company_id, model, operation, record_id, values, action):
        try:
            env=self._business_env(company_id)
            _,_,_,preview,token=self._business_plan(env,company_id,model,operation,record_id,values,action)
            return {'preview':preview,'token':token}
        except (UserError,AccessError) as error:return {'error':str(error)[:1000],'rejected':True}

    @api.model
    def business_execute(self, company_id, model, operation, record_id, values, action, expected_token):
        try:
            with self.env.cr.savepoint():
                env=self._business_env(company_id)
                records,record,normalized,_,token=self._business_plan(env,company_id,model,operation,record_id,values,action,lock=True)
                if not isinstance(expected_token,str) or token!=expected_token:raise UserError('El registro cambió. Prepará una nueva propuesta.')
                if operation=='delete':
                    remote_id=record.id
                    if record.unlink() is not True:raise UserError('Odoo no confirmó la eliminación.')
                    return {'id':remote_id,'state':'deleted','complete':True}
                if operation=='create':record=records.create(normalized)
                elif operation=='update':record.write(normalized)
                else:
                    result=getattr(record,action)()
                    if isinstance(result,dict) and result.get('type','').startswith('ir.actions.'):
                        raise UserError('Odoo abrió un asistente o una acción adicional. Completá ese paso en Odoo; los cambios SQL de este intento se revirtieron.')
                record.check_access('read')
                if self._business_scope(records,company_id) and not records.search_count([('id','=',record.id)]+self._business_scope(records,company_id)):
                    raise UserError('La operación cambió el alcance de empresa; se revirtió.')
                return {'id':record.id,'state':str(record.state) if 'state' in records._fields else '', 'complete':True}
        except (UserError,AccessError) as error:return {'error':str(error)[:1000],'rejected':True}
