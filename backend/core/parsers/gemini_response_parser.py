"""
Parser para respostas do Google Gemini AI.

Centraliza todo parsing de respostas do Gemini para evitar código duplicado
e facilitar evolução do formato de resposta.
"""
from typing import Optional, Dict, Any, List


def parse_classification_response(response_text: str) -> Optional[Dict[str, Any]]:
    """
    Faz parse da resposta de classificação do Gemini.
    
    Espera formato:
        CATEGORIA: [caminho completo]
        ID: [número]
    
    Args:
        response_text: Texto da resposta do Gemini
        
    Returns:
        Optional[Dict[str, Any]]: Dicionário com:
            - 'category_name': Nome completo da categoria
            - 'category_id': ID da categoria (opcional)
        Retorna None se não conseguir fazer parse
    """
    if not response_text:
        return None
    
    lines = response_text.split('\n')
    category_name = None
    category_id = None
    
    for line in lines:
        line_lower = line.lower()
        if 'categoria:' in line_lower:
            category_name = line.split(':', 1)[1].strip() if ':' in line else line.strip()
        elif line_lower.startswith('id:'):
            try:
                category_id = int(line.split(':', 1)[1].strip())
            except (ValueError, IndexError):
                pass
    
    if not category_name:
        return None
    
    result = {'category_name': category_name}
    if category_id:
        result['category_id'] = category_id
    
    return result


def parse_suggestion_response(response_text: str) -> Optional[str]:
    """
    Faz parse da resposta de sugestão de categoria do Gemini.
    
    Espera formato:
        SUGESTÃO: [caminho completo]
    
    Ou simplesmente o caminho completo em uma linha.
    
    Args:
        response_text: Texto da resposta do Gemini
        
    Returns:
        Optional[str]: Caminho completo sugerido ou None se não conseguir fazer parse
    """
    if not response_text:
        return None
    
    lines = response_text.split('\n')
    suggested_path = None
    
    # Primeiro tenta encontrar linha com "SUGESTÃO:"
    for line in lines:
        line_lower = line.lower()
        if 'sugestão:' in line_lower or 'sugestao:' in line_lower:
            suggested_path = line.split(':', 1)[1].strip() if ':' in line else line.strip()
            break
    
    # Se não encontrou, tenta pegar primeira linha não vazia que não seja um cabeçalho
    if not suggested_path:
        for line in lines:
            line = line.strip()
            if line and not line.lower().startswith('sugestão') and not line.lower().startswith('sugestao'):
                suggested_path = line
                break
    
    # Valida se começa com "TI" (padrão esperado)
    if suggested_path and suggested_path.startswith('TI'):
        return suggested_path
    
    return None


def parse_knowledge_base_response(response_text: str) -> str:
    """
    Faz parse da resposta de geração de artigo de Base de Conhecimento.
    
    Remove cabeçalhos opcionais e retorna o texto limpo.
    
    Args:
        response_text: Texto da resposta do Gemini
        
    Returns:
        str: Texto processado sem cabeçalhos
    """
    if not response_text:
        return ""
    
    lines = response_text.split('\n')
    # Remove primeira linha se for cabeçalho
    if lines and lines[0].lower().startswith(('artigo:', 'base de conhecimento:')):
        response_text = '\n'.join(lines[1:]).strip()
    
    return response_text

