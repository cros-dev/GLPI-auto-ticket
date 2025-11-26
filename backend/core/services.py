"""
Serviços auxiliares para processamento de tickets.

Este módulo contém funções para classificação automática de tickets usando
Google Gemini AI (quando disponível) ou classificação simples baseada em palavras-chave como fallback.
"""
import logging
from typing import Optional, Dict
from django.conf import settings
from .models import GlpiCategory
from .keywords import KEYWORD_MAPPING

logger = logging.getLogger(__name__)


def get_category_path(category):
    """
    Retorna o caminho completo da hierarquia de categorias como lista.
    
    Args:
        category: Instância de GlpiCategory
        
    Returns:
        list: Lista de nomes de categorias do nível raiz até a categoria atual
        Exemplo: ['Requisição', 'Acesso', 'AD', 'Criação de Usuário / Conta']
    """
    if hasattr(category, 'full_path') and category.full_path:
        return [part.strip() for part in category.full_path.split('>') if part.strip()]
    
    path = []
    current = category
    while current:
        path.insert(0, current.name)
        current = current.parent
    return path


def determine_ticket_type(path_parts):
    """
    Determina se uma categoria pertence a Incidente ou Requisição.
    
    Args:
        path_parts (list[str]): Caminho da categoria
    
    Returns:
        tuple: (ticket_type, ticket_type_label)
               ticket_type -> 1 (incidente), 2 (requisição), None (indefinido)
    """
    if not path_parts:
        return None, None
    
    normalized = [part.strip().lower() for part in path_parts if part.strip()]
    for name in normalized:
        if 'incidente' in name:
            return 1, 'incidente'
        if 'requisição' in name or 'requisicao' in name:
            return 2, 'requisição'
    return None, None


def classify_ticket_simple(
    title: str,
    content: str
) -> Optional[Dict[str, any]]:
    """
    Classificação simples baseada em palavras-chave.
    
    Utiliza o caminho hierárquico completo das categorias para encontrar
    a melhor correspondência com base em palavras-chave no título e conteúdo.
    
    Args:
        title (str): Título do ticket
        content (str): Conteúdo/descrição do ticket
        
    Returns:
        Optional[Dict[str, any]]: Dicionário com:
            - 'suggested_category_name': Nome completo da categoria sugerida (caminho hierárquico)
            - 'suggested_category_id': ID GLPI da categoria
            - 'confidence': 'medium' ou 'high'
        Retorna None se nenhuma correspondência for encontrada.
    """
    text = f"{title} {content}".lower()
    
    is_incident = any(word in text for word in [
        'problema', 'erro', 'falha', 'não funciona', 'não está funcionando',
        'não imprime', 'não liga', 'travando', 'lento', 'sem conexão',
        'indisponível', 'inacessível', 'bloqueado', 'tela azul', 'crash',
        'travamento', 'não abre', 'não responde', 'sem resposta'
    ])
    
    is_request = any(word in text for word in [
        'solicitar', 'solicitação', 'pedido', 'preciso', 'precisamos',
        'quero', 'gostaria', 'instalar', 'instalação', 'novo', 'nova',
        'criar', 'criação', 'adicionar', 'adicionar', 'configurar'
    ])
    
    software_indicators = ['office', 'word', 'excel', 'powerpoint', 'outlook', 'software', 'programa', 'aplicativo', 'app']
    has_software_indicator = any(indicator in text for indicator in software_indicators)
    
    categories = GlpiCategory.objects.all()
    best_match = None
    best_match_path = None
    best_match_parts = None
    max_score = 0
    
    for category in categories:
        path = get_category_path(category)
        full_path = ' > '.join(path)
        full_path_lower = full_path.lower()
        
        score = 0
        
        path_first_level = path[0].lower() if path else ''
        type_match = False
        
        if path_first_level == 'incidente' and is_incident:
            score += 30
            type_match = True
        elif path_first_level == 'requisição' and is_request:
            score += 30
            type_match = True
        elif path_first_level == 'incidente' and is_request:
            score -= 20
        elif path_first_level == 'requisição' and is_incident:
            score -= 20
        
        category_name_lower = category.name.lower()
        words = text.split()
        
        if category_name_lower in text:
            score += 20
        
        if category_name_lower in words:
            score += 15
        
        for keyword, synonyms, weight in KEYWORD_MAPPING:
            if keyword in full_path_lower:
                for synonym in synonyms:
                    if synonym in text:
                        depth_bonus = len(path) * 3
                        score += weight + depth_bonus
                        
                        if has_software_indicator and 'software' in full_path_lower:
                            score += 15
                        
                        break
        
        if has_software_indicator and 'hardware' in full_path_lower and 'software' not in full_path_lower:
            score -= 30
        
        if score == 0 or (score < 10 and not type_match):
            for path_part in path:
                path_part_lower = path_part.lower()
                if path_part_lower in text and len(path_part_lower) > 4:
                    if has_software_indicator and path_part_lower in ['hardware', 'computadores', 'computador']:
                        score -= 5
                    else:
                        score += 1
        
        if score > 0:
            score += len(path) * 2
        
        if score > max_score:
            max_score = score
            best_match = category
            best_match_path = full_path
            best_match_parts = path
    
    if best_match and max_score > 0:
        confidence = 'high' if max_score >= 10 else 'medium'
        
        ticket_type, ticket_type_label = determine_ticket_type(best_match_parts or [])
        
        return {
            'suggested_category_name': best_match_path,
            'suggested_category_id': best_match.glpi_id,
            'confidence': confidence,
            'classification_method': 'keywords',
            'ticket_type': ticket_type,
            'ticket_type_label': ticket_type_label
        }
    
    return None


