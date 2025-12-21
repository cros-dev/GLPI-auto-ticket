"""
Constantes e configurações do sistema.

Centraliza todas as constantes usadas em múltiplos módulos para facilitar
manutenção e evitar duplicação.
"""

# Sistemas conhecidos para detecção em tickets
SYSTEMS = [
    'anews', 'arion', 'glpi', 'ad', 'active directory', 'outlook', 'excel', 
    'word', 'teams', 'sharepoint', 'sap', 'erp', 'crm', 'bi', 'power bi'
]

# Palavras-chave relacionadas a eventos/montagem de setup
EVENT_KEYWORDS = [
    'transmissão', 'transmissao', 'vídeo conferência', 'video conferencia', 
    'evento', 'premiação', 'premiacao', 'montagem', 'setup', 'apoio', 
    'cerimônia', 'cerimonia', 'auditório', 'auditorio'
]

# Categorias genéricas que devem ser evitadas
GENERIC_CATEGORIES = [
    'periféricos', 'outros', 'outros acessos', 'outros equipamentos', 
    'solicitação geral', 'problema geral', 'problema geral de sistema',
    'equipamentos', 'hardware', 'software', 'sistemas', 'acesso'
]

# Tipos válidos de artigos de Base de Conhecimento
VALID_ARTICLE_TYPES = ['conceitual', 'operacional', 'troubleshooting']

