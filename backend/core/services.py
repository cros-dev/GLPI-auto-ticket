"""
Serviços auxiliares para processamento de tickets.

Este módulo contém funções para classificação automática de tickets usando
Google Gemini AI. 
"""
import logging
from typing import Optional, Dict, Tuple, List
from django.conf import settings
from .models import GlpiCategory, CategorySuggestion, Ticket 

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


# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================

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


def _find_similar_category_by_systems(ticket_text: str, min_levels: int = 5) -> Optional[str]:
    """
    Busca categoria existente que menciona sistemas do ticket.
    
    Args:
        ticket_text: Texto do ticket em minúsculas
        min_levels: Número mínimo de níveis da categoria
        
    Returns:
        Optional[str]: Caminho completo da categoria encontrada ou None
    """
    for system in SYSTEMS:
        if system in ticket_text:
            categories = GlpiCategory.objects.filter(full_path__icontains=system)
            for cat in categories:
                path = get_category_path(cat)
                if len(path) >= min_levels:
                    full_path = ' > '.join(path)
                    full_path_lower = full_path.lower()
                    if ('problema de acesso' in full_path_lower or 
                        'indisponibilidade de sistema' in full_path_lower or
                        'falha em processo' in full_path_lower or
                        'requisição' in full_path_lower):
                        logger.info(f"Categoria similar encontrada: {full_path}")
                        return full_path
    return None


def _find_similar_category_by_events(ticket_text: str, min_levels: int = 5) -> Optional[str]:
    """
    Busca categoria existente relacionada a eventos/montagem de setup.
    
    Args:
        ticket_text: Texto do ticket em minúsculas
        min_levels: Número mínimo de níveis da categoria
        
    Returns:
        Optional[str]: Caminho completo da categoria encontrada ou None
    """
    for keyword in EVENT_KEYWORDS:
        if keyword in ticket_text:
            categories = GlpiCategory.objects.filter(full_path__icontains=keyword)
            for cat in categories:
                path = get_category_path(cat)
                if len(path) >= min_levels:
                    full_path = ' > '.join(path)
                    full_path_lower = full_path.lower()
                    if ('montagem de setup' in full_path_lower or 
                        'transmissão' in full_path_lower or 
                        'video conferência' in full_path_lower):
                        logger.info(f"Categoria de evento/montagem encontrada: {full_path}")
                        return full_path
    return None


def _get_similar_categories_for_reference(ticket_text: str) -> List[str]:
    """
    Busca categorias similares para usar como referência em prompts.
    
    Args:
        ticket_text: Texto do ticket em minúsculas
        
    Returns:
        List[str]: Lista de caminhos completos de categorias similares
    """
    similar_categories = []
    
    # Busca por sistemas mencionados
    for system in SYSTEMS:
        if system in ticket_text:
            for cat in GlpiCategory.objects.filter(full_path__icontains=system):
                path = get_category_path(cat)
                if len(path) >= 4:
                    similar_categories.append(' > '.join(path))
    
    # Busca por palavras-chave de eventos/montagem
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

REGRAS CRÍTICAS: 
- SEMPRE prefira categorias com MAIS NÍVEIS (mais específicas) quando disponíveis
- Se o ticket menciona um sistema/aplicação específico (ex: Anews, Arion, GLPI, AD, etc.), DEVE usar uma categoria que inclua esse sistema
- NUNCA escolha uma categoria genérica se existir uma subcategoria mais específica que se encaixe melhor
- Se encontrar uma categoria de nível 4 ou 5 que se encaixa, mas há uma subcategoria de nível 5 ou 6 que menciona o sistema/aplicação do ticket, USE A SUBCATEGORIA MAIS ESPECÍFICA
- USE O NOME EXATO da categoria da lista acima - NÃO invente ou modifique nomes de sistemas/aplicações
- Se existe "Anews / Arion" na lista, USE "Anews / Arion" - NÃO use apenas "Anews" ou "Arion"

DISTINÇÕES CRÍTICAS ENTRE TIPOS DE PROBLEMA:

