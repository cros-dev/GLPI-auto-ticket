"""
Parser para erros da API Twilio SMS.

Centraliza análise de exceções do Twilio para evitar código duplicado
e facilitar evolução do tratamento de erros.
"""
from typing import Tuple


def parse_sms_error(exception: Exception) -> Tuple[str, str]:
    """
    Analisa exceções do Twilio e retorna informações específicas.
    
    Args:
        exception: Exceção capturada
        
    Returns:
        Tuple[str, str]: (tipo_erro, mensagem_amigavel)
    """
    error_str = str(exception)
    error_lower = error_str.lower()
    
    if 'authentication' in error_lower or 'unauthorized' in error_lower:
        return 'authentication_error', 'Credenciais do Twilio inválidas. Verifique Account SID e Auth Token.'
    
    if 'invalid' in error_lower and 'phone' in error_lower:
        return 'invalid_phone', 'Número de telefone inválido. Verifique o formato (ex: +5511999999999).'
    
    if 'insufficient' in error_lower or 'balance' in error_lower:
        return 'insufficient_balance', 'Saldo insuficiente na conta Twilio.'
    
    if 'timeout' in error_lower:
        return 'timeout', 'Timeout ao comunicar com Twilio. Tente novamente.'
    
    return 'sms_error', f'Erro ao enviar SMS: {error_str}'

