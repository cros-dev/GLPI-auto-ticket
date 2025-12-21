"""
Serviços auxiliares para processamento de tickets.

Este módulo contém funções para classificação automática de tickets usando
Google Gemini AI. 
"""
import logging
from typing import Optional, Dict, Tuple, List, Any
from django.utils import timezone
from .models import GlpiCategory, CategorySuggestion, Ticket, SatisfactionSurvey
from .prompts import get_classification_prompt, get_suggestion_prompt, get_knowledge_base_prompt
from .constants import SYSTEMS, EVENT_KEYWORDS, GENERIC_CATEGORIES, VALID_ARTICLE_TYPES
from .clients.gemini_client import GeminiClient
from .exceptions import GeminiException
from .parsers.gemini_response_parser import (
    parse_classification_response,
    parse_suggestion_response,
    parse_knowledge_base_response
)

logger = logging.getLogger(__name__)


def get_category_path(category) -> List[str]:
    """
    Retorna o caminho completo da hierarquia de categorias como lista.
    
    Args:
        category: Instância de GlpiCategory
        
    Returns:
        List[str]: Lista de nomes de categorias do nível raiz até a categoria atual.
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


def find_category_by_path(path: str) -> Optional[GlpiCategory]:
    """
    Busca uma categoria existente no banco percorrendo o caminho informado.
    
    Args:
        path: Caminho hierárquico (ex.: "TI > Requisição")
        
    Returns:
        Optional[GlpiCategory]: Categoria encontrada ou None se não existir
    """
    if not path:
        return None
    
    parts = [p.strip() for p in path.split('>') if p.strip()]
    parent = None
    for part in parts:
        parent = GlpiCategory.objects.filter(name=part, parent=parent).first()
        if not parent:
            return None
    return parent


def process_categories_sync(categories, source_name="fonte"):
    """
    Processa lista de categorias e cria/atualiza no banco.
    Remove categorias que não estão na fonte para manter o Django como espelho do GLPI.
    
    Args:
        categories: Lista de dicionários contendo:
            - glpi_id: ID da categoria no GLPI
            - full_path: Caminho completo (ex.: "TI > Requisição > Acesso")
            - parts: Lista de partes do caminho
            - parent_path: Caminho do pai (ex.: "TI > Requisição")
        source_name: Nome da fonte (para logs/mensagens de erro)
        
    Returns:
        dict: Estatísticas de criação/atualização/remoção
    """
    created_count = 0
    updated_count = 0
    cache_by_path = {}
    
    source_glpi_ids = {entry["glpi_id"] for entry in categories}
    
    sorted_categories = sorted(categories, key=lambda item: len(item["parts"]))
    
    for entry in sorted_categories:
        category_name = entry["parts"][-1]
        parent_path = entry["parent_path"]
        parent = None
        
        if parent_path:
            parent = cache_by_path.get(parent_path)
            if not parent:
                parent = find_category_by_path(parent_path)
            if not parent:
                parent_segments = [p.strip() for p in parent_path.split('>') if p.strip()]
                if len(parent_segments) > 1:
                    logger.warning(f"Categoria pai '{parent_path}' não encontrada na {source_name}. Criando sem pai.")
        
        obj, created = GlpiCategory.objects.update_or_create(
            glpi_id=entry["glpi_id"],
            defaults={
                "name": category_name,
                "parent": parent,
                "full_path": entry["full_path"]
            }
        )
        
        cache_by_path[entry["full_path"]] = obj
        if created:
            created_count += 1
        else:
            updated_count += 1
    
    deleted_count = 0
    if source_glpi_ids:
        categories_to_delete = GlpiCategory.objects.exclude(glpi_id__in=source_glpi_ids)
        deleted_count = categories_to_delete.count()
        categories_to_delete.delete()

    return {
        "created": created_count,
        "updated": updated_count,
        "deleted": deleted_count,
        "total": GlpiCategory.objects.count()
    }


def determine_ticket_type(path_parts: List[str]) -> Tuple[Optional[int], Optional[str]]:
    """
    Determina se uma categoria pertence a Incidente ou Requisição.
    
    Args:
        path_parts: Caminho da categoria (lista de strings)
        
    Returns:
        Tuple[Optional[int], Optional[str]]: (ticket_type, ticket_type_label)
            - ticket_type: 1 (incidente), 2 (requisição), None (indefinido)
            - ticket_type_label: 'incidente', 'requisição', ou None
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


