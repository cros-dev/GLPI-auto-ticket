""" 
Serviços auxiliares para processamento de tickets. 
 
Este módulo contém funções para classificação automática de tickets usando 
Google Gemini AI. 
""" 
import logging 
from typing import Optional, Dict 
from django.conf import settings 
from .models import GlpiCategory 
 
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
        logger.debug("GEMINI_API_KEY não configurada, classificação será ignorada")
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
        logger.warning("Biblioteca google-genai não instalada, classificação será ignorada")
        return None
    except Exception as e:
        logger.warning(f"Erro ao classificar com Gemini AI: {str(e)}, classificação será ignorada")
        return None


def classify_ticket(
    title: str,
    content: str
) -> Optional[Dict[str, any]]:
    """
    Classifica um ticket usando Google Gemini AI.
    
    Args:
        title (str): Título do ticket
        content (str): Conteúdo/descrição do ticket
        
    Returns:
        Optional[Dict[str, any]]: Dicionário com:
            - 'suggested_category_name': Nome completo da categoria sugerida (caminho hierárquico)
            - 'suggested_category_id': ID GLPI da categoria
            - 'confidence': 'high' (quando IA responde)
        Retorna None se nenhuma classificação for possível.
    """
    return classify_ticket_with_gemini(title, content)

