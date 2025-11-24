"""
Utilitários para processamento de conteúdo HTML.

Este módulo contém funções auxiliares para limpeza e formatação de conteúdo.
"""
import re
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

