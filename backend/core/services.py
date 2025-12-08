"""
Serviços auxiliares para processamento de tickets.

Este módulo contém funções para classificação automática de tickets usando
Google Gemini AI. 
"""
import logging
from typing import Optional, Dict, Tuple
from django.conf import settings
from .models import GlpiCategory, CategorySuggestion, Ticket 

logger = logging.getLogger(__name__)


def _parse_gemini_error(exception: Exception) -> Tuple[str, str]:
    """
    Analisa exceções da API do Gemini e retorna informações específicas sobre o erro.
    
    Args:
        exception: Exceção capturada
        
    Returns:
        Tuple[str, str]: (tipo_erro, mensagem_amigavel)
        tipos possíveis: 'api_key_invalid', 'api_key_expired', 'quota_exceeded', 'unknown'
    """
    error_str = str(exception)
    error_lower = error_str.lower()
    
    if 'api key expired' in error_lower or 'api_key_expired' in error_lower or 'expired' in error_lower:
        if 'api key' in error_lower or 'api_key' in error_lower:
            return 'api_key_expired', 'A chave da API do Gemini está expirada. Por favor, renove a chave de API.'
    
    if 'api key' in error_lower or 'api_key' in error_lower:
        if 'invalid' in error_lower or 'api_key_invalid' in error_lower:
            return 'api_key_invalid', 'A chave da API do Gemini é inválida. Verifique a configuração da chave.'
    
    if 'quota' in error_lower or 'rate limit' in error_lower:
        return 'quota_exceeded', 'Limite de quota da API do Gemini foi excedido. Tente novamente mais tarde.'
    
    if 'authentication' in error_lower or 'unauthorized' in error_lower:
        return 'api_key_invalid', 'Erro de autenticação com a API do Gemini. Verifique a chave de API.'
    
    if 'permission' in error_lower or 'forbidden' in error_lower:
        return 'api_key_invalid', 'A chave da API do Gemini não tem permissões suficientes.'
    
    if 'invalid_argument' in error_lower or 'invalid argument' in error_lower:
        if 'api key' in error_lower or 'api_key' in error_lower:
            if 'expired' in error_lower:
                return 'api_key_expired', 'A chave da API do Gemini está expirada. Por favor, renove a chave de API.'
            return 'api_key_invalid', 'A chave da API do Gemini é inválida. Verifique a configuração da chave.'
    
    return 'unknown', f'Erro ao comunicar com a API do Gemini: {error_str}'

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
        if 'administrativo' in name:
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

Analise o seguinte ticket e classifique-o na categoria MAIS ESPECÍFICA e APROPRIADA da lista acima.

IMPORTANTE: 
- Só retorne uma categoria se ela se encaixar PERFEITAMENTE no contexto do ticket
- Prefira categorias mais específicas (com mais níveis) quando disponíveis
- Se a categoria mais próxima for muito genérica (ex: apenas "Periféricos" sem subcategoria), responda "Nenhuma" para que possamos criar uma categoria mais específica

Título: {title}
Conteúdo: {content}

Responda APENAS com o caminho completo da categoria (ex: "TI > Incidente > Equipamentos > Hardware > Computadores > Não Liga / Travando") e o ID entre parênteses (ex: "(84)"). 
Se não encontrar uma categoria adequada e específica, responda "Nenhuma".

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
        
        generic_categories = ['periféricos', 'outros', 'outros acessos', 'outros equipamentos', 
                             'solicitação geral', 'problema geral', 'equipamentos', 'hardware',
                             'software', 'sistemas', 'acesso']
        
        last_level = category_path[-1].lower() if category_path else ''
        
        if len(category_path) < 4 or last_level in generic_categories:
            logger.info(f"Categoria muito genérica encontrada ({len(category_path)} níveis, último: '{last_level}'): {' > '.join(category_path)}. Gerando sugestão mais específica.")
            return None
        
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
        return {'error': 'library_not_installed', 'message': 'Biblioteca google-genai não está instalada.'}
    except Exception as e:
        error_type, error_message = _parse_gemini_error(e)
        logger.warning(f"Erro ao classificar com Gemini AI: {error_type} - {str(e)}")
        return {'error': error_type, 'message': error_message}


