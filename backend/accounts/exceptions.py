"""
Exceções customizadas para o app accounts (SSPR).

Centraliza exceções relacionadas a integrações externas e erros de negócio.
"""


class ZohoException(Exception):
    """
    Exceção base para erros do serviço Zoho.
    
    Attributes:
        error_type: Tipo do erro ('invalid_token', 'api_error', etc)
        message: Mensagem amigável do erro
    """
    
    def __init__(self, error_type: str, message: str):
        self.error_type = error_type
        self.message = message
        super().__init__(message)


class SMSException(Exception):
    """
    Exceção base para erros do serviço SMS (Twilio).
    
    Attributes:
        error_type: Tipo do erro ('authentication_error', 'invalid_phone', etc)
        message: Mensagem amigável do erro
    """
    
    def __init__(self, error_type: str, message: str):
        self.error_type = error_type
        self.message = message
        super().__init__(message)