1. "Problema de Acesso" = usuário não consegue acessar/login (credencial inválida, senha errada, permissão negada, bloqueio de conta, etc.) - o sistema está funcionando, mas o usuário específico não consegue entrar
   - Palavras-chave: "credencial inválida", "não consegui logar", "senha não funciona", "acesso negado", "conta bloqueada"
   - Use: "TI > Incidente > Sistemas > Problema de Acesso > [Sistema EXATO da lista]"
   - IMPORTANTE: Se o sistema é "Anews", use "Anews" (não "Anews / Arion") conforme a lista

2. "Indisponibilidade de Sistema" = sistema está fora do ar, não está funcionando, inacessível para todos - problema de infraestrutura/servidor/redes
   - Palavras-chave: "sistema fora do ar", "indisponível", "não está funcionando", "erro ao acessar" (sem mencionar credencial), "servidor não responde", "sistema down"
   - Use: "TI > Incidente > Sistemas > Indisponibilidade de Sistema > [Sistema EXATO da lista]"
   - IMPORTANTE: Se o sistema é "Anews / Arion", use "Anews / Arion" conforme a lista

3. "Falha em Processo" = sistema funciona normalmente, mas um processo específico dentro do sistema falha (ex: processo de RP, processo de Salesforce)
   - Palavras-chave: "processo não funciona", "falha no processo", "erro no processo", "processo travado"
   - Use: "TI > Incidente > Sistemas > Falha em Processo > [Sistema específico: RP, Salesforce, Outros]"

4. "Problema Geral de Sistema" = categoria genérica - EVITE quando há categorias mais específicas disponíveis
   - Só use se realmente não houver categoria mais específica que se encaixe

5. "Outros" = categoria genérica - SEMPRE EVITE quando há categorias específicas disponíveis

- Exemplos de categorias genéricas a EVITAR quando há subcategorias: "Problema de Acesso" (sem sistema), "Indisponibilidade de Sistema" (sem sistema), "Problema Geral de Sistema", "Outros", "Hardware" (sem tipo específico)

DISTINÇÕES PARA REQUISIÇÕES:

1. "Requisição > Acesso" = acesso a INFRAESTRUTURA (AD, VPN, Rede, Pastas de Rede)
   - "Requisição > Acesso > AD > Liberação de Rede / Wi-Fi" = solicitação de LIBERAÇÃO/PERMISSÃO de acesso Wi-Fi (não é instalação física)
   - Use para: criar usuário AD, liberar acesso Wi-Fi (permissão), acesso VPN, acesso a pastas de rede
   - Palavras-chave: "criar usuário AD", "liberar Wi-Fi", "liberar rede", "permissão Wi-Fi", "acesso VPN", "pasta de rede"
   - IMPORTANTE: Distinga de "Requisição > Equipamentos > Hardware > Infraestrutura de Rede" (instalação física de cabo/ponto/equipamento)

2. "Requisição > Sistemas > Acesso a Sistema" = acesso a SISTEMAS/APLICAÇÕES específicos (Anews, Salesforce, RP, etc.)
   - Use para: solicitar acesso a sistemas/aplicações específicos
   - Palavras-chave: "acesso ao sistema", "solicitar acesso", "permissão no sistema"
   - IMPORTANTE: Distinga entre acesso a infraestrutura (AD/rede) e acesso a sistemas/aplicações (Anews, Salesforce, etc.)