def generate_category_suggestion(
    title: str,
    content: str,
    ticket_id: Optional[int] = None
) -> Optional[str]:
    """
    Gera uma sugestão de categoria quando a IA não encontra categoria exata.
    
    Usa o Gemini para sugerir uma nova categoria seguindo o padrão hierárquico
    (ex.: "TI > Requisição > Administrativo > Montagem de Setup > Transmissão/Vídeo Conferência").
    
    Args:
        title (str): Título do ticket
        content (str): Conteúdo/descrição do ticket
        ticket_id (Optional[int]): ID do ticket para vincular a sugestão
        
    Returns:
        Optional[str]: Caminho completo sugerido ou None se não conseguir gerar
    """
    api_key = getattr(settings, 'GEMINI_API_KEY', None)
    
    if not api_key:
        return None
    
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        
        prompt = f"""Você é um assistente especializado em classificação de tickets de suporte técnico.

Analise o seguinte ticket e sugira uma categoria hierárquica seguindo o padrão:
TI > [Incidente/Requisição] > [Área] > [Subárea] > [Categoria Específica]

Exemplos de padrões:
- TI > Requisição > Acesso > AD > Criação de Usuário / Conta
- TI > Incidente > Equipamentos > Hardware > Computadores > Não Liga / Travando
- TI > Requisição > Administrativo > Montagem de Setup > Transmissão/Vídeo Conferência

Título: {title}
Conteúdo: {content}

Sugira APENAS o caminho completo da categoria seguindo o padrão acima.
Se não conseguir determinar, responda "Nenhuma".

Formato da resposta:
SUGESTÃO: [caminho completo]"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        response_text = response.text.strip()
        
        if not response_text or "Nenhuma" in response_text.lower():
            return None
        
        lines = response_text.split('\n')
        suggested_path = None
        
        for line in lines:
            line_lower = line.lower()
            if 'sugestão:' in line_lower or 'sugestao:' in line_lower:
                suggested_path = line.split(':', 1)[1].strip() if ':' in line else line.strip()
                break
        
        if not suggested_path:
            for line in lines:
                line = line.strip()
                if line and not line.lower().startswith('sugestão') and not line.lower().startswith('sugestao'):
                    suggested_path = line
                    break
        
        if suggested_path and suggested_path.startswith('TI'):
            return suggested_path
        
        return None
        
    except ImportError:
        logger.warning("Biblioteca google-genai não instalada, geração de sugestão será ignorada")
        return {'error': 'library_not_installed', 'message': 'Biblioteca google-genai não está instalada.'}
    except Exception as e:
        error_type, error_message = _parse_gemini_error(e)
        logger.warning(f"Erro ao gerar sugestão de categoria: {error_type} - {str(e)}")
        return {'error': error_type, 'message': error_message}


def save_category_suggestion(
    ticket_id: int,
    suggested_path: str,
    title: str,
    content: str
) -> Optional[CategorySuggestion]:
    """
    Salva uma sugestão de categoria para revisão manual.
    
    Args:
        ticket_id (int): ID do ticket
        suggested_path (str): Caminho completo sugerido
        title (str): Título do ticket
        content (str): Conteúdo do ticket
        
    Returns:
        Optional[CategorySuggestion]: Instância criada ou None se houver erro
    """
    try:
        ticket = Ticket.objects.get(id=ticket_id)
        
        existing = CategorySuggestion.objects.filter(
            ticket=ticket,
            status='pending'
        ).first()
        
        if existing:
            existing.suggested_path = suggested_path
            existing.ticket_title = title
            existing.ticket_content = content[:5000]
            existing.save()
            return existing
        
        suggestion = CategorySuggestion.objects.create(
            ticket=ticket,
            suggested_path=suggested_path,
            ticket_title=title,
            ticket_content=content[:5000],
            status='pending'
        )
        return suggestion
        
    except Ticket.DoesNotExist:
        logger.warning(f"Ticket {ticket_id} não encontrado para salvar sugestão")
        return None
    except Exception as e:
        logger.error(f"Erro ao salvar sugestão de categoria: {str(e)}")
        return None


def classify_ticket(
    title: str,
    content: str,
    ticket_id: Optional[int] = None
) -> Optional[Dict[str, any]]:
    """
    Classifica um ticket usando Google Gemini AI.
    
    Se não encontrar categoria exata, tenta gerar uma sugestão e salva para revisão manual.
    
    Args:
        title (str): Título do ticket
        content (str): Conteúdo/descrição do ticket
        ticket_id (Optional[int]): ID do ticket para vincular sugestões
        
    Returns:
        Optional[Dict[str, any]]: Dicionário com:
            - 'suggested_category_name': Nome completo da categoria sugerida (caminho hierárquico)
            - 'suggested_category_id': ID GLPI da categoria
            - 'confidence': 'high' (quando IA responde)
        Retorna None se nenhuma classificação for possível.
    """
    result = classify_ticket_with_gemini(title, content)
    
    if isinstance(result, dict) and 'error' in result:
        return result
    
    if not result and ticket_id:
        suggested_path = generate_category_suggestion(title, content, ticket_id)
        
        if isinstance(suggested_path, dict) and 'error' in suggested_path:
            return suggested_path
        
        if suggested_path and isinstance(suggested_path, str):
            save_category_suggestion(ticket_id, suggested_path, title, content)
            logger.info(f"Sugestão de categoria criada para ticket {ticket_id}: {suggested_path}")
    
    return result