def get_categories_for_ai() -> str:
    """
    Retorna lista formatada de categorias para uso em prompts de IA.
    
    Returns:
        str: String formatada com todas as categorias hierárquicas, uma por linha,
             no formato "- Categoria > Subcategoria (ID: 123)"
    """
    categories = GlpiCategory.objects.all()
    category_list = []
    
    for category in categories:
        path = get_category_path(category)
        full_path = ' > '.join(path)
        category_list.append(f"- {full_path} (ID: {category.glpi_id})")
    
    return '\n'.join(category_list)


def _is_generic_category(category_path: List[str]) -> bool:
    """
    Verifica se uma categoria é muito genérica.
    
    Args:
        category_path: Lista com o caminho da categoria
        
    Returns:
        bool: True se a categoria for genérica, False caso contrário
    """
    if len(category_path) < 5:
        return True
    
    last_level = category_path[-1].lower() if category_path else ''
    return last_level in [cat.lower() for cat in GENERIC_CATEGORIES]


def _mentions_system(ticket_text: str) -> bool:
    """
    Verifica se o texto do ticket menciona algum sistema conhecido.
    
    Args:
        ticket_text: Texto do ticket em minúsculas
        
    Returns:
        bool: True se menciona sistema, False caso contrário
    """
    return any(system in ticket_text for system in SYSTEMS)


def _find_similar_category(
    ticket_text: str,
    search_terms: List[str],
    min_levels: int = 5,
    path_filters: Optional[List[str]] = None
) -> Optional[str]:
    """
    Busca categoria existente que contém termos de busca específicos.
    
    Args:
        ticket_text: Texto do ticket em minúsculas
        search_terms: Lista de termos para buscar nas categorias
        min_levels: Número mínimo de níveis da categoria
        path_filters: Lista de filtros opcionais para aplicar no caminho da categoria
        
    Returns:
        Optional[str]: Caminho completo da categoria encontrada ou None
    """
    for term in search_terms:
        if term in ticket_text:
            categories = GlpiCategory.objects.filter(full_path__icontains=term)
            for cat in categories:
                path = get_category_path(cat)
                if len(path) >= min_levels:
                    full_path = ' > '.join(path)
                    
                    if path_filters:
                        full_path_lower = full_path.lower()
                        if not any(filter_term in full_path_lower for filter_term in path_filters):
                            continue
                    
                    logger.info(f"Categoria similar encontrada: {full_path}")
                    return full_path
    return None


def _find_similar_category_by_systems(ticket_text: str, min_levels: int = 5) -> Optional[str]:
    """
    Busca categoria existente que menciona sistemas do ticket.
    
    Args:
        ticket_text: Texto do ticket em minúsculas
        min_levels: Número mínimo de níveis da categoria
        
    Returns:
        Optional[str]: Caminho completo da categoria encontrada ou None
    """
    filters = ['problema de acesso', 'indisponibilidade de sistema', 'falha em processo', 'requisição']
    return _find_similar_category(ticket_text, SYSTEMS, min_levels, filters)


def _find_similar_category_by_events(ticket_text: str, min_levels: int = 5) -> Optional[str]:
    """
    Busca categoria existente relacionada a eventos/montagem de setup.
    
    Args:
        ticket_text: Texto do ticket em minúsculas
        min_levels: Número mínimo de níveis da categoria
        
    Returns:
        Optional[str]: Caminho completo da categoria encontrada ou None
    """
    filters = ['montagem de setup', 'transmissão', 'video conferência']
    return _find_similar_category(ticket_text, EVENT_KEYWORDS, min_levels, filters)


def _get_similar_categories_for_reference(ticket_text: str) -> List[str]:
    """
    Busca categorias similares para usar como referência em prompts.
    
    Args:
        ticket_text: Texto do ticket em minúsculas
        
    Returns:
        List[str]: Lista de caminhos completos de categorias similares
    """
    similar_categories = []
    
    for system in SYSTEMS:
        if system in ticket_text:
            for cat in GlpiCategory.objects.filter(full_path__icontains=system):
                path = get_category_path(cat)
                if len(path) >= 4:
                    similar_categories.append(' > '.join(path))
    
    for keyword in EVENT_KEYWORDS:
        if keyword in ticket_text:
            for cat in GlpiCategory.objects.filter(full_path__icontains=keyword):
                path = get_category_path(cat)
                if len(path) >= 4:
                    similar_categories.append(' > '.join(path))
    
    return similar_categories[:10]


