"""
Prompts para classificação de tickets usando Google Gemini AI.
Este módulo contém os templates de prompts utilizados para classificação
e sugestão de categorias de tickets.
"""

# ==================== PARTES COMUNS ====================

INTRO = """Você é um assistente especializado em classificação de tickets de suporte técnico."""

PROBLEM_DISTINCTIONS = """DISTINÇÕES CRÍTICAS ENTRE TIPOS DE PROBLEMA:
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
5. "Outros" = categoria genérica - SEMPRE EVITE quando há categorias específicas disponíveis"""

REQUEST_DISTINCTIONS = """DISTINÇÕES PARA REQUISIÇÕES:
1. "Requisição > Acesso" = acesso a INFRAESTRUTURA (AD, VPN, Rede, Pastas de Rede)
   - "Requisição > Acesso > AD > Liberação de Rede / Wi-Fi" = liberação de PERMISSÃO de acesso Wi-Fi/rede (não instalação física)
   - "Requisição > Equipamentos > Hardware > Infraestrutura de Rede" = INSTALAÇÃO FÍSICA de componentes de rede (cabos, pontos, switches)
   - Use para: criar usuário AD, liberar rede, acesso VPN, acesso a pastas de rede
   - Palavras-chave: "criar usuário AD", "liberar rede", "acesso VPN", "pasta de rede", "permissão de Wi-Fi"
   - IMPORTANTE: Distinga entre permissão de acesso (AD > Liberação de Rede / Wi-Fi) e instalação física (Equipamentos > Infraestrutura de Rede)
2. "Requisição > Sistemas > Acesso a Sistema" = acesso a SISTEMAS/APLICAÇÕES específicos (Anews, Salesforce, RP, etc.)
   - Use para: solicitar acesso a sistemas/aplicações específicos
   - Palavras-chave: "acesso ao sistema", "solicitar acesso", "permissão no sistema"
   - IMPORTANTE: Distinga entre acesso a infraestrutura (AD/rede) e acesso a sistemas/aplicações (Anews, Salesforce, etc.)
3. "Requisição > Equipamentos" = solicitação de equipamentos (novo, reparo, substituição, mudança de local)
   - Use para: solicitar novo equipamento, reparo, substituição, mudança de local
   - Palavras-chave: "novo equipamento", "preciso de", "solicitar", "reparo", "substituição"
   - IMPORTANTE: Em Requisição use "Impressora" (singular), em Incidente use "Impressoras" (plural)
4. "Requisição > Equipamentos > Hardware > Montagem de Setup" = solicitação de montagem TEMPORÁRIA de equipamentos para eventos, transmissões, vídeo conferências
   - "Requisição > Equipamentos > Hardware > Montagem de Setup > Transmissão/Vídeo Conferência" = montagem de equipamentos para transmissão/vídeo conferência em eventos
   - Use para: eventos, transmissões, vídeo conferências, premiações, cerimônias que requerem montagem temporária de equipamentos (microfone, câmera, áudio, vídeo)
   - Palavras-chave: "transmissão", "vídeo conferência", "evento", "apoio", "montagem", "setup", "premiação", "cerimônia", "auditório", "interação", "microfone", "câmera", "áudio", "vídeo", "solicitação de serviço", "acompanhamento"
   - EXEMPLO ESPECÍFICO: "Solicitação de Serviço - APOIO para transmissão de premiação" → "TI > Requisição > Equipamentos > Hardware > Montagem de Setup > Transmissão/Vídeo Conferência"
   - IMPORTANTE: Distinga de "Mudança > Gestão de Mudança > Programada > Instalação de Equipamento"
     * Montagem de Setup = TEMPORÁRIA para eventos/ocasiões especiais
     * Instalação de Equipamento = PERMANENTE para infraestrutura
5. "Requisição > Software" = solicitação de software (instalação, atualização, licenciamento)
   - Use para: instalar software, atualizar software, renovar licença
   - Palavras-chave: "instalar", "atualizar", "licença", "licenciamento"
"""

INCIDENT_DISTINCTIONS = """DISTINÇÕES PARA INCIDENTES:
1. "Incidente > Acesso > AD > Rede / Wi-Fi - Sem Conexão" = problema de CONEXÃO Wi-Fi/rede (sem acesso, não conecta)
   - Use para: usuário não consegue conectar na rede Wi-Fi, problema de conexão
   - Palavras-chave: "não conecta", "sem conexão", "Wi-Fi não funciona", "rede não conecta"
   - IMPORTANTE: Distinga de "Incidente > Equipamentos > Hardware > Infraestrutura de Rede" (problema físico)
2. "Incidente > Equipamentos > Hardware > Infraestrutura de Rede" = problema com EQUIPAMENTO FÍSICO de rede (switch, roteador, cabo, ponto de rede)
   - Use para: switch com falha, roteador não funciona, cabo com problema, ponto de rede inoperante
   - Palavras-chave: "switch com falha", "roteador não funciona", "cabo de rede", "ponto de rede", "equipamento de rede"
   - IMPORTANTE: Distinga de "Incidente > Acesso > AD > Rede / Wi-Fi - Sem Conexão" (problema de conexão/permissão)
3. "Incidente > Equipamentos" = problema com equipamento existente (não liga, travando, lentidão, etc.)
   - Use para: equipamento com problema, não funciona, travando, lentidão
   - Palavras-chave: "não funciona", "não liga", "travando", "lentidão", "erro"
   - IMPORTANTE: Em Incidente use "Impressoras" (plural), em Requisição use "Impressora" (singular)
4. "Incidente > Software" = problema com software (erro, travamento, desempenho lento, etc.)
   - Use para: software com erro, travando, desempenho lento, falha ao abrir
   - Palavras-chave: "erro", "travando", "lento", "não abre", "falha\""""

