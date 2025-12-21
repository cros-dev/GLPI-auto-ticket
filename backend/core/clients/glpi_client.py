"""
Cliente para integração com GLPI Legacy API.

Centraliza toda comunicação com a API Legacy do GLPI, incluindo:
- Autenticação (initSession)
- Busca de categorias ITIL
- Tratamento de erros e timeouts
"""
import logging
from typing import List, Dict, Optional
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class GlpiLegacyClient:
    """
    Cliente para comunicação com GLPI Legacy API.
    
    Encapsula toda lógica de autenticação, chamadas e tratamento de erros.
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        app_token: Optional[str] = None
    ):
        """
        Inicializa o cliente GLPI Legacy.
        
        Args:
            base_url: URL base da API (ex: "http://172.16.0.180:81")
            user: Usuário para autenticação
            password: Senha para autenticação
            app_token: Token da aplicação (opcional)
        """
        self.base_url = self._normalize_base_url(
            base_url or getattr(settings, 'GLPI_LEGACY_API_URL', None)
        )
        self.user = user or getattr(settings, 'GLPI_LEGACY_API_USER', None)
        self.password = password or getattr(settings, 'GLPI_LEGACY_API_PASSWORD', None)
        self.app_token = app_token or getattr(settings, 'GLPI_LEGACY_APP_TOKEN', None)
        self._session_token = None
    
    def _normalize_base_url(self, url: Optional[str]) -> Optional[str]:
        """
        Normaliza a URL base da API GLPI.
        
        Args:
            url: URL bruta do .env
            
        Returns:
            Optional[str]: URL formatada (ex: "http://172.16.0.180:81/api.php/v1") 
                          ou None se não estiver configurada
        """
        if not url:
            return None
        
        url = url.rstrip('/')
        if url.endswith('/api.php/v1'):
            return url
        return f"{url}/api.php/v1"
    
    def get_session_token(self) -> str:
        """
        Obtém token de sessão da API Legacy do GLPI.
        
        Returns:
            str: Session token para autenticação
            
        Raises:
            ValueError: Se configuração estiver incompleta
            requests.RequestException: Se houver erro na autenticação
        """
        if not self.base_url or not self.user or not self.password:
            raise ValueError(
                "Configuração da API Legacy do GLPI incompleta. "
                "Verifique GLPI_LEGACY_API_URL, GLPI_LEGACY_API_USER e "
                "GLPI_LEGACY_API_PASSWORD no .env"
            )
        
        headers = {'Content-Type': 'application/json'}
        if self.app_token:
            headers['App-Token'] = self.app_token
        
        response = requests.post(
            f"{self.base_url}/initSession",
            json={
                "login": self.user,
                "password": self.password
            },
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        if 'session_token' not in data:
            raise ValueError("Token de sessão não retornado pela API do GLPI")
        
        self._session_token = data['session_token']
        return self._session_token
    
    def fetch_categories(self) -> List[Dict]:
        """
        Busca todas as categorias ITIL da API Legacy do GLPI.
        
        Implementa paginação automática para buscar todas as categorias.
        
        Returns:
            list: Lista de dicionários contendo:
                - glpi_id: ID da categoria no GLPI
                - full_path: Caminho completo (ex.: "TI > Requisição > Acesso")
                - parts: Lista de partes do caminho
                - parent_path: Caminho do pai (ex.: "TI > Requisição")
            
        Raises:
            ValueError: Se configuração estiver incompleta
            requests.RequestException: Se houver erro na requisição
        """
        if not self.base_url:
            raise ValueError("GLPI_LEGACY_API_URL não configurado")
        
        if not self._session_token:
            self.get_session_token()
        
        headers = {
            'Content-Type': 'application/json',
            'Session-Token': self._session_token
        }
        if self.app_token:
            headers['App-Token'] = self.app_token
        
        all_categories = []
        range_start = 0
        range_limit = 50
        
        while True:
            response = requests.get(
                f"{self.base_url}/ITILCategory/?expand_dropdowns=true&range={range_start}-{range_start + range_limit - 1}",
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            categories_batch = response.json()
            if not categories_batch or not isinstance(categories_batch, list):
                break
            
            all_categories.extend(categories_batch)
            
            # Verifica se há mais páginas usando Content-Range header
            content_range = response.headers.get('Content-Range', '')
            if content_range:
                range_info = content_range.split('/')
                if len(range_info) == 2:
                    current_range = range_info[0]
                    total_count = int(range_info[1])
                    if '-' in current_range:
                        current_end = int(current_range.split('-')[1])
                        if current_end >= total_count - 1:
                            break
            
            range_start += range_limit
            
            # Se retornou menos que o limite, chegou ao fim
            if len(categories_batch) < range_limit:
                break
        
        # Processa e formata as categorias
        processed_categories = []
        seen_ids = set()
        
        for category in all_categories:
            glpi_id = category.get('id')
            if not glpi_id or glpi_id in seen_ids:
                continue
            
            seen_ids.add(glpi_id)
            completename = category.get('completename', '')
            
            if not completename:
                name = category.get('name', '')
                if name:
                    completename = name
            
            if not completename:
                continue
            
            parts = [p.strip() for p in completename.split('>') if p.strip()]
            if not parts:
                continue
            
            processed_categories.append({
                "full_path": ' > '.join(parts),
                "parts": parts,
                "parent_path": ' > '.join(parts[:-1]) if len(parts) > 1 else '',
                "glpi_id": glpi_id,
            })
        
        return processed_categories

