"""
Utilitários para processamento de conteúdo HTML e Markdown.

Este módulo contém funções auxiliares para limpeza e formatação de conteúdo.
"""
import re
import markdown
from django.utils.html import strip_tags


def clean_html_content(html_content):
    """
    Limpa HTML, remove imagens (assinaturas) e retorna apenas o texto puro.
    
    Aplica a mesma lógica usada no admin para exibir conteúdo limpo.
    Processa o conteúdo HTML removendo tags, imagens e espaços extras,
    mantendo apenas o texto formatado com quebras de linha.
    
    Args:
        html_content (str): Conteúdo HTML a ser limpo
        
    Returns:
        str: Texto limpo sem HTML, imagens e espaços extras
    """
    if not html_content:
        return ""
    
    text = html_content
    
    # Remove imagens (assinaturas de email, etc)
    text = re.sub(r'<img[^>]*>', '', text)
    
    # Converte tags de bloco em quebras de linha
    text = text.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
    text = text.replace('</div>', '\n').replace('</p>', '\n')
    
    # Remove todas as tags HTML restantes
    text = strip_tags(text)
    
    # Remove espaços extras e quebras de linha duplicadas
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = text.strip()
    
    return text


def markdown_to_html(markdown_content: str) -> str:
    """
    Converte Markdown para HTML com extensões customizadas.
    
    Suporta:
    - Markdown padrão (negrito, itálico, listas, títulos, etc.)
    - Extensão customizada: ==texto== → <span class="highlight">texto</span>
    - Extensão customizada: [Inserir print da tela ...] → <span class="print-instruction">...</span>
    
    Args:
        markdown_content: Texto em Markdown
        
    Returns:
        str: HTML convertido com extensões customizadas aplicadas
    """
    if not markdown_content:
        return ""
    
    # Usa placeholders temporários únicos que não são interpretados pelo Markdown
    # Usa caracteres especiais que não são processados pelo markdown
    import uuid
    placeholders = {}
    
    # Protege ==texto== (highlight) antes da conversão Markdown
    def highlight_replacer(match):
        placeholder = f"<!--HIGHLIGHT_{uuid.uuid4().hex[:12]}-->"
        placeholders[placeholder] = f'<span class="highlight">{match.group(1)}</span>'
        return placeholder
    
    # Protege [Inserir print da tela ...] antes da conversão Markdown
    def print_replacer(match):
        placeholder = f"<!--PRINT_{uuid.uuid4().hex[:12]}-->"
        placeholders[placeholder] = f'<span class="print-instruction">Inserir print da tela {match.group(1)}</span>'
        return placeholder
    
    # Substitui extensões customizadas por placeholders
    protected_content = re.sub(r'==([^=]+)==', highlight_replacer, markdown_content)
    protected_content = re.sub(r'\[Inserir print da tela ([^\]]+)\]', print_replacer, protected_content)
    
    # Converte Markdown padrão para HTML
    md = markdown.Markdown(extensions=['extra', 'nl2br'])
    html = md.convert(protected_content)
    
    # Restaura extensões customizadas dos placeholders
    # Os comentários HTML são preservados pelo markdown, então podemos substituí-los
    for placeholder, replacement in placeholders.items():
        html = html.replace(placeholder, replacement)
    
    return html

