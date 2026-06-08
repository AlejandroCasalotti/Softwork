# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo import _
import logging
import requests
from bs4 import BeautifulSoup

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    # ============================================================
    # CAMPOS AFIP
    # ============================================================
    
    x_afip_cuit = fields.Char(string='AFIP CUIT', help='CUIT sin guiones')
    x_estado_padron = fields.Char(string='Estado AFIP', readonly=True)
    x_imp_iva_padron = fields.Char(string='IVA AFIP', readonly=True)
    x_imp_ganancias_padron = fields.Char(string='Ganancias AFIP', readonly=True)
    x_last_update_padron = fields.Date(string='Última Actualización AFIP', readonly=True)
    
    # ============================================================
    # BOTÓN PRINCIPAL
    # ============================================================
    
    def action_update_from_padron_afip(self):
        """Consulta y actualiza desde Padrón AFIP"""
        self.ensure_one()
        
        if not self.x_afip_cuit:
            raise UserError(_('Debe ingresar el CUIT primero'))
        
        # Limpiar CUIT
        try:
            cuit = ''.join(filter(str.isdigit, str(self.x_afip_cuit)))
        except:
            raise UserError(_('CUIT inválido'))
        
        if len(cuit) != 11:
            raise UserError(_('El CUIT debe tener 11 dígitos sin guiones'))
        
        # Consultar AFIP
        datos_afip = self._consultar_afip(cuit)
        
        if not datos_afip:
            raise UserError(_('No se pudieron obtener datos de AFIP'))
        
        # Buscar país Argentina
        pais_argentina = self.env.ref('base.ar')
        
        # Buscar provincia
        state_id = False
        if datos_afip.get('provincia'):
            state_id = self._buscar_provincia(datos_afip['provincia'])
        
        # Actualizar datos
        vals = {
            'name': datos_afip.get('name', '') or self.name,
            'street': datos_afip.get('street', '') or self.street,
            'city': datos_afip.get('city', '') or self.city,
            'zip': datos_afip.get('zip', '') or self.zip,
            'state_id': state_id or self.state_id,
            'country_id': pais_argentina.id if pais_argentina else self.country_id.id,
            'x_estado_padron': datos_afip.get('estado', ''),
            'x_imp_iva_padron': datos_afip.get('imp_iva', ''),
            'x_imp_ganancias_padron': datos_afip.get('imp_ganancias', ''),
            'x_last_update_padron': fields.Date.today(),
        }
        
        self.write(vals)
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    # ============================================================
    # WEB SCRAPING
    # ============================================================
    
    def _consultar_afip(self, cuit):
        """
        Consulta datos de AFIP usando web scraping
        """
        # Método 1: Padrón consumidores activo
        datos = self._scraping_padron_consumidor(cuit)
        if datos:
            return datos
        
        # Método 2: Constancia de inscripción
        datos = self._scraping_constancia(cuit)
        if datos:
            return datos
        
        # Método 3: Busca en paginas alternativas
        datos = self._scraping_alternativo(cuit)
        if datos:
            return datos
        
        return None
    
    def _scraping_padron_consumidor(self, cuit):
        """
        Scraping de padronesar.afip.gob.ar
        """
        try:
            session = requests.Session()
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
            }
            
            # URL del padrón
            url = "https://padronesar.afip.gob.ar/PadronConsumidorActivo/buscaContribuyente.html"
            
            # Primero obtener la página inicial
            response = session.get(url, headers=headers, timeout=20)
            
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar el formulario
            form = soup.find('form')
            
            if not form:
                return None
            
            # Buscar inputs necesarios
            action = form.get('action', '')
            if action:
                url = "https://padronesar.afip.gob.ar" + action
            
            # Buscar id del CUIT
            inputs = soup.find_all('input')
            params = {}
            
            for inp in inputs:
                name = inp.get('name', '')
                type_input = inp.get('type', 'text')
                
                if type_input == 'text' or type_input == 'hidden':
                    if 'cuit' in name.lower():
                        params[name] = cuit
                    elif 'id' in name.lower():
                        pass  # Puede tener ID de sesión
            
            # Enviar solicitud
            response = session.post(url, data=params, headers=headers, timeout=20)
            
            if response.status_code == 200:
                # Procesar respuesta
                soup = BeautifulSoup(response.text, 'html.parser')
                datos = self._parsear_html_afip(str(soup))
                
                if datos:
                    return datos
                    
        except Exception as e:
            _logger.error(f"Error scraping: {e}")
        
        return None
    
    def _scraping_constancia(self, cuit):
        """
        Scraping de constancia de inscripción
        """
        try:
            session = requests.Session()
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml',
            }
            
            url = f"https://www.afip.gob.ar/genericos/constanciaInscripcion.asp?cuit={cuit}&clase=contribuyente"
            
            response = session.get(url, headers=headers, timeout=20)
            
            if response.status_code == 200:
                datos = self._parsear_html_afip(response.text)
                if datos:
                    return datos
                    
        except Exception as e:
            _logger.warning(f"Constancia error: {e}")
        
        return None
    
    def _scraping_alternativo(self, cuit):
        """
        Intentar con otras fuentes
        """
        # Aquí puedes agregar otras URLs si las conoces
        urls_alternativas = []
        
        for url in urls_alternativas:
            try:
                response = requests.get(f"{url}/{cuit}", timeout=10)
                if response.status_code == 200:
                    datos = self._parsear_html_afip(response.text)
                    if datos:
                        return datos
            except:
                continue
        
        return None
    
    def _parsear_html_afip(self, html):
        """
        Extrae datos del HTML de AFIP
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            texto = soup.get_text(separator=' ', strip=True)
            
            # Buscar la denominacion (nombre)
            # Viene después de "Denominación:" o "Denominacion:"
            datos = {}
            
            # Estado
            if 'activo' in texto.lower():
                datos['estado'] = 'Activo'
            elif 'baja' in texto.lower():
                datos['estado'] = 'Inactivo'
            else:
                datos['estado'] = 'Activo'  # Por defecto
            
            # IVA - buscar en tablas o texto
            if 'iva' in texto.lower():
                texto_lower = texto.lower()
                if 'responsable inscripto' in texto_lower or 'ri' in texto_lower:
                    datos['imp_iva'] = 'Responsable Inscripto'
                elif 'monotributo' in texto_lower:
                    datos['imp_iva'] = 'Monotributo'
                elif 'exento' in texto_lower:
                    datos['imp_iva'] = 'Exento'
                else:
                    datos['imp_iva'] = 'No Inscripto'
            
            # Buscar dirección
            if 'domicilio' in texto.lower() or 'direccion' in texto.lower():
                # Intentar buscar en tablas
                tables = soup.find_all('table')
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        for i, cell in enumerate(cells):
                            cell_text = cell.get_text(strip=True).lower()
                            if 'direccion' in cell_text or 'domicilio' in cell_text:
                                if i + 1 < len(cells):
                                    direccion = cells[i + 1].get_text(strip=True)
                                    if direccion and len(direccion) > 3:
                                        datos['street'] = direccion
                                        break
            
            # Buscar código postal
            if 'codigo postal' in texto.lower() or 'cp' in texto.lower():
                tables = soup.find_all('table')
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        for i, cell in enumerate(cells):
                            cell_text = cell.get_text(strip=True).lower()
                            if 'codigo postal' in cell_text or cell_text == 'cp':
                                if i + 1 < len(cells):
                                    cp = cells[i + 1].get_text(strip=True)
                                    if cp and cp.isdigit():
                                        datos['zip'] = cp
                                        break
            
            # Buscar localidad
            if 'localidad' in texto.lower() or 'ciudad' in texto.lower():
                tables = soup.find_all('table')
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        for i, cell in enumerate(cells):
                            cell_text = cell.get_text(strip=True).lower()
                            if 'localidad' in cell_text or 'ciudad' in cell_text:
                                if i + 1 < len(cells):
                                    ciudad = cells[i + 1].get_text(strip=True)
                                    if ciudad and len(ciudad) > 2:
                                        datos['city'] = ciudad
                                        break
            
            # Buscar provincia
            if 'provincia' in texto.lower() or 'jurisdiccion' in texto.lower():
                tables = soup.find_all('table')
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        for i, cell in enumerate(cells):
                            cell_text = cell.get_text(strip=True).lower()
                            if 'provincia' in cell_text or 'jurisdiccion' in cell_text:
                                if i + 1 < len(cells):
                                    prov = cells[i + 1].get_text(strip=True)
                                    if prov and len(prov) > 2:
                                        datos['provincia'] = prov
                                        break
            
            # Si tiene datos, retornarlos
            if datos:
                return datos
            
        except Exception as e:
            _logger.warning(f"Parse error: {e}")
        
        return None
    
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
        
        # Mapear nombres comunes
        mapas = {
            'santa fe': 'S',
            'buenos aires': 'B',
            'capital federal': 'CABA',
            'caba': 'CABA',
            'rosario': 'S',
            'mendoza': 'M',
            'tucuman': 'T',
            'cordoba': 'X',
            'entre rios': 'E',
            'corrientes': 'W',
            'misiones': 'N',
            'chaco': 'H',
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