# =========================================================
# CLASSIFICAÇÃO COM IA
# =========================================================

def classify_ticket_with_gemini(
    title: str,
    content: str
) -> Optional[Dict[str, Any]]:
    """
    Classificação usando Google Gemini AI.
    
    Utiliza a API do Google Gemini para classificar o ticket baseado no título
    e conteúdo, comparando com as categorias GLPI disponíveis.
    
    Args:
        title: Título do ticket
        content: Conteúdo/descrição do ticket
        
    Returns:
        Optional[Dict[str, Any]]: Dicionário com:
            - 'suggested_category_name': Nome completo da categoria sugerida (caminho hierárquico)
            - 'suggested_category_id': ID GLPI da categoria
            - 'confidence': 'high' ou 'medium'
        Retorna None se houver erro ou se a API não estiver configurada.
        Retorna dict com 'error' e 'message' em caso de erro na API.
    """
    client = GeminiClient()
    if not client.get_client():
        logger.debug("GEMINI_API_KEY não configurada, classificação será ignorada")
        return None
    
    try:
        categories_text = get_categories_for_ai()
        prompt = get_classification_prompt(categories_text, title, content)
        response_text = client.generate_content(prompt)
        
        if not response_text or "Nenhuma" in response_text.lower():
            return None
        
        # Usa parser centralizado
        parsed = parse_classification_response(response_text)
        if not parsed:
            return None
        
        category_name = parsed.get('category_name')
        category_id = parsed.get('category_id')
        
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
        
        if _is_generic_category(category_path):
            logger.info(f"Categoria muito genérica encontrada ({len(category_path)} níveis): {' > '.join(category_path)}. Gerando sugestão mais específica.")
            return None
        
        ticket_text = f"{title} {content}".lower()
        mentions_system = _mentions_system(ticket_text)
        
        if len(category_path) == 4 and mentions_system:
            last_level = category_path[-1].lower()
            if last_level in ['problema de acesso', 'problemas de acesso', 'indisponibilidade de sistema']:
                logger.info(f"Categoria '{last_level}' encontrada mas ticket menciona sistema específico. Gerando sugestão mais específica com sistema.")
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
        
    except GeminiException as e:
        logger.warning(f"Erro ao classificar com Gemini AI: {e.error_type} - {e.message}")
        return {'error': e.error_type, 'message': e.message}
    except Exception as e:
        logger.warning(f"Erro inesperado ao classificar com Gemini AI: {str(e)}")
        return {'error': 'unknown', 'message': f'Erro ao comunicar com a API do Gemini: {str(e)}'}


def generate_category_suggestion(
    title: str,
    content: str,
    ticket_id: Optional[int] = None
) -> Optional[str]:
    """
    Gera uma sugestão de categoria quando a IA não encontra categoria exata.
    
    Usa o Gemini para sugerir uma nova categoria seguindo o padrão hierárquico
    (ex.: "TI > Requisição > Equipamentos > Hardware > Montagem de Setup > Transmissão/Vídeo Conferência").
    
    Antes de gerar, verifica se já existe uma categoria similar no banco para evitar duplicatas.
    
    Args:
        title: Título do ticket
        content: Conteúdo/descrição do ticket
        ticket_id: ID do ticket para vincular a sugestão (opcional)
        
    Returns:
        Optional[str]: Caminho completo sugerido ou None se não conseguir gerar
    """
    client = GeminiClient()
    if not client.get_client():
        return None
    
    ticket_text = f"{title} {content}".lower()
    
    similar_category = _find_similar_category_by_systems(ticket_text)
    if similar_category:
        return similar_category
    
    similar_category = _find_similar_category_by_events(ticket_text)
    if similar_category:
        return similar_category
    
    try:
        categories_text = get_categories_for_ai()
        similar_categories = _get_similar_categories_for_reference(ticket_text)
        prompt = get_suggestion_prompt(categories_text, similar_categories, title, content)
        response_text = client.generate_content(prompt)
        
        if not response_text or "Nenhuma" in response_text.lower():
            return None
        
        # Usa parser centralizado
        suggested_path = parse_suggestion_response(response_text)
        return suggested_path
        
    except GeminiException as e:
        logger.warning(f"Erro ao gerar sugestão de categoria: {e.error_type} - {e.message}")
        return None
    except Exception as e:
        logger.warning(f"Erro inesperado ao gerar sugestão de categoria: {str(e)}")
        return None


