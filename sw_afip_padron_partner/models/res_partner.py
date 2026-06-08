# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo import _
import logging
import requests

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    # ============================================================
    # CAMPOS AFIP
    # ============================================================
    
    x_afip_cuit = fields.Char(
        string='AFIP CUIT',
        help='CUIT para consultar Padrón AFIP (sin guiones)',
    )
    
    x_estado_padron = fields.Char(
        string='Estado AFIP',
        readonly=True,
    )
    
    x_imp_iva_padron = fields.Char(
        string='IVA AFIP',
        readonly=True,
    )
    
    x_imp_ganancias_padron = fields.Char(
        string='Ganancias AFIP',
        readonly=True,
    )
    
    x_last_update_padron = fields.Date(
        string='Última Actualización AFIP',
        readonly=True,
    )
    
    # ============================================================
    # BOTÓN PRINCIPAL
    # ============================================================
    
    def action_update_from_padron_afip(self):
        """
        Consulta y actualiza desde Padrón AFIP
        """
        self.ensure_one()
        
        # Validar CUIT
        if not self.x_afip_cuit:
            raise UserError(_('Debe ingresar el CUIT primero'))
        
        try:
            # Limpiar CUIT (solo números)
            cuit = ''.join(filter(str.isdigit, str(self.x_afip_cuit)))
        except:
            raise UserError(_('CUIT inválido'))
        
        if len(cuit) != 11:
            raise UserError(_('El CUIT debe tener 11 dígitos sin guiones'))
        
        # Consultar AFIP
        datos_afip = self._consultar_afip_api(cuit)
        
        if not datos_afip:
            raise UserError(_(
                'No se pudo obtener datos de AFIP.\n\n'
                'Para usar este servicio necesita:\n'
                '1. Instalar pyafipws en el servidor: pip install pyafipws\n'
                '2. Tener certificado AFIP configurado'
            ))
        
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
    # CONSULTA API (SIN pyafipws)
    # ============================================================
    
    def _consultar_afip_api(self, cuit):
        """
        Intenta consultar AFIP sin pyafipws
        """
        # Intentar método 1: Solicitar constancia de AFIP
        datos = self._consultar_constancia_afip(cuit)
        if datos:
            return datos
        
        # Intentar método 2: API alternativa
        datos = self._consultar_api_externa(cuit)
        if datos:
            return datos
        
        # Intentar método 3: Web scraping
        datos = self._consultar_web_afip(cuit)
        if datos:
            return datos
        
        return None
    
    def _consultar_constancia_afip(self, cuit):
        """
        Método 1: Obtener constancia de AFIP
        """
        try:
            import requests
            
            # URL de constancia de AFIP
            url = f"https://www.afip.gob.ar/genericos/constanciaInscripcion.asp?denominacion=&cuit={cuit}&clase=contribuyente&subclase="
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
            }
            
            response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
            
            if response.status_code == 200:
                # Buscar datos en el HTML
                html = response.text
                
                # Extraer denomination
                if 'denominacion' in html.lower():
                    # Buscar en el HTML
                    datos = self._extraer_datos_html(html)
                    if datos:
                        return datos
                        
        except Exception as e:
            _logger.warning(f'Méthodo constancia falló: {e}')
        
        return None
    
    def _consultar_api_externa(self, cuit):
        """
        Método 2: Usar API externa (si hay disponible)
        """
        # Esta es una opción de ejemplo
        # NO hay APIs públicas gratuitas confiables para AFIP
        # Puedes implementar una propia si la tienes
        
        # Intentar con algunos servicios conocidos
        apis_a_probar = []
        
        for api_url in apis_a_probar:
            try:
                response = requests.get(f"{api_url}/{cuit}", timeout=5)
                if response.status_code == 200:
                    return response.json()
            except:
                continue
        
        return None
    
    def _consultar_web_afip(self, cuit):
        """
        Método 3: Web scraping de padronesar.afip.gob.ar
        """
        try:
            import requests
            from bs4 import BeautifulSoup
            
            # Ir a la página del padrón
            url = "https://padronesar.afip.gob.ar/PadronConsumidorActivo/"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
                'Accept-Language': 'es-AR,es;q=0.9,en;q=0.8',
            }
            
            session = requests.Session()
            
            # Primera request para obtener cookies
            response = session.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                # Buscar formulario o datos
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Buscar campo CUIT
                cuit_input = soup.find('input', {'name': 'cuit'})
                
                if cuit_input:
                    # Enviar datos del CUIT
                    data = {'cuit': cuit}
                    response = session.post(url, data=data, headers=headers, timeout=15)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        datos = self._extraer_datos_html(soup.text)
                        if datos:
                            return datos
                            
        except Exception as e:
            _logger.warning(f'Web scraping falló: {e}')
        
        return None
    
    def _extraer_datos_html(self, html):
        """
        Extrae datos del HTML de AFIP
        """
        try:
            from bs4 import BeautifulSoup
            
            soup = BeautifulSoup(html, 'html.parser')
            texto = soup.get_text()
            
            # Buscar datos comunes
            datos = {}
            
            # Denominación/Nombre
            if 'denominacion' intexto.lower():
                lines = texto.split('\n')
                for i, line in enumerate(lines):
                    if 'denominacion' in line.lower():
                        if i + 1 < len(lines):
                            datos['name'] = lines[i + 1].strip()
                            break
            
            # Estado
            if 'estado' in texto.lower():
                if 'activo' in texto.lower():
                    datos['estado'] = 'Activo'
                elif 'baja' in texto.lower() or 'cancelado' in texto.lower():
                    datos['estado'] = 'Inactivo'
            
            # IVA
            if 'iva' in texto.lower():
                if 'inscripto' in texto.lower():
                    datos['imp_iva'] = 'Activo'
                elif 'exento' in texto.lower():
                    datos['imp_iva'] = 'Exento'
                else:
                    datos['imp_iva'] = 'No Inscripto'
            
            # Si no encontró nada, retornar datos genéricos
            if not datos.get('name'):
                return None
            
            return datos
            
        except Exception as e:
            _logger.warning(f'Error extrayendo datos: {e}')
        
        return None
    
    def _buscar_provincia(self, nombre):
        """Busca provincia por nombre"""
        if not nombre:
            return False
        
        # Mapeo de nombres
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
        }
        
        nombre_lower = nombre.lower().strip()
        
        # Buscar por nombre
        state = self.env['res.country.state'].search([
            ('name', 'ilike', nombre),
            ('country_id.code', '=', 'AR'),
        ], limit=1)
        
        if state:
            return state.id
        
        # Buscar por código
        if nombre_lower in mapas:
            state = self.env['res.country.state'].search([
                ('code', '=', mapas[nombre_lower]),
                ('country_id.code', '=', 'AR'),
            ], limit=1)
            if state:
                return state.id
        
        return False