3. "Requisição > Equipamentos" = solicitação de equipamentos (novo, reparo, substituição, mudança de local)
   - "Requisição > Equipamentos > Hardware > Infraestrutura de Rede > Novo Ponto de Rede" = solicitar instalação de novo ponto de rede (cabo físico)
   - "Requisição > Equipamentos > Hardware > Infraestrutura de Rede > Instalação / Substituição de Equipamento" = solicitar instalação/substituição de equipamento de rede (switch, roteador, cabo)
   - Use para: solicitar novo equipamento, reparo, substituição, mudança de local, instalação de cabo de rede, novo ponto de rede
   - Palavras-chave: "novo equipamento", "preciso de", "solicitar", "reparo", "substituição", "cabo de rede", "ponto de rede", "instalar cabo", "novo ponto"
   - IMPORTANTE: Em Requisição use "Impressora" (singular), em Incidente use "Impressoras" (plural)
   - IMPORTANTE: "Requisição > Acesso > AD > Liberação de Rede / Wi-Fi" = permissão/acesso Wi-Fi | "Requisição > Equipamentos > Hardware > Infraestrutura de Rede" = instalação física de cabo/ponto/equipamento

4. "Requisição > Equipamentos > Hardware > Montagem de Setup" = solicitação de montagem TEMPORÁRIA de equipamentos para eventos, transmissões, vídeo conferências
   - "Requisição > Equipamentos > Hardware > Montagem de Setup > Transmissão/Vídeo Conferência" = montagem de equipamentos para transmissão/vídeo conferência em eventos
   - Use para: eventos, transmissões, vídeo conferências, premiações, cerimônias que requerem montagem temporária de equipamentos (microfone, câmera, áudio, vídeo)
   - Palavras-chave: "transmissão", "vídeo conferência", "evento", "apoio", "montagem", "setup", "premiação", "cerimônia", "auditório", "interação", "microfone", "câmera", "áudio", "vídeo", "solicitação de serviço", "acompanhamento"
   - EXEMPLO ESPECÍFICO: "Solicitação de Serviço - APOIO para transmissão de premiação" → "TI > Requisição > Equipamentos > Hardware > Montagem de Setup > Transmissão/Vídeo Conferência"
   - IMPORTANTE: Distinga de "Mudança > Gestão de Mudança > Programada > Instalação de Equipamento"
     * Montagem de Setup = TEMPORÁRIA para eventos/ocasiões especiais (ex: "apoio para evento", "transmissão de premiação", "montagem temporária")
     * Instalação de Equipamento = PERMANENTE para infraestrutura (ex: "instalar servidor", "nova infraestrutura permanente")

5. "Requisição > Software" = solicitação de software (instalação, atualização, licenciamento)
   - Use para: instalar software, atualizar software, renovar licença
   - Palavras-chave: "instalar", "atualizar", "licença", "licenciamento"

DISTINÇÕES PARA INCIDENTES:

1. "Incidente > Acesso > AD > Rede / Wi-Fi - Sem Conexão" = problema de conexão Wi-Fi/rede (sem acesso, não conecta)
   - Use para: não consegue conectar no Wi-Fi, sem conexão de rede, problema de acesso à rede
   - Palavras-chave: "não conecta", "sem conexão", "Wi-Fi não funciona", "sem acesso à rede"
   - IMPORTANTE: Distinga de "Incidente > Equipamentos > Hardware > Infraestrutura de Rede" (problema com equipamento físico)

2. "Incidente > Equipamentos > Hardware > Infraestrutura de Rede" = problema com equipamento físico de rede
   - "Incidente > Equipamentos > Hardware > Infraestrutura de Rede > Switch / Roteador com Falha" = problema com switch ou roteador
   - "Incidente > Equipamentos > Hardware > Infraestrutura de Rede > Outros" = problema com cabo de rede, ponto de rede, outro equipamento físico
   - Use para: cabo de rede com problema, switch com falha, roteador com problema, ponto de rede com falha
   - Palavras-chave: "cabo quebrado", "switch com problema", "roteador com falha", "ponto de rede com problema", "equipamento de rede com falha"
   - IMPORTANTE: "Incidente > Acesso > AD > Rede / Wi-Fi - Sem Conexão" = problema de conexão/acesso | "Incidente > Equipamentos > Hardware > Infraestrutura de Rede" = problema com equipamento físico

