"""
Parser para erros da API Zoho.

Centraliza análise de exceções e respostas de erro do Zoho para evitar código duplicado
e facilitar evolução do tratamento de erros.
"""
from typing import Optional, Tuple, Dict, Any
import requests


def extract_error_message(error_data: Dict[str, Any]) -> Optional[str]:
    """
    Extrai mensagem de erro do payload da API Zoho.
    
    Tenta extrair de diferentes formatos:
    - data.moreInfo (informação adicional, ex: "Password has previously appeared in a data breach")
    - message
    - status.description
    - error.message ou error (string)
    
    Args:
        error_data: Dicionário com dados de erro da API
        
    Returns:
        Optional[str]: Mensagem de erro extraída ou None
    """
    if not error_data or not isinstance(error_data, dict):
        return None
    
    if 'data' in error_data and isinstance(error_data['data'], dict):
        if 'moreInfo' in error_data['data']:
            return str(error_data['data']['moreInfo'])
    
    if 'message' in error_data:
        return str(error_data['message'])
    
    if 'status' in error_data and isinstance(error_data['status'], dict):
        if 'description' in error_data['status']:
            return str(error_data['status']['description'])
    
    if 'error' in error_data:
        if isinstance(error_data['error'], dict) and 'message' in error_data['error']:
            return str(error_data['error']['message'])
        elif isinstance(error_data['error'], str):
            return error_data['error']
    
    return None


def parse_zoho_error(
    exception: Exception,
    response: Optional[requests.Response] = None
) -> Tuple[str, str]:
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
        
        if status_code == 500:
            return 'server_error', 'Erro interno do servidor Zoho. Verifique os parâmetros da requisição (ex: senha pode não atender aos requisitos) ou tente novamente mais tarde.'
        
        if status_code >= 500:
            return 'service_unavailable', 'Serviço do Zoho indisponível. Tente novamente mais tarde.'
        
        if status_code == 400:
            return 'invalid_request', 'Parâmetros inválidos na requisição. Verifique os dados enviados.'
    
    if 'refresh_token' in error_lower or 'invalid_grant' in error_lower:
        return 'invalid_refresh_token', 'Refresh token do Zoho inválido. É necessário gerar um novo code.'
    
    if 'access_token' in error_lower or 'unauthorized' in error_lower:
        return 'invalid_token', 'Token do Zoho inválido. Verifique a configuração.'
    
    if 'timeout' in error_lower:
        return 'timeout', 'Timeout ao comunicar com a API do Zoho. Tente novamente.'
    
    return 'unknown', f'Erro ao comunicar com a API do Zoho: {error_str}'


