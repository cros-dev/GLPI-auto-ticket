"""
Cliente para integração com Google Gemini AI.

Centraliza toda comunicação com a API do Gemini, incluindo:
- Criação do cliente
- Chamadas à API
- Tratamento de erros
"""
import logging
from typing import Optional, Tuple
from django.conf import settings
from ..exceptions import GeminiException

logger = logging.getLogger(__name__)


class GeminiClient:
    """
    Cliente para comunicação com Google Gemini AI.
    
    Encapsula toda lógica de autenticação, chamadas e tratamento de erros.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializa o cliente Gemini.
        
        Args:
            api_key: Chave da API do Gemini. Se None, tenta obter de settings.
        """
        self.api_key = api_key or getattr(settings, 'GEMINI_API_KEY', None)
        self._client = None
    
    def get_client(self):
        """
        Cria e retorna o cliente do Google Gemini AI.
        
        Returns:
            Optional[genai.Client]: Cliente Gemini ou None se API key não estiver configurada
        """
        if not self.api_key:
            return None
        
        if self._client is None:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except ImportError:
                logger.warning("Biblioteca google-genai não instalada")
                return None
        
        return self._client
    
    def generate_content(self, prompt: str, model: str = "gemini-2.5-flash") -> Optional[str]:
        """
        Faz chamada à API do Gemini e retorna a resposta processada.
        
        Args:
            prompt: Prompt a ser enviado
            model: Modelo a ser usado (padrão: gemini-2.5-flash)
            
        Returns:
            Optional[str]: Resposta processada ou None em caso de erro
        """
        client = self.get_client()
        if not client:
            return None
        
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt
            )
            return response.text.strip() if response.text else None
        except Exception as e:
            error_type, error_message = self._parse_error(e)
            logger.warning(f"Erro ao chamar API do Gemini: {error_type} - {str(e)}")
            raise GeminiException(error_type, error_message) from e
    
    def _parse_error(self, exception: Exception) -> Tuple[str, str]:
        """
        Analisa exceções da API do Gemini e retorna informações específicas sobre o erro.
        
        Args:
            exception: Exceção capturada
            
        Returns:
            Tuple[str, str]: (tipo_erro, mensagem_amigavel)
            tipos possíveis: 'api_key_invalid', 'api_key_expired', 'quota_exceeded', 
                             'service_unavailable', 'unknown'
        """
        error_str = str(exception)
        error_lower = error_str.lower()
        
        if '503' in error_str or 'unavailable' in error_lower or 'overloaded' in error_lower:
            return 'service_unavailable', 'O modelo do Gemini está sobrecarregado. Tente novamente em alguns instantes.'
        
        if 'api key expired' in error_lower or 'api_key_expired' in error_lower or 'expired' in error_lower:
            if 'api key' in error_lower or 'api_key' in error_lower:
                return 'api_key_expired', 'A chave da API do Gemini está expirada. Por favor, renove a chave de API.'
        
        if 'api key' in error_lower or 'api_key' in error_lower:
            if 'invalid' in error_lower or 'api_key_invalid' in error_lower:
                return 'api_key_invalid', 'A chave da API do Gemini é inválida. Verifique a configuração da chave.'
        
        if 'quota' in error_lower or 'rate limit' in error_lower:
            return 'quota_exceeded', 'Limite de quota da API do Gemini foi excedido. Tente novamente mais tarde.'
        
        if 'authentication' in error_lower or 'unauthorized' in error_lower:
            return 'api_key_invalid', 'Erro de autenticação com a API do Gemini. Verifique a chave de API.'
        
        if 'permission' in error_lower or 'forbidden' in error_lower:
            return 'api_key_invalid', 'A chave da API do Gemini não tem permissões suficientes.'
        
        if 'invalid_argument' in error_lower or 'invalid argument' in error_lower:
            if 'api key' in error_lower or 'api_key' in error_lower:
                if 'expired' in error_lower:
                    return 'api_key_expired', 'A chave da API do Gemini está expirada. Por favor, renove a chave de API.'
                return 'api_key_invalid', 'A chave da API do Gemini é inválida. Verifique a configuração da chave.'
        
        return 'unknown', f'Erro ao comunicar com a API do Gemini: {error_str}'

