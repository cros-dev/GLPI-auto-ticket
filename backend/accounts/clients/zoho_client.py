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
from ..parsers.zoho_error_parser import parse_zoho_error, extract_error_message

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
        Se existir mas for diferente do .env, atualiza com o valor do .env (fonte da verdade).
        
        Returns:
            Optional[ZohoToken]: Instância de ZohoToken ou None
        """
        if not self._zoho_token:
            self._zoho_token = ZohoToken.objects.first()
            
            env_refresh_token = (
                self.refresh_token or 
                getattr(settings, 'ZOHO_REFRESH_TOKEN', None)
            )
            
            if not self._zoho_token:
                if env_refresh_token:
                    self._zoho_token = ZohoToken.objects.create(
                        refresh_token=env_refresh_token,
                        scope='',
                        api_domain=getattr(
                            settings, 
                            'ZOHO_API_DOMAIN', 
                            'https://www.zohoapis.com'
                        )
                    )
                    logger.info("ZohoToken criado automaticamente do .env")
            elif env_refresh_token and self._zoho_token.refresh_token != env_refresh_token:
                logger.info("Refresh token no banco diferente do .env. Atualizando com valor do .env (fonte da verdade)")
                self._zoho_token.refresh_token = env_refresh_token
                self._zoho_token.access_token = None
                self._zoho_token.expires_at = None
                self._zoho_token.save()
        
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
        
        if not zoho_token:
            logger.warning("ZohoToken não encontrado no banco. Configure o refresh_token primeiro.")
            return None
        
        if zoho_token.is_access_token_valid():
            return zoho_token.access_token
        
        logger.info("Access token expirado. Renovando usando refresh token...")
        new_token = self.refresh_access_token()
        
        if not new_token:
            logger.error("Falha ao renovar access token")
            return None
        
        self._zoho_token = None
        zoho_token = self._get_zoho_token_from_db()
        
        if zoho_token and zoho_token.access_token:
            return zoho_token.access_token
        
        return new_token
    
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
            
            try:
                data = response.json()
            except Exception as e:
                logger.error(f"Erro ao parsear JSON da resposta: {e}")
                raise ZohoException(
                    'api_error',
                    f'Resposta da API não é um JSON válido: {response.text[:200]}'
                )
            
            if 'error' in data:
                error_type = data.get('error', 'unknown_error')
                error_description = data.get('error_description', '')
                
                if error_type == 'invalid_code':
                    logger.error("Refresh token inválido ou expirado")
                    raise ZohoException(
                        'invalid_refresh_token',
                        'Refresh token inválido ou expirado. Gere um novo refresh token em https://api-console.zoho.com/'
                    )
                else:
                    logger.error(f"Erro na resposta da API: {error_type} - {error_description}")
                    raise ZohoException(
                        'api_error',
                        f'Erro ao renovar token: {error_type} - {error_description}'
                    )
            
            if response.status_code != 200:
                logger.error(f"Erro ao renovar token: HTTP {response.status_code}")
                raise ZohoException(
                    'api_error',
                    f'Erro ao renovar token: HTTP {response.status_code} - {response.text[:200]}'
                )
            
            zoho_token = self._get_zoho_token_from_db()
            if not zoho_token:
                zoho_token = ZohoToken(refresh_token=refresh_token)
            
            access_token = data.get('access_token')
            if not access_token:
                logger.error(f"Resposta da API não contém access_token. Chaves: {list(data.keys())}")
                raise ZohoException(
                    'api_error',
                    f'Resposta da API não contém access_token. Resposta: {data}'
                )
            
            zoho_token.access_token = access_token
            zoho_token.scope = data.get('scope', '')
            zoho_token.api_domain = data.get('api_domain', 'https://www.zohoapis.com')
            expires_in = data.get('expires_in', 3600)
            zoho_token.expires_at = timezone.now() + timedelta(seconds=expires_in)
            zoho_token.save()
            
            self._zoho_token = zoho_token
            
            logger.info("Access token renovado com sucesso")
            return access_token
            
        except requests.RequestException as e:
            error_type, error_message = parse_zoho_error(e, response if 'response' in locals() else None)
            logger.error(f"Erro ao renovar access token: {error_type} - {str(e)}")
            raise ZohoException(error_type, error_message) from e
    
    def _get_organization_id(self) -> Optional[int]:
        """
        Obtém o ID da organização Zoho (zoid) do settings.
        
        Returns:
            Optional[int]: ID da organização ou None se não estiver configurado
        """
        zoid_from_settings = getattr(settings, 'ZOHO_ORGANIZATION_ID', None)
        if zoid_from_settings:
            try:
                return int(zoid_from_settings)
            except (ValueError, TypeError):
                logger.warning(f"ZOHO_ORGANIZATION_ID inválido no settings: {zoid_from_settings}")
        return None
    
    def get_user_by_email(
        self,
        email: str,
        zoid: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Obtém os dados completos do usuário pelo email.
        
        Faz uma requisição direta para o endpoint específico do usuário,
        retornando o payload completo com todas as informações disponíveis.
        
        Args:
            email: Email do usuário no Zoho
            zoid: ID da organização (se None, busca automaticamente)
            
        Returns:
            Optional[Dict[str, Any]]: Dados completos do usuário ou None se não encontrar.
                Retorna o objeto 'data' do payload da API.
            
        Raises:
            ZohoException: Se houver erro na API do Zoho
        """
        access_token = self.get_access_token()
        if not access_token:
            logger.warning("Não foi possível obter access token para buscar usuário")
            return None
        
        if not zoid:
            zoid = self._get_organization_id()
            if not zoid:
                logger.warning("ZOHO_ORGANIZATION_ID não configurado no .env")
                return None
        
        try:
            response = requests.get(
                f"https://mail.zoho.com/api/organization/{zoid}/accounts/{email}",
                headers={
                    "Authorization": f"Zoho-oauthtoken {access_token}",
                    "Content-Type": "application/json"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and data['data']:
                    user_data = data['data']
                    logger.info(f"Usuário encontrado para {email}: {user_data.get('zuid', 'N/A')}")
                    return user_data
                
                logger.warning(f"Resposta da API não contém dados do usuário para {email}")
                return None
            
            if response.status_code == 401:
                raise ZohoException(
                    'unauthorized',
                    'Token de autenticação inválido ao buscar usuário.'
                )
            
            if response.status_code == 404:
                logger.info(f"Usuário com email {email} não encontrado na organização")
                return None
            
            if response.status_code == 403:
                raise ZohoException(
                    'forbidden',
                    'Não tem permissão para buscar usuários. Verifique os scopes do token.'
                )
            
            error_msg = f"Erro ao buscar usuário: HTTP {response.status_code}"
            try:
                error_data = response.json()
                extracted_message = extract_error_message(error_data)
                if extracted_message:
                    error_msg = extracted_message
            except:
                pass
            
            logger.warning(f"Resposta inesperada ao buscar usuário: {response.status_code} - {error_msg}")
            raise ZohoException('api_error', error_msg)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao buscar usuário: {e}")
            raise ZohoException(
                'api_error',
                f'Erro ao comunicar com API do Zoho para obter dados do usuário: {str(e)}'
            )
    
    def get_user_id_by_email(self, email: str, zoid: Optional[int] = None) -> Optional[int]:
        """
        Obtém o ID do usuário (zuid) pelo email.
        
        Utiliza o método get_user_by_email() internamente para obter
        apenas o zuid do payload completo.
        
        Args:
            email: Email do usuário
            zoid: ID da organização (se None, busca automaticamente)
            
        Returns:
            Optional[int]: ID do usuário (zuid) ou None se não encontrar
            
        Raises:
            ZohoException: Se houver erro na API do Zoho
        """
        user_data = self.get_user_by_email(email, zoid)
        if not user_data:
            return None
        
        zuid = user_data.get('zuid') or user_data.get('id')
        if zuid:
            return int(zuid)
        
        logger.warning(f"Payload do usuário não contém zuid para {email}")
        return None
    
    def get_user_phone_by_email(
        self,
        email: str,
        zoid: Optional[int] = None
    ) -> Optional[str]:
        """
        Obtém o número de telefone do usuário pelo email.
        
        Utiliza o método get_user_by_email() internamente para obter
        o telefone do payload completo.
        
        Args:
            email: Email do usuário
            zoid: ID da organização (se None, busca automaticamente)
            
        Returns:
            Optional[str]: Número de telefone ou None se não encontrar
            
        Raises:
            ZohoException: Se houver erro na API do Zoho
        """
        user_data = self.get_user_by_email(email, zoid)
        if not user_data:
            return None
        
        phone_number = (
            user_data.get('mobileNumber') or
            user_data.get('phoneNumber') or
            user_data.get('phoneNumer')
        )
        
        return phone_number
    
    def reset_password(
        self,
        email: str,
        new_password: str
    ) -> bool:
        """
        Reseta a senha de um usuário no Zoho usando a API oficial.
        
        Requer scope: ZohoMail.organization.accounts.ALL ou ZohoMail.organization.accounts.UPDATE
        
        Endpoint: PUT https://mail.zoho.com/api/organization/{zoid}/accounts/{zuid}
        
        O método busca automaticamente o zuid do usuário pelo email.
        
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
        
        zoid = self._get_organization_id()
        if not zoid:
            raise ZohoException(
                'organization_not_found',
                'ZOHO_ORGANIZATION_ID não configurado no .env'
            )
        
        zuid = self.get_user_id_by_email(email)
        if not zuid:
            raise ZohoException(
                'user_not_found',
                f'Usuário com email {email} não encontrado na organização Zoho.'
            )
        
        try:
            response = requests.put(
                f"https://mail.zoho.com/api/organization/{zoid}/accounts/{zuid}",
                headers={
                    "Authorization": f"Zoho-oauthtoken {access_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "zuid": zuid,
                    "password": new_password,
                    "mode": "resetPassword"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Senha resetada com sucesso para {email}")
                return True
            
            if response.status_code in [400, 401, 403, 404, 429] or response.status_code >= 500:
                error_type, error_message = parse_zoho_error(
                    Exception(f"HTTP {response.status_code}"),
                    response
                )
                
                try:
                    error_data = response.json()
                    extracted_message = extract_error_message(error_data)
                    if extracted_message:
                        error_message = extracted_message
                except:
                    pass
                
                raise ZohoException(error_type, error_message)
            
            error_type, error_message = parse_zoho_error(
                Exception(f"HTTP {response.status_code}"),
                response
            )
            raise ZohoException(error_type, error_message)
            
        except ZohoException:
            raise
        except requests.exceptions.RequestException as e:
            error_type, error_message = parse_zoho_error(e, None)
            logger.error(f"Erro na requisição de reset de senha: {e}")
            raise ZohoException(error_type, error_message) from e
    
    def validate_user(self, email: str) -> bool:
        """
        Valida se um usuário existe no Zoho.
        
        Args:
            email: Email do usuário
            
        Returns:
            bool: True se usuário existe, False caso contrário
        """
        try:
            user_data = self.get_user_by_email(email)
            return user_data is not None
        except ZohoException:
            return False