def save_category_suggestion(
    ticket_id: int,
    suggested_path: str,
    title: str,
    content: str
) -> Optional[CategorySuggestion]:
    """
    Salva uma sugestão de categoria para revisão manual.
    
    Args:
        ticket_id: ID do ticket
        suggested_path: Caminho completo sugerido
        title: Título do ticket
        content: Conteúdo do ticket
        
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
            existing.ticket_content = content
            existing.save()
            return existing
        
        suggestion = CategorySuggestion.objects.create(
            ticket=ticket,
            suggested_path=suggested_path,
            ticket_title=title,
            ticket_content=content,
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
) -> Optional[Dict[str, Any]]:
    """
    Classifica um ticket usando Google Gemini AI.
    
    Se não encontrar categoria exata, tenta gerar uma sugestão e salva para revisão manual.
    
    Args:
        title: Título do ticket
        content: Conteúdo/descrição do ticket
        ticket_id: ID do ticket para vincular sugestões (opcional)
        
    Returns:
        Optional[Dict[str, Any]]: Dicionário com:
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
        
        if suggested_path and isinstance(suggested_path, str):
            save_category_suggestion(ticket_id, suggested_path, title, content)
            logger.info(f"Sugestão de categoria criada para ticket {ticket_id}: {suggested_path}")
    
    return result


# =========================================================
# BASE DE CONHECIMENTO
# =========================================================

def _split_articles(text: str) -> list[Dict[str, str]]:
    """
    Separa múltiplos artigos de Base de Conhecimento em uma lista.
    
    Detecta o início de cada artigo pelo padrão "**Base de Conhecimento —".
    Cada artigo é retornado como um dicionário com 'content' contendo o texto completo.
    
    Args:
        text: Texto completo com potencialmente múltiplos artigos
        
    Returns:
        Lista de dicionários, cada um contendo:
        - 'content': Texto completo do artigo
    """
    if not text or not text.strip():
        return []
    
    articles = []
    lines = text.split('\n')
    current_article_lines = []
    
    for line in lines:
        # Detecta início de novo artigo pelo padrão "**Base de Conhecimento —"
        if line.strip().startswith('**Base de Conhecimento —'):
            # Se já temos um artigo em construção, salva ele
            if current_article_lines:
                article_text = '\n'.join(current_article_lines).strip()
                if article_text:
                    articles.append({'content': article_text})
                current_article_lines = []
        
        current_article_lines.append(line)
    
    # Adiciona o último artigo
    if current_article_lines:
        article_text = '\n'.join(current_article_lines).strip()
        if article_text:
            articles.append({'content': article_text})
    
    # Se não encontrou nenhum padrão de separação, retorna o texto como um único artigo
    if not articles:
        articles.append({'content': text.strip()})
    
    return articles


