"""
Exceções customizadas para o projeto.

Centraliza exceções relacionadas a integrações externas e erros de negócio.
"""


class GeminiException(Exception):
    """
    Exceção base para erros do serviço Gemini.
    
    Attributes:
        error_type: Tipo do erro ('api_key_invalid', 'quota_exceeded', etc.)
        message: Mensagem amigável do erro
    """
    
    def __init__(self, error_type: str, message: str):
        self.error_type = error_type
        self.message = message
        super().__init__(message)


class GlpiApiException(Exception):
    """
    Exceção para erros na API do GLPI.
    
    Attributes:
        message: Mensagem descritiva do erro
    """
    
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class CategoryNotFoundException(Exception):
    """
    Exceção quando categoria não é encontrada.
    
    Attributes:
        path: Caminho da categoria que não foi encontrado
    """
    
    def __init__(self, path: str):
        self.path = path
        super().__init__(f"Categoria não encontrada: {path}")