CHANGE_DISTINCTIONS = """DISTINÇÕES PARA MUDANÇAS:
1. "Mudança > Gestão de Mudança > Programada > Instalação de Equipamento" = instalação PERMANENTE de infraestrutura (servidor, rede permanente, nova infraestrutura)
   - Use para: instalação permanente de servidores, equipamentos de rede, infraestrutura nova
   - Palavras-chave: "instalar servidor", "nova infraestrutura", "rede permanente", "instalação permanente"
   - IMPORTANTE: Distinga de "Requisição > Equipamentos > Hardware > Montagem de Setup" (temporário para eventos)
2. "Mudança > Gestão de Mudança > Programada > Atualização de Sistema" = atualização permanente de sistema/aplicação
   - Use para: atualizações de sistema que alteram infraestrutura permanentemente
   - Palavras-chave: "atualização de sistema", "upgrade permanente", "migração"
3. "Mudança > Gestão de Mudança > Programada > Alteração de Configuração" = alteração permanente de configuração de infraestrutura
   - Use para: mudanças permanentes em configurações de servidores, redes, sistemas
   - Palavras-chave: "alterar configuração", "mudança de configuração permanente"
4. "Mudança > Gestão de Mudança > Emergencial" = mudanças emergenciais/críticas
   - Use para: correções críticas, recuperação de servidor/VM, intervenção emergencial em rede
   - Palavras-chave: "emergência", "crítico", "recuperação", "intervenção emergencial"
"""

GENERAL_DISTINCTIONS = """DISTINÇÃO CRÍTICA GERAL - DECISÃO INICIAL:
Para decidir entre Requisição, Incidente ou Mudança, siga esta ordem:

1. É uma MUDANÇA PERMANENTE na infraestrutura? (instalação permanente, atualização de sistema, alteração de configuração permanente)
   → Use: "TI > Mudança > Gestão de Mudança > [Programada/Emergencial] > [Tipo específico]"

2. É uma SOLICITAÇÃO? (novo equipamento, acesso, instalação de software, montagem temporária para eventos)
   → Use: "TI > Requisição > [Área] > [Subárea] > [Categoria Específica]"

3. É um PROBLEMA/ERRO? (não funciona, erro, travando, indisponível, sem acesso)
   → Use: "TI > Incidente > [Área] > [Subárea] > [Categoria Específica]"

REGRAS DE DISTINÇÃO:
- "Requisição > Acesso" = acesso a INFRAESTRUTURA (AD, rede, VPN)
- "Requisição > Sistemas > Acesso a Sistema" = acesso a SISTEMAS/APLICAÇÕES específicos (Anews, Salesforce, etc.)
- "Requisição > Equipamentos > Hardware > Montagem de Setup" = montagem TEMPORÁRIA para eventos/transmissões
- "Mudança > Instalação de Equipamento" = instalação PERMANENTE de infraestrutura
- "Requisição" = solicitação | "Incidente" = problema | "Mudança" = alteração PERMANENTE na infraestrutura"""

# ==================== FUNÇÕES ====================

def get_classification_prompt(categories_text: str, title: str, content: str) -> str:
    """
    Retorna o prompt para classificação de tickets com categoria existente.
    """
    classification_rules = f"""Categorias disponíveis (formato: Nível 1 > Nível 2 > Nível 3 > ...):
{categories_text}
Analise o seguinte ticket e classifique-o na categoria MAIS ESPECÍFICA e APROPRIADA da lista acima.
REGRAS CRÍTICAS:
- SEMPRE prefira categorias com MAIS NÍVEIS (mais específicas) quando disponíveis
- Se o ticket menciona um sistema/aplicação específico (ex: Anews, Arion, GLPI, AD, etc.), DEVE usar uma categoria que inclua esse sistema
- NUNCA escolha uma categoria genérica se existir uma subcategoria mais específica que se encaixe melhor
- USE O NOME EXATO da categoria da lista acima - NÃO invente ou modifique nomes de sistemas/aplicações
- Se existe "Anews / Arion" na lista, USE "Anews / Arion" - NÃO use apenas "Anews" ou "Arion"
- Só retorne uma categoria se ela se encaixar PERFEITAMENTE no contexto do ticket
- Se a categoria mais próxima for muito genérica ou não mencionar sistemas/aplicações do ticket, responda "Nenhuma\""""

    return f"""{INTRO}
{classification_rules}
{GENERAL_DISTINCTIONS}
{PROBLEM_DISTINCTIONS}
{REQUEST_DISTINCTIONS}
{INCIDENT_DISTINCTIONS}
{CHANGE_DISTINCTIONS}
Título: {title}
Conteúdo: {content}
Responda APENAS com o caminho completo da categoria EXATA da lista acima (ex: "TI > Incidente > Sistemas > Indisponibilidade de Sistema > Anews / Arion") e o ID entre parênteses (ex: "(84)").
IMPORTANTE: Use o nome EXATO do sistema/aplicação como aparece na lista.
Se não encontrar uma categoria adequada e específica, responda "Nenhuma".
Formato da resposta:
CATEGORIA: [caminho completo EXATO da lista]
ID: [número do ID]"""


