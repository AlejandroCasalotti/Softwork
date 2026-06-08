# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo import _
import logging
import requests

_logger = logging.getLogger(__name__)

# APIs públicas conocidas (algunas pueden requerir registro)
AFIP_APIS = [
    # ejemplos - hay que verificar cuáles funcionan
    "https://api.afip.gob.ar/servicios/paas/contribuyentes/v1/{cuit}",
]


class ResPartner(models.Model):
    _inherit = "res.partner"

    # CAMPOS AFIP
    estado_padron = fields.Char('Estado AFIP')
    imp_ganancias_padron = fields.Selection([
        ('NI', 'No Inscripto'),
        ('AC', 'Activo'),
        ('EX', 'Exento'),
        ('NC', 'No corresponde'),
    ], 'Ganancias')
    imp_iva_padron = fields.Selection([
        ('NI', 'No Inscripto'),
        ('AC', 'Activo'),
        ('EX', 'Exento'),
        ('NA', 'No alcanzado'),
    ], 'IVA')
    monotributo_padron = fields.Selection([('N', 'No'), ('S', 'Si')], 'Monotributo')
    empleador_padron = fields.Boolean('Empleador')
    last_update_padron = fields.Date('Last Update Padron')
    activities_padron = fields.Char('Actividades')

    def update_constancia_from_padron_afip(self):
        """Actualiza desde Padrón AFIP"""
        self.ensure_one()
        
        # Obtener CUIT del partner
        cuit = self.vat
        if not cuit:
            raise UserError(_('Debe tener un CUIT configurado en el campo VAT'))
        
        # Limpiar CUIT
        try:
            cuit = ''.join(filter(str.isdigit, str(cuit)))
        except:
            raise UserError(_('CUIT inválido'))
        
        if len(cuit) != 11:
            raise UserError(_('El CUIT debe tener 11 dígitos sin guiones'))
        
        # Consultar AFIP
        datos = self._consultar_afip(cuit)
        
        if not datos:
            # Abrir página de AFIP como alternativa
            return self._abrir_pagina_afip(cuit)
        
        # Buscar provincia
        state_id = self._buscar_provincia(datos.get('provincia', ''))
        
        # Actualizar datos
        vals = {
            'name': datos.get('name', '') or self.name,
            'street': datos.get('direccion', '') or self.street,
            'city': datos.get('localidad', '') or self.city,
            'zip': datos.get('cod_postal', '') or self.zip,
            'state_id': state_id or self.state_id,
            'estado_padron': datos.get('estado', ''),
            'imp_iva_padron': datos.get('imp_iva', 'NI'),
            'imp_ganancias_padron': datos.get('imp_ganancias', 'NI'),
            'monotributo_padron': datos.get('monotributo', 'N'),
            'empleador_padron': datos.get('empleador', False),
            'last_update_padron': fields.Date.today(),
            'activities_padron': datos.get('actividades', ''),
        }
        
        self.write(vals)
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def _abrir_pagina_afip(self, cuit):
        """Abre la página de AFIP si no hay API"""
        return {
            'type': 'ir.actions.act_url',
            'url': f'https://padronesar.afip.gob.ar/PadronConsumidorActivo/constancia?cuit={cuit}',
            'target': 'new',
        }
    
    def _buscar_provincia(self, nombre):
        """Busca provincia por nombre"""
        if not nombre:
            return False
        
        # Buscar por nombre
        state = self.env['res.country.state'].search([
            ('name', 'ilike', nombre),
            ('country_id.code', '=', 'AR'),
        ], limit=1)
        
        if state:
            return state.id
        
        # Mapeo común
        mapas = {
            'santa fe': 'S', 'buenos aires': 'B', 'capital federal': 'CABA',
            'caba': 'CABA', 'rosario': 'S', 'mendoza': 'M', 'tucuman': 'T',
            'cordoba': 'X', 'entre rios': 'E', 'corrientes': 'W', 'misiones': 'N',
        }
        
        nombre_lower = nombre.lower().strip()
        if nombre_lower in mapas:
            state = self.env['res.country.state'].search([
                ('code', '=', mapas[nombre_lower]),
                ('country_id.code', '=', 'AR'),
            ], limit=1)
            if state:
                return state.id
        
        return False
    
    def _consultar_afip(self, cuit):
        """Consulta AFIP - intenta varias APIs"""
        
        # ============================================
        # MÉTODO 1: API oficial de AFIP (si está habilitada)
        # ============================================
        datos = self._consultar_api_oficial(cuit)
        if datos:
            return datos
        
        # ============================================
        # MÉTODO 2: APIs alternativas gratuitas
        # ============================================
        datos = self._consultar_apis_alternativas(cuit)
        if datos:
            return datos
        
        # ============================================
        # MÉTODO 3: Web scraping (último intento)
        # ============================================
        datos = self._consultar_web_scraping(cuit)
        if datos:
            return datos
        
        # No se pudo obtener datos
        return None
    
    def _consultar_api_oficial(self, cuit):
        """Consulta la API oficial de AFIP"""
        try:
            # Obtener compañía para el token
            company = self.env.company
            if not company:
                company = self.env['res.company'].search([], limit=1)
            
            if not company:
                return None
            
            # La API oficial requiere token de AFIP
            # No es pública, necesita habilitación
            # Intentar de todas formas
            url = f"https://afipapi.com.ar/ws/services/AA/auth/ws_sr_padron_a4_v1/contribuyentes/{cuit}"
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                return self._procesar_datos_afip(data)
                
        except Exception as e:
            _logger.warning(f'API oficial error: {e}')
        
        return None
    
    def _consultar_apis_alternativas(self, cuit):
        """Intenta APIs alternatives"""
        
        # Lista de APIs públicas conocidas
        # NOTA: La mayoría son de pago o requieren registro
        
        apis_pruebas = [
            # Estas son URLs de ejemplo - hay que verificar funcionan
            # {"url": f"https://api.example.com/afip/cuit/{cuit}", "key": None},
        ]
        
        for api_info in apis_pruebas:
            try:
                url = api_info.get('url', '')
                api_key = api_info.get('key')
                
                headers = {'Content-Type': 'application/json'}
                if api_key:
                    headers['Authorization'] = f'Bearer {api_key}'
                
                response = requests.get(url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success') or data.get('data'):
                        return self._procesar_datos_afip(data)
                        
            except Exception as e:
                _logger.warning(f'API {url} error: {e}')
                continue
        
        # Si no hay APIs disponibles, retornar None
        _logger.info('No hay APIs públicas disponibles')
        return None
    
    def _consultar_web_scraping(self,uit):
        """Web scraping de Padrón AFIP"""
        try:
            session = requests.Session()
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            }
            
            # Ir a la página del padrón
            url = "https://padronesar.afip.gob.ar/PadronConsumidorActivo/"
            
            response = session.get(url, headers=headers, timeout=20)
            
            if response.status_code != 200:
                return None
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar formulario
            form = soup.find('form')
            if not form:
                return None
            
            action = form.get('action', '')
            if action:
                url_post = f"https://padronesar.afip.gob.ar{action}"
            else:
                url_post = "https://padronesar.afip.gob.ar/PadronConsumidorActivo/buscaContribuyente.html"
            
            # Buscar inputs del formulario
            inputs = soup.find_all('input')
            data = {}
            for inp in inputs:
                name = inp.get('name', '')
                type_inp = inp.get('type', 'text')
                if type_inp in ['text', 'hidden'] and 'cuit' in name.lower():
                    data[name] = cuit
            
            # Enviar solicitud
            response = session.post(url_post, data=data, headers=headers, timeout=20)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Buscar datos en tablas
                datos = self._extraer_datos_tabla(soup)
                if datos:
                    return datos
                    
        except Exception as e:
            _logger.warning(f'Web scraping error: {e}')
        
        return None
    
    def _extraer_datos_tabla(self, soup):
        """Extrae datos de las tablas HTML"""
        try:
            tables = soup.find_all('table')
            
            datos = {}
            
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        key = cells[0].get_text(strip=True).lower()
                        value = cells[1].get_text(strip=True)
                        
                        if 'denominacion' in key or 'nombre' in key:
                            datos['name'] = value
                        elif 'estado' in key:
                            datos['estado'] = value
                        elif 'domicilio' in key or 'direccion' in key:
                            datos['direccion'] = value
                        elif 'localidad' in key:
                            datos['localidad'] = value
                        elif 'codigo postal' in key or 'cp' in key:
                            datos['cod_postal'] = value
                        elif 'provincia' in key or 'jurisdiccion' in key:
                            datos['provincia'] = value
            
            if datos.get('name'):
                return datos
                
        except Exception as e:
            _logger.warning(f'Extraer datos error: {e}')
        
        return None
    
    def _procesar_datos_afip(self, data):
        """Procesa los datos de la API"""
        if not data:
            return None
        
        # Extraer data
        if isinstance(data, dict):
            if data.get('data'):
                data = data['data']
            elif data.get('GetPersonaResult'):
                data = data['GetPersonaResult']
        
        if not data:
            return None
        
        return {
            'name': data.get('denominacion') or data.get('nombre') or data.get('name') or '',
            'estado': data.get('estado') or 'Activo',
            'direccion': data.get('direccion') or data.get('domicilio') or '',
            'localidad': data.get('localidad') or '',
            'cod_postal': data.get('cod_postal') or data.get('cp') or '',
            'provincia': data.get('provincia') or '',
            'imp_iva': data.get('imp_iva') or 'NI',
            'imp_ganancias': data.get('imp_ganancias') or 'NI',
            'monotributo': data.get('monotributo') or 'N',
            'empleador': data.get('empleador') == 'S',
            'actividades': data.get('actividades') or '',
        }