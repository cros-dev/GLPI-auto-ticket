"""
Serviços auxiliares para processamento de tickets.

Este módulo contém funções para classificação automática de tickets usando
Google Gemini AI. 
"""
import logging
from typing import Optional, Dict, Tuple, List
from django.conf import settings
from .models import GlpiCategory, CategorySuggestion, Ticket
from .prompts import get_classification_prompt, get_suggestion_prompt, get_knowledge_base_prompt 

logger = logging.getLogger(__name__)


# =========================================================
# CONSTANTES
# =========================================================

SYSTEMS = [
    'anews', 'arion', 'glpi', 'ad', 'active directory', 'outlook', 'excel', 
    'word', 'teams', 'sharepoint', 'sap', 'erp', 'crm', 'bi', 'power bi'
]

EVENT_KEYWORDS = [
    'transmissão', 'transmissao', 'vídeo conferência', 'video conferencia', 
    'evento', 'premiação', 'premiacao', 'montagem', 'setup', 'apoio', 
    'cerimônia', 'cerimonia', 'auditório', 'auditorio'
]

GENERIC_CATEGORIES = [
    'periféricos', 'outros', 'outros acessos', 'outros equipamentos', 
    'solicitação geral', 'problema geral', 'problema geral de sistema',
    'equipamentos', 'hardware', 'software', 'sistemas', 'acesso'
]

VALID_ARTICLE_TYPES = ['conceitual', 'operacional', 'troubleshooting']


# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================

def _get_gemini_client():
    """
    Cria e retorna o cliente do Google Gemini AI.
    
    Returns:
        Optional[genai.Client]: Cliente Gemini ou None se API key não estiver configurada
    """
    api_key = getattr(settings, 'GEMINI_API_KEY', None)
    if not api_key:
        return None
    
    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except ImportError:
        logger.warning("Biblioteca google-genai não instalada")
        return None


def _call_gemini_api(client, prompt: str, model: str = "gemini-2.5-flash") -> Optional[str]:
    """
    Faz chamada à API do Gemini e retorna a resposta processada.
    
    Args:
        client: Cliente Gemini
        prompt: Prompt a ser enviado
        model: Modelo a ser usado (padrão: gemini-2.5-flash)
        
    Returns:
        Optional[str]: Resposta processada ou None em caso de erro
    """
    if not client:
        return None
    
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt
        )
        return response.text.strip() if response.text else None
    except Exception as e:
        error_type, error_message = _parse_gemini_error(e)
        logger.warning(f"Erro ao chamar API do Gemini: {error_type} - {str(e)}")
        return None


def _parse_gemini_error(exception: Exception) -> Tuple[str, str]:
    """
    Analisa exceções da API do Gemini e retorna informações específicas sobre o erro.
    
    Args:
        exception: Exceção capturada
        
    Returns:
        Tuple[str, str]: (tipo_erro, mensagem_amigavel)
        tipos possíveis: 'api_key_invalid', 'api_key_expired', 'quota_exceeded', 
                         'service_unavailable', 'unknown'
    """
    error_str = str(exception)
    error_lower = error_str.lower()
    
    if '503' in error_str or 'unavailable' in error_lower or 'overloaded' in error_lower:
        return 'service_unavailable', 'O modelo do Gemini está sobrecarregado. Tente novamente em alguns instantes.'
    
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
    return last_level in GENERIC_CATEGORIES


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
    """
    client = _get_gemini_client()
    if not client:
        logger.debug("GEMINI_API_KEY não configurada, classificação será ignorada")
        return None
    
    try:
        categories_text = get_categories_for_ai()
        prompt = get_classification_prompt(categories_text, title, content)
        response_text = _call_gemini_api(client, prompt)
        
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
    (ex.: "TI > Requisição > Equipamentos > Hardware > Montagem de Setup > Transmissão/Vídeo Conferência").
    
    Antes de gerar, verifica se já existe uma categoria similar no banco para evitar duplicatas.
    
    Args:
        title: Título do ticket
        content: Conteúdo/descrição do ticket
        ticket_id: ID do ticket para vincular a sugestão (opcional)
        
    Returns:
        Optional[str]: Caminho completo sugerido ou None se não conseguir gerar
    """
    client = _get_gemini_client()
    if not client:
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
        response_text = _call_gemini_api(client, prompt)
        
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
        
    except Exception as e:
        error_type, error_message = _parse_gemini_error(e)
        logger.warning(f"Erro ao gerar sugestão de categoria: {error_type} - {str(e)}")
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
    
    client = _get_gemini_client()
    if not client:
        logger.debug("GEMINI_API_KEY não configurada, geração de artigo será ignorada")
        return None
    
    try:
        prompt = get_knowledge_base_prompt(article_type, category, context)
        response_text = _call_gemini_api(client, prompt)
        
        if not response_text:
            logger.warning("Resposta vazia da API do Gemini para geração de artigo")
            return {'error': 'empty_response', 'message': 'A API do Gemini retornou uma resposta vazia'}
        
        lines = response_text.split('\n')
        if lines and lines[0].lower().startswith(('artigo:', 'base de conhecimento:')):
            response_text = '\n'.join(lines[1:]).strip()
        
        # Separa múltiplos artigos se houver
        articles = _split_articles(response_text)
        
        logger.info(f"Artigo(s) de Base de Conhecimento gerado(s) com sucesso. Tipo: {article_type}, Categoria: {category}, Total: {len(articles)}")
        
        return {
            'articles': articles,
            'article_type': article_type.lower(),
            'category': category.strip()
        }
        
    except Exception as e:
        error_type, error_message = _parse_gemini_error(e)
        logger.warning(f"Erro ao gerar artigo de Base de Conhecimento: {error_type} - {str(e)}")
        return {'error': error_type, 'message': error_message}