def get_suggestion_prompt(
    categories_text: str,
    similar_categories: list,
    title: str,
    content: str
) -> str:
    """
    Retorna o prompt para geração de sugestão de nova categoria.
    """
    similar_ref = ""
    if similar_categories:
        similar_ref = f"\n\nCategorias similares existentes (use como referência para nomes e estrutura):\n" + "\n".join([f"- {cat}" for cat in similar_categories])

    mandatory_analysis = """ANÁLISE OBRIGATÓRIA ANTES DE SUGERIR (SIGA ESTA ORDEM EXATA):
1. O ticket menciona "evento", "transmissão", "vídeo conferência", "premiação", "cerimônia", "apoio", "solicitação de serviço - apoio", "acompanhamento de transmissão", "montagem", "setup", "auditório", "interação", "microfone", "câmera", "áudio", "vídeo"?
   → SEMPRE use: "TI > Requisição > Equipamentos > Hardware > Montagem de Setup > Transmissão/Vídeo Conferência"
2. O ticket menciona instalação permanente de infraestrutura (servidor, rede permanente, nova infraestrutura)?
   → Use: "TI > Mudança > Gestão de Mudança > Programada > Instalação de Equipamento"
3. O ticket menciona problema com equipamento existente (não funciona, erro, travando, não liga)?
   → Use: "TI > Incidente > Equipamentos"
4. O ticket menciona solicitação de novo equipamento permanente (computador, impressora, servidor)?
   → Use: "TI > Requisição > Equipamentos > Hardware"
5. O ticket menciona instalação de software (Adobe, Office, etc.)?
   → Use: "TI > Requisição > Software > Instalação"""

    suggestion_rules = """Analise o seguinte ticket e sugira uma categoria hierárquica seguindo o padrão:
TI > [Incidente/Requisição/Mudança] > [Área] > [Subárea] > [Categoria Específica] > [Sistema/Aplicação quando aplicável]
REGRAS IMPORTANTES:
- SEMPRE analise o contexto completo do ticket antes de sugerir categoria
- SEMPRE inclua o sistema/aplicação mencionado no ticket no último nível quando aplicável
- Se existem categorias similares listadas abaixo, USE O NOME EXATO e a ESTRUTURA EXATA como aparece nelas
- Mantenha consistência com nomes de sistemas e estruturas já existentes no sistema"""

    examples = """Exemplos de padrões:
- TI > Requisição > Acesso > AD > Criação de Usuário / Conta
- TI > Incidente > Sistemas > Problema de Acesso > Anews
- TI > Incidente > Sistemas > Indisponibilidade de Sistema > Anews / Arion
- TI > Requisição > Sistemas > Acesso a Sistema > Anews / Arion
- TI > Incidente > Equipamentos > Hardware > Computadores > Não Liga / Travando
- TI > Requisição > Equipamentos > Hardware > Montagem de Setup > Transmissão/Vídeo Conferência"""

    return f"""{INTRO}
{mandatory_analysis}
{GENERAL_DISTINCTIONS}
{suggestion_rules}
{PROBLEM_DISTINCTIONS}
{REQUEST_DISTINCTIONS}
{INCIDENT_DISTINCTIONS}
{CHANGE_DISTINCTIONS}
{similar_ref}
{examples}
Título: {title}
Conteúdo: {content}
Sugira APENAS o caminho completo da categoria seguindo o padrão acima.
IMPORTANTE CRÍTICO:
- Se há categorias similares listadas acima, use o nome EXATO e a ESTRUTURA EXATA como aparece nelas
- Para eventos/transmissões/apoio, SEMPRE use "TI > Requisição > Equipamentos > Hardware > Montagem de Setup > Transmissão/Vídeo Conferência"
- NÃO invente categorias que não seguem o padrão hierárquico correto
- NÃO confunda "Montagem de Setup" (temporário para eventos) com "Instalação de Equipamento" (permanente)
Se não conseguir determinar, responda "Nenhuma".
Formato da resposta:
SUGESTÃO: [caminho completo]"""