def generate_knowledge_base_article(
    article_type: str,
    category: str,
    context: str
) -> Optional[Dict[str, Any]]:
    """
    Gera um artigo de Base de Conhecimento usando Google Gemini AI.
    
    Args:
        article_type: Tipo do artigo ('conceitual', 'operacional' ou 'troubleshooting')
        category: Categoria da Base de Conhecimento.
                  Exemplo: "RTV > AM > TI > Suporte > Técnicos > Jornal / Switcher > Playout"
        context: Contexto do ambiente, sistemas, servidores, softwares envolvidos
        
    Returns:
        Optional[Dict[str, Any]]: Dicionário com:
            - 'articles': Lista de artigos (cada um com 'content')
            - 'article_type': Tipo do artigo
            - 'category': Categoria informada
        Retorna None se houver erro ou se a API não estiver configurada.
        Retorna dict com 'error' e 'message' em caso de erro na API.
        
        Nota: A resposta contém uma lista de artigos, pois a IA pode gerar múltiplos
        artigos (um para cada sistema/software identificado no contexto).
    """
    if article_type.lower() not in VALID_ARTICLE_TYPES:
        logger.warning(f"Tipo de artigo inválido: {article_type}. Tipos válidos: {VALID_ARTICLE_TYPES}")
        return {'error': 'invalid_article_type', 'message': f'Tipo de artigo inválido. Tipos válidos: {", ".join(VALID_ARTICLE_TYPES)}'}
    
    if not category or not category.strip():
        logger.warning("Categoria não informada para geração de artigo")
        return {'error': 'missing_category', 'message': 'Categoria da Base de Conhecimento é obrigatória'}
    
    if not context or not context.strip():
        logger.warning("Contexto não informado para geração de artigo")
        return {'error': 'missing_context', 'message': 'Contexto do ambiente é obrigatório'}
    
    client = GeminiClient()
    if not client.get_client():
        logger.debug("GEMINI_API_KEY não configurada, geração de artigo será ignorada")
        return None
    
    try:
        prompt = get_knowledge_base_prompt(article_type, category, context)
        response_text = client.generate_content(prompt)
        
        if not response_text:
            logger.warning("Resposta vazia da API do Gemini para geração de artigo")
            return {'error': 'empty_response', 'message': 'A API do Gemini retornou uma resposta vazia'}
        
        # Usa parser centralizado
        cleaned_text = parse_knowledge_base_response(response_text)
        
        # Separa múltiplos artigos se houver
        articles = _split_articles(cleaned_text)
        
        logger.info(f"Artigo(s) de Base de Conhecimento gerado(s) com sucesso. Tipo: {article_type}, Categoria: {category}, Total: {len(articles)}")
        
        return {
            'articles': articles,
            'article_type': article_type.lower(),
            'category': category.strip()
        }
        
    except GeminiException as e:
        logger.warning(f"Erro ao gerar artigo de Base de Conhecimento: {e.error_type} - {e.message}")
        return {'error': e.error_type, 'message': e.message}
    except Exception as e:
        logger.warning(f"Erro inesperado ao gerar artigo de Base de Conhecimento: {str(e)}")
        return {'error': 'unknown', 'message': f'Erro ao comunicar com a API do Gemini: {str(e)}'}


# =========================================================
# SERVIÇOS DE TICKET E SUGESTÕES
# =========================================================

def update_ticket_with_classification(
    ticket_id: int,
    classification_result: Dict[str, Any]
) -> bool:
    """
    Atualiza ticket com resultado da classificação.
    
    Args:
        ticket_id: ID do ticket
        classification_result: Resultado da classificação com categoria sugerida
        
    Returns:
        bool: True se atualizado com sucesso, False caso contrário
    """
    try:
        ticket = Ticket.objects.get(id=ticket_id)
        suggested_category = GlpiCategory.objects.filter(
            glpi_id=classification_result.get("suggested_category_id")
        ).first()
        
        if suggested_category:
            ticket.category = suggested_category
            ticket.category_name = classification_result.get("suggested_category_name")
            ticket.classification_method = classification_result.get("classification_method")
            ticket.classification_confidence = classification_result.get("confidence")
            ticket.save()
            return True
        return False
    except Ticket.DoesNotExist:
        logger.warning(f"Ticket {ticket_id} não encontrado ao atualizar categoria")
        return False
    except Exception as e:
        logger.error(f"Erro ao atualizar ticket {ticket_id}: {str(e)}")
        return False


def handle_classification_failure(ticket_id: int) -> Tuple[bool, bool]:
    """
    Processa falha na classificação: atualiza status do ticket e verifica sugestão criada.
    
    Args:
        ticket_id: ID do ticket
        
    Returns:
        Tuple[bool, bool]: (status_updated, suggestion_exists)
            - status_updated: True se status foi atualizado
            - suggestion_exists: True se existe sugestão pendente
    """
    try:
        ticket = Ticket.objects.get(id=ticket_id)
        ticket.glpi_status = "Aprovação"
        ticket.save()
        
        suggestion = CategorySuggestion.objects.filter(
            ticket=ticket,
            status='pending'
        ).order_by('-created_at').first()
        
        return True, suggestion is not None
    except Ticket.DoesNotExist:
        logger.warning(f"Ticket {ticket_id} não encontrado ao definir status")
        return False, False
    except Exception as e:
        logger.error(f"Erro ao processar ticket {ticket_id}: {str(e)}")
        return False, False