def get_categories_for_ai():
    """
    Retorna lista formatada de categorias para uso em prompts de IA.
    
    Returns:
        str: String formatada com todas as categorias hierárquicas
    """
    categories = GlpiCategory.objects.all()
    category_list = []
    
    for category in categories:
        path = get_category_path(category)
        full_path = ' > '.join(path)
        category_list.append(f"- {full_path} (ID: {category.glpi_id})")
    
    return '\n'.join(category_list)


def classify_ticket_with_gemini(
    title: str,
    content: str
) -> Optional[Dict[str, any]]:
    """
    Classificação usando Google Gemini AI.
    
    Utiliza a API do Google Gemini para classificar o ticket baseado no título
    e conteúdo, comparando com as categorias GLPI disponíveis.
    
    Args:
        title (str): Título do ticket
        content (str): Conteúdo/descrição do ticket
        
    Returns:
        Optional[Dict[str, any]]: Dicionário com:
            - 'suggested_category_name': Nome completo da categoria sugerida (caminho hierárquico)
            - 'suggested_category_id': ID GLPI da categoria
            - 'confidence': 'high' ou 'medium'
        Retorna None se houver erro ou se a API não estiver configurada.
    """
    api_key = getattr(settings, 'GEMINI_API_KEY', None)
    
    if not api_key:
        logger.debug("GEMINI_API_KEY não configurada, usando fallback para palavras-chave")
        return None
    
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        
        categories_text = get_categories_for_ai()
        
        prompt = f"""Você é um assistente especializado em classificação de tickets de suporte técnico.

Categorias disponíveis (formato: Nível 1 > Nível 2 > Nível 3 > ...):
{categories_text}

Analise o seguinte ticket e classifique-o na categoria mais apropriada da lista acima.

Título: {title}
Conteúdo: {content}

Responda APENAS com o caminho completo da categoria (ex: "Incidente > Equipamentos > Hardware > Computadores > Não Liga / Travando") e o ID entre parênteses (ex: "(84)"). 
Se não encontrar uma categoria adequada, responda "Nenhuma".

Formato da resposta:
CATEGORIA: [caminho completo]
ID: [número do ID]"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        response_text = response.text.strip()
        
        if not response_text or "Nenhuma" in response_text.lower():
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
        
        if category_id:
            category = GlpiCategory.objects.filter(glpi_id=category_id).first()
        else:
            category = None
        
        if not category:
            categories = GlpiCategory.objects.all()
            for cat in categories:
                path = get_category_path(cat)
                full_path = ' > '.join(path)
                if full_path.lower() == category_name.lower():
                    category = cat
                    category_id = cat.glpi_id
                    break
        
        if not category:
            return None
        
        category_path = get_category_path(category)
        ticket_type, ticket_type_label = determine_ticket_type(category_path)
        
        return {
            'suggested_category_name': ' > '.join(category_path),
            'suggested_category_id': category.glpi_id,
            'confidence': 'high',
            'classification_method': 'ai',
            'ticket_type': ticket_type,
            'ticket_type_label': ticket_type_label
        }
        
    except ImportError:
        logger.warning("Biblioteca google-genai não instalada, usando fallback para palavras-chave")
        return None
    except Exception as e:
        logger.warning(f"Erro ao classificar com Gemini AI: {str(e)}, usando fallback para palavras-chave")
        return None


def classify_ticket(
    title: str,
    content: str
) -> Optional[Dict[str, any]]:
    """
    Classifica um ticket tentando usar Gemini AI primeiro, com fallback para classificação simples.
    
    Tenta classificar usando Google Gemini AI. Se falhar ou não estiver configurado,
    usa classificação baseada em palavras-chave como fallback.
    
    Args:
        title (str): Título do ticket
        content (str): Conteúdo/descrição do ticket
        
    Returns:
        Optional[Dict[str, any]]: Dicionário com:
            - 'suggested_category_name': Nome completo da categoria sugerida (caminho hierárquico)
            - 'suggested_category_id': ID GLPI da categoria
            - 'confidence': 'high' ou 'medium'
        Retorna None se nenhuma classificação for possível.
    """
    result = classify_ticket_with_gemini(title, content)
    
    if result:
        return result
    
    return classify_ticket_simple(title, content)

