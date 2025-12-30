"""
Cliente para integração com Zoho API.

Centraliza toda comunicação com a API do Zoho, incluindo:
- Gerenciamento de tokens OAuth (refresh automático)
- Reset de senha de usuários
- Validação de usuários
- Tratamento de erros e timeouts
"""
import logging
from typing import Optional, Dict, Any
import requests
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from ..models import ZohoToken
from ..exceptions import ZohoException

logger = logging.getLogger(__name__)


class ZohoClient:
    """
    Cliente para comunicação com Zoho API.
    
    Encapsula toda lógica de autenticação OAuth, renovação de tokens
    e chamadas à API do Zoho.
    """
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        refresh_token: Optional[str] = None
    ):
        """
        Inicializa o cliente Zoho.
        
        Args:
            client_id: Client ID do Zoho (ou obtém de settings)
            client_secret: Client Secret do Zoho (ou obtém de settings)
            refresh_token: Refresh token (ou obtém do banco)
        """
        self.client_id = client_id or getattr(settings, 'ZOHO_CLIENT_ID', None)
        self.client_secret = client_secret or getattr(settings, 'ZOHO_CLIENT_SECRET', None)
        self.refresh_token = refresh_token
        self._zoho_token = None
    
    def _get_zoho_token_from_db(self) -> Optional[ZohoToken]:
        """
        Busca o token Zoho no banco de dados.
        
        Se não existir no banco, tenta criar automaticamente do .env.
        
        Returns:
            Optional[ZohoToken]: Instância de ZohoToken ou None
        """
        if not self._zoho_token:
            self._zoho_token = ZohoToken.objects.first()
            
            # Se não existe no banco, tenta criar do .env (auto-criação)
            if not self._zoho_token:
                refresh_token = (
                    self.refresh_token or 
                    getattr(settings, 'ZOHO_REFRESH_TOKEN', None)
                )
                
                if refresh_token:
                    # Scope será atualizado na primeira renovação do token
                    # Por enquanto usa um valor padrão
                    self._zoho_token = ZohoToken.objects.create(
                        refresh_token=refresh_token,
                        scope='',  # Será preenchido na primeira renovação
                        api_domain=getattr(
                            settings, 
                            'ZOHO_API_DOMAIN', 
                            'https://www.zohoapis.com'
                        )
                    )
                    logger.info("ZohoToken criado automaticamente do .env")
        
        return self._zoho_token
    
    def _get_refresh_token(self) -> Optional[str]:
        """
        Obtém o refresh token (do banco ou parâmetro).
        
        Returns:
            Optional[str]: Refresh token ou None
        """
        if self.refresh_token:
            return self.refresh_token
        
        zoho_token = self._get_zoho_token_from_db()
        if zoho_token:
            return zoho_token.refresh_token
        
        return None
    
    def get_access_token(self) -> Optional[str]:
        """
        Obtém um access token válido, renovando se necessário.
        
        Este método gerencia automaticamente a renovação do access token
        usando o refresh token quando o access token expira.
        
        Returns:
            Optional[str]: Access token válido ou None se não conseguir obter
        """
        zoho_token = self._get_zoho_token_from_db()
        
        # Se não existe token no banco, precisa configurar primeiro
        if not zoho_token:
            logger.warning("ZohoToken não encontrado no banco. Configure o refresh_token primeiro.")
            return None
        
        # Se o access token ainda é válido, retorna ele
        if zoho_token.is_access_token_valid():
            return zoho_token.access_token
        
        # Se precisa renovar, faz refresh
        logger.info("Access token expirado. Renovando usando refresh token...")
        return self.refresh_access_token()
    
    def refresh_access_token(self) -> Optional[str]:
        """
        Renova o access token usando o refresh token.
        
        Este método faz a chamada OAuth para renovar o access token
        e salva no banco de dados.
        
        Returns:
            Optional[str]: Novo access token ou None se falhar
        """
        if not self.client_id or not self.client_secret:
            raise ValueError(
                "ZOHO_CLIENT_ID e ZOHO_CLIENT_SECRET devem estar configurados no .env"
            )
        
        refresh_token = self._get_refresh_token()
        if not refresh_token:
            raise ValueError(
                "Refresh token não encontrado. Configure ZOHO_REFRESH_TOKEN no .env ou no banco."
            )
        
        try:
            response = requests.post(
                "https://accounts.zoho.com/oauth/v2/token",
                data={
                    "grant_type": "refresh_token",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            # Atualiza ou cria token no banco
            zoho_token = self._get_zoho_token_from_db()
            if not zoho_token:
                zoho_token = ZohoToken(refresh_token=refresh_token)
            
            zoho_token.access_token = data.get('access_token')
            zoho_token.scope = data.get('scope', '')
            zoho_token.api_domain = data.get('api_domain', 'https://www.zohoapis.com')
            
            # Calcula expiração (expires_in está em segundos)
            expires_in = data.get('expires_in', 3600)
            zoho_token.expires_at = timezone.now() + timedelta(seconds=expires_in)
            
            zoho_token.save()
            
            logger.info("Access token renovado com sucesso")
            return zoho_token.access_token
            
        except requests.RequestException as e:
            error_type, error_message = self._parse_error(e, response if 'response' in locals() else None)
            logger.error(f"Erro ao renovar access token: {error_type} - {str(e)}")
            raise ZohoException(error_type, error_message) from e
    
    def get_organization_id(self) -> Optional[int]:
        """
        Obtém o ID da organização Zoho (zoid).
        
        Primeiro tenta obter do settings (.env), se não estiver configurado,
        tenta buscar via API (pode não funcionar para contas comuns).
        
        Returns:
            Optional[int]: ID da organização ou None se não conseguir obter
            
        Raises:
            ZohoException: Se houver erro na API do Zoho
        """
        # Tenta obter do settings primeiro (recomendado)
        zoid_from_settings = getattr(settings, 'ZOHO_ORGANIZATION_ID', None)
        if zoid_from_settings:
            try:
                zoid = int(zoid_from_settings)
                logger.info(f"Organization ID obtido do settings: {zoid}")
                self._organization_id = zoid  # Cache
                return zoid
            except (ValueError, TypeError):
                logger.warning(f"ZOHO_ORGANIZATION_ID inválido no settings: {zoid_from_settings}")
        
        # Se não está no settings, tenta buscar via API (pode falhar para contas comuns)
        access_token = self.get_access_token()
        if not access_token:
            logger.warning("Não foi possível obter access token para buscar organization ID")
            return None
        
        try:
            # API para obter detalhes da organização
            # GET https://mail.zoho.com/api/organization
            # NOTA: Contas comuns podem não ter acesso a este endpoint
            response = requests.get(
                "https://mail.zoho.com/api/organization",
                headers={
                    "Authorization": f"Zoho-oauthtoken {access_token}",
                    "Content-Type": "application/json"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                # A resposta pode ter diferentes estruturas, verificar documentação
                # Geralmente vem em data['data'][0]['zoid'] ou similar
                if 'data' in data and len(data['data']) > 0:
                    org_data = data['data'][0]
                    zoid = org_data.get('zoid') or org_data.get('id')
                    if zoid:
                        zoid_int = int(zoid)
                        logger.info(f"Organization ID obtido via API: {zoid_int}")
                        self._organization_id = zoid_int  # Cache
                        return zoid_int
                
                # Tentar estrutura alternativa
                if 'zoid' in data:
                    zoid_int = int(data['zoid'])
                    self._organization_id = zoid_int  # Cache
                    return zoid_int
            
            # Se falhou, retorna None (não é erro crítico se estiver no settings)
            logger.warning(f"Não foi possível obter organization ID via API (status {response.status_code})")
            logger.info("Configure ZOHO_ORGANIZATION_ID no .env para evitar buscar via API")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Erro ao buscar organization ID via API: {e}")
            logger.info("Configure ZOHO_ORGANIZATION_ID no .env para usar valor estático")
            return None
    
    def get_user_id_by_email(self, email: str, zoid: Optional[int] = None) -> Optional[int]:
        """
        Obtém o ID do usuário (zuid) pelo email.
        
        Args:
            email: Email do usuário
            zoid: ID da organização (se None, busca automaticamente)
            
        Returns:
            Optional[int]: ID do usuário ou None se não encontrar
            
        Raises:
            ZohoException: Se houver erro na API do Zoho
        """
        access_token = self.get_access_token()
        if not access_token:
            logger.warning("Não foi possível obter access token para buscar user ID")
            return None
        
        if not zoid:
            zoid = self.get_organization_id()
            if not zoid:
                logger.warning("Não foi possível obter organization ID")
                return None
        
        try:
            # API para buscar usuário por email na organização
            # GET https://mail.zoho.com/api/organization/{zoid}/accounts?emailId={email}
            response = requests.get(
                f"https://mail.zoho.com/api/organization/{zoid}/accounts",
                headers={
                    "Authorization": f"Zoho-oauthtoken {access_token}",
                    "Content-Type": "application/json"
                },
                params={"emailId": email},  # Filtrar por email diretamente
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                # Buscar usuário pelo email
                if 'data' in data:
                    for user in data['data']:
                        user_email = user.get('emailAddress') or user.get('email') or user.get('emailId')
                        if user_email and user_email.lower() == email.lower():
                            zuid = user.get('zuid') or user.get('id')
                            if zuid:
                                logger.info(f"User ID encontrado para {email}: {zuid}")
                                return int(zuid)
                
                logger.warning(f"Usuário com email {email} não encontrado na organização")
                return None
            
            if response.status_code == 401:
                raise ZohoException(
                    'unauthorized',
                    'Token de autenticação inválido ao buscar user ID.'
                )
            
            logger.warning(f"Resposta inesperada ao buscar user ID: {response.status_code}")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao buscar user ID: {e}")
            raise ZohoException(
                'api_error',
                f'Erro ao comunicar com API do Zoho para obter user ID: {str(e)}'
            )
    
    def reset_password(
        self,
        email: str,
        new_password: str
    ) -> bool:
        """
        Reseta a senha de um usuário no Zoho usando a API oficial.
        
        Requer scope: ZohoMail.organization.accounts.ALL ou ZohoMail.organization.accounts.UPDATE
        
        Endpoint: PUT https://mail.zoho.com/api/organization/{zoid}/accounts/{zuid}
        
        Args:
            email: Email do usuário no Zoho
            new_password: Nova senha
            
        Returns:
            bool: True se resetado com sucesso
            
        Raises:
            ZohoException: Se houver erro na API do Zoho
        """
        access_token = self.get_access_token()
        if not access_token:
            raise ZohoException(
                'no_access_token',
                'Não foi possível obter access token do Zoho. Verifique a configuração.'
            )
        
        # Obter organization ID (zoid)
        zoid = self.get_organization_id()
        if not zoid:
            raise ZohoException(
                'organization_not_found',
                'Não foi possível obter o ID da organização Zoho.'
            )
        
        # Obter user ID (zuid) pelo email
        zuid = self.get_user_id_by_email(email, zoid)
        if not zuid:
            raise ZohoException(
                'user_not_found',
                f'Usuário com email {email} não encontrado na organização Zoho.'
            )
        
        try:
            # PUT https://mail.zoho.com/api/organization/{zoid}/accounts/{zuid}
            response = requests.put(
                f"https://mail.zoho.com/api/organization/{zoid}/accounts/{zuid}",
                headers={
                    "Authorization": f"Zoho-oauthtoken {access_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "password": new_password,
                    "mode": "resetPassword"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Senha resetada com sucesso para {email}")
                return True
            
            # Tratar erros específicos
            if response.status_code == 400:
                error_msg = "Parâmetros inválidos na requisição de reset de senha."
                try:
                    error_data = response.json()
                    if 'message' in error_data:
                        error_msg = error_data['message']
                except:
                    pass
                raise ZohoException('invalid_request', error_msg)
            
            if response.status_code == 401:
                raise ZohoException(
                    'unauthorized',
                    'Token de autenticação inválido ou expirado. Verifique as credenciais.'
                )
            
            if response.status_code == 403:
                raise ZohoException(
                    'forbidden',
                    'Não tem permissão para resetar senhas. Verifique se o scope inclui ZohoMail.organization.accounts.ALL ou UPDATE.'
                )
            
            if response.status_code == 404:
                raise ZohoException(
                    'user_not_found',
                    f'Usuário não encontrado na organização Zoho.'
                )
            
            # Outros erros
            error_msg = f"Erro ao resetar senha: HTTP {response.status_code}"
            try:
                error_data = response.json()
                if 'message' in error_data:
                    error_msg = error_data['message']
            except:
                pass
            
            raise ZohoException('api_error', error_msg)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição de reset de senha: {e}")
            raise ZohoException(
                'api_error',
                f'Erro ao comunicar com API do Zoho: {str(e)}'
            )
    
    def validate_user(self, email: str) -> bool:
        """
        Valida se um usuário existe no Zoho.
        
        Args:
            email: Email do usuário
            
        Returns:
            bool: True se usuário existe, False caso contrário
        """
        try:
            zuid = self.get_user_id_by_email(email)
            return zuid is not None
        except ZohoException:
            return False
    
    def _parse_error(
        self,
        exception: Exception,
        response: Optional[requests.Response] = None
    ) -> tuple[str, str]:
        """
        Analisa exceções da API do Zoho e retorna informações específicas.
        
        Args:
            exception: Exceção capturada
            response: Response do requests (se disponível)
            
        Returns:
            Tuple[str, str]: (tipo_erro, mensagem_amigavel)
        """
        error_str = str(exception)
        error_lower = error_str.lower()
        
        # Se temos response, analisa status code
        if response is not None:
            status_code = response.status_code
            
            if status_code == 401:
                return 'invalid_token', 'Token do Zoho inválido ou expirado. Verifique a configuração.'
            
            if status_code == 403:
                return 'insufficient_permissions', 'Token do Zoho não tem permissões suficientes.'
            
            if status_code == 404:
                return 'user_not_found', 'Usuário não encontrado no Zoho.'
            
            if status_code == 429:
                return 'rate_limit_exceeded', 'Limite de requisições do Zoho excedido. Tente novamente mais tarde.'
            
            if status_code >= 500:
                return 'service_unavailable', 'Serviço do Zoho indisponível. Tente novamente mais tarde.'
        
        # Análise por texto do erro
        if 'refresh_token' in error_lower or 'invalid_grant' in error_lower:
            return 'invalid_refresh_token', 'Refresh token do Zoho inválido. É necessário gerar um novo code.'
        
        if 'access_token' in error_lower or 'unauthorized' in error_lower:
            return 'invalid_token', 'Token do Zoho inválido. Verifique a configuração.'
        
        if 'timeout' in error_lower:
            return 'timeout', 'Timeout ao comunicar com a API do Zoho. Tente novamente.'
        
        return 'unknown', f'Erro ao comunicar com a API do Zoho: {error_str}'