3. "Incidente > Equipamentos" = problema com equipamento existente (não liga, travando, lentidão, etc.)
   - "Incidente > Equipamentos > Hardware > Computadores > Não Liga / Travando" = computador não liga ou trava
   - "Incidente > Equipamentos > Hardware > Computadores > Lentidão" = computador lento
   - "Incidente > Equipamentos > Impressoras > Não Imprime" = impressora não imprime
   - "Incidente > Equipamentos > Impressoras > Falha de Conexão / Spooler" = problema de conexão/spooler
   - Palavras-chave: "não funciona", "não liga", "travando", "lentidão", "erro", "não imprime"
   - IMPORTANTE: Em Incidente use "Impressoras" (plural), em Requisição use "Impressora" (singular)

4. "Incidente > Software" = problema com software (erro, travamento, desempenho lento, etc.)
   - Use para: software com erro, travando, desempenho lento, falha ao abrir
   - Palavras-chave: "erro", "travando", "lento", "não abre", "falha"

- Só retorne uma categoria se ela se encaixar PERFEITAMENTE no contexto do ticket, incluindo sistemas/aplicações mencionados E o tipo correto de problema (Incidente = problema, Requisição = solicitação)
- Se a categoria mais próxima for muito genérica ou não mencionar sistemas/aplicações do ticket, responda "Nenhuma" para que possamos criar uma categoria mais específica

Título: {title}
Conteúdo: {content}

Responda APENAS com o caminho completo da categoria EXATA da lista acima (ex: "TI > Incidente > Sistemas > Indisponibilidade de Sistema > Anews / Arion") e o ID entre parênteses (ex: "(84)"). 
IMPORTANTE: Use o nome EXATO do sistema/aplicação como aparece na lista - não invente ou modifique.
Se não encontrar uma categoria adequada e específica que mencione sistemas/aplicações do ticket, responda "Nenhuma".

