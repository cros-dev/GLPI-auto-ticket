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

# Palavras-chave relacionadas a certificado digital
CERTIFICATE_KEYWORDS = [
    'certificado digital', 'certificado', 'e-cpf', 'e-cnpj', 'e-cpf', 'e-cnpj',
    'token', 'atualizar certificado', 'renovar certificado', 'receita federal',
    'site da receita', 'acesso ao site da receita', 'certificado expirado'
]

# Palavras-chave que indicam que o ticket é sobre instalação/uso de software
SOFTWARE_INSTALLATION_KEYWORDS = [
    'instalar', 'instalação', 'instalacao', 'instalar software', 'instalar programa',
    'instalar aplicativo', 'instalar app', 'adobe', 'office', 'photoshop', 'illustrator',
    'instalar microsoft', 'instalar windows', 'instalar excel', 'instalar word',
    'instalar powerpoint', 'licença', 'licenciamento', 'ativar software'
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

# Choices para tipos de artigos de Base de Conhecimento
ARTICLE_TYPE_CHOICES = [
    ('conceitual', 'Conceitual'),
    ('operacional', 'Operacional'),
    ('troubleshooting', 'Troubleshooting'),
]

# Choices para origem de sugestões/artigos
SUGGESTION_SOURCE_CHOICES = [
    ('ticket', 'Ticket Real'),
    ('preview', 'Preview Manual'),
]

# Choices para origem de artigos de Base de Conhecimento
# Por enquanto apenas 'preview', mas pode ser expandido no futuro
KNOWLEDGE_BASE_ARTICLE_SOURCE_CHOICES = [
    ('preview', 'Preview Manual'),
]

# Choices para status de sugestões de categoria
CATEGORY_SUGGESTION_STATUS_CHOICES = [
    ('pending', 'Pendente'),
    ('approved', 'Aprovada'),
    ('rejected', 'Rejeitada'),
]

# Choices para rating de pesquisas de satisfação
SATISFACTION_SURVEY_RATING_CHOICES = [
    (1, '1 - Muito Insatisfeito'),
    (2, '2 - Insatisfeito'),
    (3, '3 - Neutro'),
    (4, '4 - Satisfeito'),
    (5, '5 - Muito Satisfeito'),
]

