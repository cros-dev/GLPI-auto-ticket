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


class OtpException(Exception):
    """
    Exceção para erros relacionados a OTP.
    
    Attributes:
        error_type: Tipo do erro ('expired', 'invalid', 'exceeded_attempts')
        message: Mensagem amigável do erro
    """
    
    def __init__(self, error_type: str, message: str):
        self.error_type = error_type
        self.message = message
        super().__init__(message)


class PasswordResetException(Exception):
    """
    Exceção para erros no processo de reset de senha.
    
    Attributes:
        error_type: Tipo do erro ('user_not_found', 'system_unavailable', etc)
        message: Mensagem amigável do erro
    """
    
    def __init__(self, error_type: str, message: str):
        self.error_type = error_type
        self.message = message
        super().__init__(message)