def parse_suggestion_path(suggested_path: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Faz parse do caminho sugerido e valida.
    
    Args:
        suggested_path: Caminho completo sugerido
        
    Returns:
        Tuple[Optional[str], Optional[str], Optional[str]]: 
            (category_name, parent_path, error_message)
            - category_name: Nome da categoria ou None
            - parent_path: Caminho do pai ou None
            - error_message: Mensagem de erro ou None se válido
    """
    suggested_path = (suggested_path or '').strip()
    path_parts = [p.strip() for p in suggested_path.split('>') if p.strip()]
    category_name = path_parts[-1] if path_parts else ''
    parent_path = ' > '.join(path_parts[:-1]) if len(path_parts) > 1 else ''
    
    if not category_name:
        return None, None, "Sugestão inválida: suggested_path vazio ou mal formatado."
    
    return category_name, parent_path, None


def process_suggestion_review(
    suggestion: CategorySuggestion,
    new_status: str,
    notes: str,
    reviewed_by: str,
    reviewed_at
) -> Tuple[bool, Optional[str]]:
    """
    Processa aprovação ou rejeição de sugestão de categoria.
    
    Args:
        suggestion: Instância de CategorySuggestion
        new_status: 'approved' ou 'rejected'
        notes: Notas do revisor
        reviewed_by: Usuário que revisou
        reviewed_at: Data/hora da revisão
        
    Returns:
        Tuple[bool, Optional[str]]: (success, error_message)
            - success: True se processado com sucesso
            - error_message: Mensagem de erro ou None
    """
    from .clients.n8n_client import N8nClient
    
    category_name, parent_path, error_message = parse_suggestion_path(suggestion.suggested_path)
    if error_message:
        return False, error_message
    
    parent = find_category_by_path(parent_path) if parent_path else None
    if parent_path and not parent:
        return False, f"Categoria pai não encontrada no espelho local: '{parent_path}'. Sincronize as categorias do GLPI e tente novamente."
    
    parent_glpi_id = parent.glpi_id if parent else 0
    path_parts = [p.strip() for p in (suggestion.suggested_path or '').split('>') if p.strip()]
    ticket_type, _ = determine_ticket_type(path_parts)
    is_incident = 1 if ticket_type == 1 else 0
    is_request = 1 if ticket_type == 2 else 0
    
    # Notifica n8n
    n8n_client = N8nClient()
    n8n_client.notify_category_approval(
        suggestion_id=suggestion.id,
        ticket_id=suggestion.ticket.id,
        suggested_path=suggestion.suggested_path,
        parent_glpi_id=parent_glpi_id,
        category_name=category_name,
        status=new_status,
        notes=notes,
        reviewed_by=reviewed_by,
        reviewed_at=reviewed_at.isoformat() if hasattr(reviewed_at, 'isoformat') else reviewed_at,
        is_incident=is_incident,
        is_request=is_request,
        is_problem=0,
        is_change=0
    )
    
    # Atualiza sugestão
    suggestion.status = new_status
    suggestion.reviewed_at = reviewed_at
    suggestion.reviewed_by = reviewed_by
    suggestion.notes = notes
    suggestion.save()
    
    return True, None


# =========================================================
# SERVIÇOS DE WEBHOOK E PESQUISA DE SATISFAÇÃO
# =========================================================

def process_webhook_ticket(validated_data: Dict[str, Any], raw_payload: Dict[str, Any]) -> Ticket:
    """
    Processa ticket recebido via webhook do GLPI.
    
    Limpa o HTML do conteúdo e cria/atualiza o ticket no banco de dados.
    
    Args:
        validated_data: Dados validados pelo serializer
        raw_payload: Payload bruto da requisição para auditoria
        
    Returns:
        Ticket: Instância do ticket criada ou atualizada
    """
    from .utils import clean_html_content
    
    cleaned_content = clean_html_content(validated_data["content"])
    
    ticket, _ = Ticket.objects.update_or_create(
        id=validated_data["id"],
        defaults={
            "date_creation": validated_data["date_creation"],
            "user_recipient_id": validated_data["user_recipient_id"],
            "user_recipient_name": validated_data["user_recipient_name"],
            "location": validated_data.get("location") or "",
            "name": validated_data["name"],
            "content_html": cleaned_content,
            "category_name": validated_data.get("category_name") or "",
            "entity_id": validated_data.get("entity_id"),
            "entity_name": validated_data.get("entity_name") or "",
            "team_assigned_id": validated_data.get("team_assigned_id"),
            "team_assigned_name": validated_data.get("team_assigned_name") or "",
            "last_glpi_update": timezone.now(),
            "raw_payload": raw_payload
        }
    )
    
    return ticket


def _validate_survey_token(survey: Optional[SatisfactionSurvey], provided_token: str) -> bool:
    """
    Valida token de pesquisa de satisfação.
    
    Args:
        survey: Instância de SatisfactionSurvey ou None
        provided_token: Token fornecido pelo usuário
        
    Returns:
        bool: True se válido, False caso contrário
    """
    if not survey or not survey.token:
        return True
    
    if not provided_token or not survey.is_token_valid(provided_token):
        return False
    
    return True


def process_survey_rating(
    ticket: Ticket,
    rating: int,
    provided_token: str,
    comment: Optional[str] = None
) -> Tuple[SatisfactionSurvey, Optional[str]]:
    """
    Processa avaliação de pesquisa de satisfação.
    
    Valida token, cria ou atualiza survey existente e notifica n8n.
    
    Args:
        ticket: Instância do ticket
        rating: Nota de satisfação (1 a 5)
        provided_token: Token fornecido pelo usuário
        comment: Comentário opcional
        
    Returns:
        Tuple[SatisfactionSurvey, Optional[str]]: 
            (survey, error_message)
            - survey: Instância do survey criado/atualizado
            - error_message: Mensagem de erro ou None se sucesso
    """
    from .clients.n8n_client import N8nClient
    
    existing_survey = SatisfactionSurvey.objects.filter(ticket=ticket).first()
    
    if existing_survey:
        if not _validate_survey_token(existing_survey, provided_token):
            return None, 'Token inválido ou expirado. Esta pesquisa já foi respondida.'
        
        existing_survey.rating = rating
        if not existing_survey.token:
            existing_survey.generate_token()
            existing_survey.save(update_fields=['rating'])
        else:
            existing_survey.save()
        survey = existing_survey
    else:
        survey = SatisfactionSurvey.objects.create(
            ticket=ticket,
            rating=rating,
            comment=''
        )
        survey.generate_token()
    
    if comment:
        survey.comment = comment
        survey.save()
    
    n8n_client = N8nClient()
    n8n_client.notify_survey_response(
        ticket_id=ticket.id,
        rating=rating,
        comment=survey.comment
    )
    
    return survey, None


def process_survey_comment(
    ticket: Ticket,
    comment: str,
    provided_token: str
) -> Tuple[SatisfactionSurvey, Optional[str]]:
    """
    Processa comentário de pesquisa de satisfação.
    
    Valida token, cria ou atualiza survey existente e notifica n8n.
    
    Args:
        ticket: Instância do ticket
        comment: Comentário do usuário
        provided_token: Token fornecido pelo usuário
        
    Returns:
        Tuple[SatisfactionSurvey, Optional[str]]:
            (survey, error_message)
            - survey: Instância do survey criado/atualizado
            - error_message: Mensagem de erro ou None se sucesso
    """
    from .clients.n8n_client import N8nClient
    
    survey = SatisfactionSurvey.objects.filter(ticket=ticket).first()
    
    if not _validate_survey_token(survey, provided_token):
        return None, 'Token inválido ou expirado. Esta pesquisa já foi respondida.'
    
    if not survey:
        survey = SatisfactionSurvey.objects.create(
            ticket=ticket,
            rating=3,
            comment=comment
        )
        survey.generate_token()
    else:
        survey.comment = comment
        survey.save()
    
    n8n_client = N8nClient()
    n8n_client.notify_survey_response(
        ticket_id=ticket.id,
        rating=survey.rating,
        comment=comment
    )
    
    return survey, None