Formato da resposta:
CATEGORIA: [caminho completo EXATO da lista]
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
        
        # Rejeita categorias muito genéricas
        if _is_generic_category(category_path):
            logger.info(f"Categoria muito genérica encontrada ({len(category_path)} níveis): {' > '.join(category_path)}. Gerando sugestão mais específica.")
            return None
        
        # Validação específica para "Problema de Acesso" e "Indisponibilidade de Sistema"
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
    (ex.: "TI > Requisição > Equipamentos > Hardware > Montagem de Setup > Transmissão/Vídeo Conferência").
    
    Antes de gerar, verifica se já existe uma categoria similar no banco para evitar duplicatas.
    
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
    
    ticket_text = f"{title} {content}".lower()
    
    # Verificação prévia: se menciona eventos/transmissões, força categoria correta
    event_indicators = ['evento', 'transmissão', 'transmissao', 'vídeo conferência', 'video conferencia', 
                       'premiação', 'premiacao', 'cerimônia', 'cerimonia', 'auditório', 'auditorio',
                       'solicitação de serviço - apoio', 'solicitação de serviço', 'apoio']
    has_event_keywords = any(indicator in ticket_text for indicator in event_indicators)
    
    if has_event_keywords:
        # Primeiro tenta encontrar categoria existente
        similar_category = _find_similar_category_by_events(ticket_text)
        if similar_category:
            return similar_category
        # Se não encontrou, força a categoria correta
        logger.info(f"Ticket menciona eventos/transmissões. Forçando categoria: TI > Requisição > Equipamentos > Hardware > Montagem de Setup > Transmissão/Vídeo Conferência")
        return "TI > Requisição > Equipamentos > Hardware > Montagem de Setup > Transmissão/Vídeo Conferência"
    
    # Verifica se já existe categoria similar antes de gerar nova sugestão
    similar_category = _find_similar_category_by_systems(ticket_text)
    if similar_category:
        return similar_category
    
    similar_category = _find_similar_category_by_events(ticket_text)
    if similar_category:
        return similar_category
    
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        
        categories_text = get_categories_for_ai()
        similar_categories = _get_similar_categories_for_reference(ticket_text)
        
        similar_ref = ""
        if similar_categories:
            similar_ref = f"\n\nCategorias similares existentes (use como referência para nomes e estrutura):\n" + "\n".join([f"- {cat}" for cat in similar_categories])
        
        prompt = f"""Você é um assistente especializado em classificação de tickets de suporte técnico.

ANÁLISE OBRIGATÓRIA PRIMEIRO - SIGA ESTA ORDEM EXATA ANTES DE QUALQUER OUTRA COISA:

1. O ticket menciona "evento", "transmissão", "vídeo conferência", "premiação", "cerimônia", "apoio", "solicitação de serviço - apoio", "acompanhamento de transmissão", "montagem", "setup", "auditório", "interação", "microfone", "câmera", "áudio", "vídeo"? 
   → SE SIM, USE OBRIGATORIAMENTE: "TI > Requisição > Equipamentos > Hardware > Montagem de Setup > Transmissão/Vídeo Conferência"
   → EXEMPLO: "Solicitação de Serviço - APOIO para transmissão de premiação" → "TI > Requisição > Equipamentos > Hardware > Montagem de Setup > Transmissão/Vídeo Conferência"
   → NÃO USE OUTRA CATEGORIA SE O TICKET MENCIONA EVENTO/TRANSMISSÃO/APOIO

2. O ticket menciona instalação permanente de infraestrutura (servidor, rede permanente, nova infraestrutura)? 
   → Use: "TI > Mudança > Gestão de Mudança > Programada > Instalação de Equipamento"

3. O ticket menciona problema com equipamento existente (não funciona, erro, travando, não liga)? 
   → Use: "TI > Incidente > Equipamentos"

4. O ticket menciona solicitação de novo equipamento permanente (computador, impressora, servidor)? 
   → Use: "TI > Requisição > Equipamentos > Hardware"

5. O ticket menciona instalação de software (Adobe, Office, etc.)? 
   → Use: "TI > Requisição > Software > Instalação"

Analise o seguinte ticket e sugira uma categoria hierárquica seguindo o padrão:
TI > [Incidente/Requisição] > [Área] > [Subárea] > [Categoria Específica] > [Sistema/Aplicação quando aplicável]

REGRAS IMPORTANTES:
- SEMPRE analise o contexto completo do ticket antes de sugerir categoria
- Se o ticket menciona eventos, transmissões, vídeo conferências, premiações, cerimônias, use "Requisição > Equipamentos > Hardware > Montagem de Setup"
- SEMPRE inclua o sistema/aplicação mencionado no ticket no último nível quando aplicável
- Se existem categorias similares listadas abaixo, USE O NOME EXATO e a ESTRUTURA EXATA como aparece nelas
- Mantenha consistência com nomes de sistemas e estruturas já existentes no sistema

DISTINÇÕES CRÍTICAS ENTRE TIPOS DE PROBLEMA:

1. "Problema de Acesso" = usuário não consegue acessar/login (credencial inválida, senha errada, permissão negada, bloqueio de conta, etc.) - o sistema está funcionando, mas o usuário específico não consegue entrar
   - Palavras-chave: "credencial inválida", "não consegui logar", "senha não funciona", "acesso negado", "conta bloqueada"
   - Use: "TI > Incidente > Sistemas > Problema de Acesso > [Nome do Sistema - use nome exato se existir em categorias similares]"
   - IMPORTANTE: Se o sistema é "Anews", use "Anews" (não "Anews / Arion") conforme categorias similares

2. "Indisponibilidade de Sistema" = sistema está fora do ar, não está funcionando, inacessível para todos - problema de infraestrutura/servidor/redes
   - Palavras-chave: "sistema fora do ar", "indisponível", "não está funcionando", "erro ao acessar" (sem mencionar credencial), "servidor não responde", "sistema down"
   - Use: "TI > Incidente > Sistemas > Indisponibilidade de Sistema > [Nome do Sistema - use nome exato se existir em categorias similares]"
   - IMPORTANTE: Se o sistema é "Anews / Arion", use "Anews / Arion" conforme categorias similares

3. "Falha em Processo" = sistema funciona normalmente, mas um processo específico dentro do sistema falha (ex: processo de RP, processo de Salesforce)
   - Palavras-chave: "processo não funciona", "falha no processo", "erro no processo", "processo travado"
   - Use: "TI > Incidente > Sistemas > Falha em Processo > [Sistema específico: RP, Salesforce, Outros]"

4. "Problema Geral de Sistema" = categoria genérica - EVITE quando há categorias mais específicas disponíveis

5. "Outros" = categoria genérica - SEMPRE EVITE quando há categorias específicas disponíveis

REGRAS DE CLASSIFICAÇÃO PARA REQUISIÇÕES:

1. "Requisição > Acesso" = acesso a INFRAESTRUTURA (AD, VPN, Rede, Pastas de Rede)
   - "Requisição > Acesso > AD > Criação de Usuário / Conta" = criação de usuário no Active Directory
   - "Requisição > Acesso > AD > Liberação de Rede / Wi-Fi" = liberação de acesso de rede/Wi-Fi (permissão, não instalação física)
   - "Requisição > Acesso > Acesso Remoto / VPN" = acesso remoto/VPN
   - "Requisição > Acesso > Pastas de Rede" = acesso a pastas de rede
   - Palavras-chave: "criar usuário AD", "liberar rede", "acesso VPN", "pasta de rede"
   - IMPORTANTE: Distinga de "Requisição > Equipamentos > Hardware > Infraestrutura de Rede" (instalação física de cabo/ponto/equipamento)

2. "Requisição > Sistemas > Acesso a Sistema" = acesso a SISTEMAS/APLICAÇÕES específicos (Anews, Salesforce, RP, etc.)
   - "Requisição > Sistemas > Acesso a Sistema > Anews / Arion" = acesso ao sistema Anews/Arion
   - "Requisição > Sistemas > Acesso a Sistema > Salesforce" = acesso ao Salesforce
   - Palavras-chave: "acesso ao sistema", "solicitar acesso", "permissão no sistema"
   - IMPORTANTE: Use o nome EXATO do sistema como aparece na lista (ex: "Anews / Arion", não apenas "Anews")

3. "Requisição > Sistemas > Atualização / Parametrização" = atualização ou parametrização de sistema
   - Palavras-chave: "atualizar sistema", "parametrizar", "configurar sistema"

4. "Requisição > Equipamentos" = solicitação de equipamentos (novo, reparo, substituição, mudança de local)
   - "Requisição > Equipamentos > Hardware > Computadores > Novo Equipamento" = solicitar novo computador
   - "Requisição > Equipamentos > Hardware > Computadores > Reparo / Substituição" = solicitar reparo/substituição
   - "Requisição > Equipamentos > Hardware > Infraestrutura de Rede > Novo Ponto de Rede" = solicitar instalação de novo ponto de rede (cabo físico)
   - "Requisição > Equipamentos > Hardware > Infraestrutura de Rede > Instalação / Substituição de Equipamento" = solicitar instalação/substituição de equipamento de rede (switch, roteador, cabo)
   - "Requisição > Equipamentos > Impressora > Nova Impressora / Instalação" = solicitar nova impressora
   - "Requisição > Equipamentos > Impressora > Solicitação de Toner" = solicitar toner
   - Palavras-chave: "novo equipamento", "preciso de", "solicitar", "reparo", "substituição", "toner", "cabo de rede", "ponto de rede", "instalar cabo", "novo ponto"
   - IMPORTANTE: Em Requisição use "Impressora" (singular), em Incidente use "Impressoras" (plural)
   - IMPORTANTE: "Requisição > Acesso > AD > Liberação de Rede / Wi-Fi" = permissão/acesso Wi-Fi | "Requisição > Equipamentos > Hardware > Infraestrutura de Rede" = instalação física de cabo/ponto/equipamento

5. "Requisição > Equipamentos > Hardware > Montagem de Setup" = solicitação de montagem TEMPORÁRIA de equipamentos para eventos, transmissões, vídeo conferências
   - "Requisição > Equipamentos > Hardware > Montagem de Setup > Transmissão/Vídeo Conferência" = montagem de equipamentos para transmissão/vídeo conferência em eventos
   - Use para: eventos, transmissões, vídeo conferências, premiações, cerimônias que requerem montagem temporária de equipamentos (microfone, câmera, áudio, vídeo)
   - Palavras-chave: "transmissão", "vídeo conferência", "evento", "apoio", "montagem", "setup", "premiação", "cerimônia", "auditório", "interação", "microfone", "câmera", "áudio", "vídeo", "solicitação de serviço", "acompanhamento"
   - EXEMPLO ESPECÍFICO: "Solicitação de Serviço - APOIO para transmissão de premiação" → "TI > Requisição > Equipamentos > Hardware > Montagem de Setup > Transmissão/Vídeo Conferência"
   - IMPORTANTE: Distinga de "Mudança > Gestão de Mudança > Programada > Instalação de Equipamento"
     * Montagem de Setup = TEMPORÁRIA para eventos/ocasiões especiais (ex: "apoio para evento", "transmissão de premiação")
     * Instalação de Equipamento = PERMANENTE para infraestrutura (ex: "instalar servidor", "nova infraestrutura permanente")

6. "Requisição > Software" = solicitação de software (instalação, atualização, licenciamento)
   - "Requisição > Software > Instalação" = instalar software
   - "Requisição > Software > Atualização" = atualizar software
   - "Requisição > Software > Licenciamento / Renovação" = renovar licença
   - Palavras-chave: "instalar", "atualizar", "licença", "licenciamento"

DISTINÇÕES PARA INCIDENTES:

1. "Incidente > Acesso > AD > Rede / Wi-Fi - Sem Conexão" = problema de conexão Wi-Fi/rede (sem acesso, não conecta)
   - Use para: não consegue conectar no Wi-Fi, sem conexão de rede, problema de acesso à rede
   - Palavras-chave: "não conecta", "sem conexão", "Wi-Fi não funciona", "sem acesso à rede"
   - IMPORTANTE: Distinga de "Incidente > Equipamentos > Hardware > Infraestrutura de Rede" (problema com equipamento físico)

2. "Incidente > Equipamentos > Hardware > Infraestrutura de Rede" = problema com equipamento físico de rede
   - "Incidente > Equipamentos > Hardware > Infraestrutura de Rede > Switch / Roteador com Falha" = problema com switch ou roteador
   - "Incidente > Equipamentos > Hardware > Infraestrutura de Rede > Outros" = problema com cabo de rede, ponto de rede, outro equipamento físico
   - Use para: cabo de rede com problema, switch com falha, roteador com problema, ponto de rede com falha
   - Palavras-chave: "cabo quebrado", "switch com problema", "roteador com falha", "ponto de rede com problema", "equipamento de rede com falha"
   - IMPORTANTE: "Incidente > Acesso > AD > Rede / Wi-Fi - Sem Conexão" = problema de conexão/acesso | "Incidente > Equipamentos > Hardware > Infraestrutura de Rede" = problema com equipamento físico

3. "Incidente > Equipamentos" = problema com equipamento existente (não liga, travando, lentidão, etc.)
   - "Incidente > Equipamentos > Hardware > Computadores > Não Liga / Travando" = computador não liga ou trava
   - "Incidente > Equipamentos > Hardware > Computadores > Lentidão" = computador lento
   - "Incidente > Equipamentos > Impressoras > Não Imprime" = impressora não imprime
   - "Incidente > Equipamentos > Impressoras > Falha de Conexão / Spooler" = problema de conexão/spooler
   - Palavras-chave: "não funciona", "não liga", "travando", "lentidão", "erro", "não imprime"
   - IMPORTANTE: Em Incidente use "Impressoras" (plural), em Requisição use "Impressora" (singular)

4. "Incidente > Software" = problema com software (erro, travamento, desempenho lento, etc.)
   - "Incidente > Software > Erro de Execução" = erro ao executar software
   - "Incidente > Software > Falha ao Abrir / Travamento" = software não abre ou trava
   - "Incidente > Software > Desempenho Lento" = software lento
   - Palavras-chave: "erro", "travando", "lento", "não abre", "falha"

DISTINÇÃO CRÍTICA GERAL:
- "Requisição > Acesso > AD > Liberação de Rede / Wi-Fi" = solicitação de PERMISSÃO/LIBERAÇÃO de acesso Wi-Fi (não é instalação física)
- "Requisição > Equipamentos > Hardware > Infraestrutura de Rede" = solicitação de INSTALAÇÃO FÍSICA de cabo, ponto de rede, equipamento (switch, roteador)
- "Incidente > Acesso > AD > Rede / Wi-Fi - Sem Conexão" = problema de CONEXÃO/ACESSO Wi-Fi (não conecta, sem acesso)
- "Incidente > Equipamentos > Hardware > Infraestrutura de Rede" = problema com EQUIPAMENTO FÍSICO de rede (cabo quebrado, switch com falha, roteador com problema)
- "Requisição > Acesso" é para INFRAESTRUTURA (AD, rede, VPN) - permissões e acessos
- "Requisição > Sistemas > Acesso a Sistema" é para SISTEMAS/APLICAÇÕES específicos (Anews, Salesforce, etc.)
- "Requisição > Equipamentos > Hardware > Montagem de Setup" = montagem TEMPORÁRIA para eventos/transmissões | "Mudança > Instalação de Equipamento" = instalação PERMANENTE de infraestrutura
- "Requisição" = solicitação (novo, instalar, acesso, montagem temporária para evento) | "Incidente" = problema (não funciona, erro, travando) | "Mudança" = alteração PERMANENTE na infraestrutura
- "TI > Mudança" = gestão de mudanças PERMANENTES na infraestrutura (planejamento, execução, gestão de mudança)

{similar_ref}

Exemplos de padrões:
- TI > Requisição > Acesso > AD > Criação de Usuário / Conta
- TI > Incidente > Sistemas > Problema de Acesso > Anews (para "não consegui logar no Anews, credencial inválida")
- TI > Incidente > Sistemas > Indisponibilidade de Sistema > Anews / Arion (para "Anews está fora do ar")
- TI > Requisição > Sistemas > Acesso a Sistema > Anews / Arion (para "preciso de acesso ao Anews")
- TI > Incidente > Equipamentos > Hardware > Computadores > Não Liga / Travando
- TI > Requisição > Equipamentos > Hardware > Montagem de Setup > Transmissão/Vídeo Conferência (para "solicitação de apoio para transmissão de evento")

Título: {title}
Conteúdo: {content}

LEMBRE-SE: SE O TICKET MENCIONA EVENTO/TRANSMISSÃO/APOIO/PREMIAÇÃO, USE OBRIGATORIAMENTE "TI > Requisição > Equipamentos > Hardware > Montagem de Setup > Transmissão/Vídeo Conferência"

Sugira APENAS o caminho completo da categoria seguindo o padrão acima.
IMPORTANTE CRÍTICO: 
- Se há categorias similares listadas acima, use o nome EXATO e a ESTRUTURA EXATA como aparece nelas
- Para eventos/transmissões/apoio, SEMPRE use "TI > Requisição > Equipamentos > Hardware > Montagem de Setup > Transmissão/Vídeo Conferência"
- NÃO invente categorias que não seguem o padrão hierárquico correto
- NÃO confunda "Montagem de Setup" (temporário para eventos) com "Instalação de Equipamento" (permanente)
- NÃO confunda solicitação de apoio para evento com instalação de software
- NÃO use "Software > Instalação" se o ticket menciona evento/transmissão/apoio
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
        
        if suggested_path and isinstance(suggested_path, str):
            save_category_suggestion(ticket_id, suggested_path, title, content)
            logger.info(f"Sugestão de categoria criada para ticket {ticket_id}: {suggested_path}")
    
    return result
