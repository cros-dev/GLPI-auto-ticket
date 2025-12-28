"""
Prompts para geração de artigos de Base de Conhecimento usando IA (ex: Google Gemini).

Este módulo contém os templates de prompts utilizados para geração de artigos
de Base de Conhecimento do GLPI, seguindo padrão técnico corporativo.
"""

# ==================== PARTES COMUNS ====================

INTRO = """Você é um assistente técnico responsável por criar artigos de Base de Conhecimento para o GLPI, voltados ao suporte técnico de ambientes de TI e broadcast."""

MANDATORY_RULES = """REGRAS OBRIGATÓRIAS:
- Linguagem técnica, corporativa e profissional
- Sem emojis
- Texto claro, objetivo e padronizado
- Público-alvo: técnicos de TI e broadcast
- Não inventar informações
- Usar exclusivamente o contexto fornecido
- Estrutura compatível com artigos de Base de Conhecimento do GLPI
- Manter consistência com padrão de documentação técnica corporativa
- MODELO MODULAR:
  * Artigos CONCEITUAIS devem ser UNITÁRIOS e isolados por software/sistema/serviço
  * Artigos OPERACIONAIS documentam procedimentos específicos
- NÃO misturar conceitos de sistemas diferentes em um mesmo artigo conceitual
- Cada software/sistema deve possuir seu próprio artigo conceitual separado"""

# ==================== ESCOPO ====================

SCOPE_RULES = """ESCOPO DOS ARTIGOS:

ARTIGOS CONCEITUAIS:
- Devem ter como foco:
  * Softwares
  * Sistemas
  * Serviços lógicos
- Devem explicar O QUE É, PARA QUE SERVE e ONDE É EXECUTADO
- NÃO devem conter passo a passo, configuração ou troubleshooting

SERVIDORES (ex: playout01, playout02):
- DEVEM ser mencionados apenas como CONTEXTO DE EXECUÇÃO
- NÃO devem ser o tema principal de artigos conceituais

COMPONENTES FÍSICOS (placas, portas COM, interfaces):
- NÃO devem gerar artigos conceituais
- Podem ser citados apenas em artigos OPERACIONAIS ou TROUBLESHOOTING
"""

# ==================== ESTRUTURAS ====================

CONCEPTUAL_STRUCTURE = """ARTIGO CONCEITUAL (UNITÁRIO):

Título: **Base de Conhecimento — [Nome do Sistema/Software]**
Categoria: [caminho completo da categoria]

**Objetivo**
Uma frase clara explicando a finalidade do sistema/software
---
**O que é**
Definição técnica e objetiva do sistema/software
---
**Função Principal**
Responsabilidade principal dentro do ambiente
---
**Onde é Executado** (se aplicável)
Ambiente, servidores ou estações onde o sistema roda
Se não for mencionado no contexto, OMITIR esta seção
---
**Integrações Conhecidas** (se aplicável)
Apenas citar integrações, sem descrever fluxo completo
Exemplo: "Integra-se com EMAM e Anews / Arion"
Se não houver integrações conhecidas, OMITIR esta seção
---
**Observações** (se necessário)
Informações técnicas relevantes e específicas
Se não houver observações, OMITIR esta seção completamente (não usar "N/A" ou similar)

IMPORTANTE: Sempre adicionar "---" (três hífens) entre cada seção para separação visual.
A última seção NÃO deve ter "---" após ela.

REGRAS CRÍTICAS:
- Artigo curto, reutilizável e objetivo
- Focar APENAS no sistema do título
"""

OPERATIONAL_STRUCTURE = """ARTIGO OPERACIONAL:

Título: **Base de Conhecimento — [Procedimento Específico]**
Categoria: [caminho completo da categoria]

**Objetivo**
Descrever o que o procedimento realiza
---
**Servidores/Sistemas Aplicáveis**
Informar onde o procedimento se aplica (ex: playout01 e playout02)
---
**Procedimento de [Nome do Procedimento]**
1. Passo numerado claro e direto
2. Passo numerado (continue sequência)
   - Subpasso quando necessário
   - Indicar print: [Inserir print da tela Menu → Submenu → Opção]
3. Continuar passos numerados...

Sempre usar colchetes [ ] ao redor da instrução de print
---
**Resultado Esperado**
Resultado final após execução correta
---
**Observações**
Pontos de atenção, dependências e comportamentos esperados

IMPORTANTE: Sempre adicionar "---" (três hífens) entre cada seção para separação visual.
A última seção NÃO deve ter "---" após ela.
"""

TROUBLESHOOTING_STRUCTURE = """ARTIGO TROUBLESHOOTING:

Título: **Base de Conhecimento — [Problema ou Diagnóstico]**
Categoria: [caminho completo da categoria]

**Objetivo**
Descrever o problema tratado
---
**Sintomas**
Lista de sintomas observáveis
---
**Causas Possíveis**
Lista de causas prováveis
---
**Procedimento de Diagnóstico**
1. Passo numerado para identificar a causa
2. Continuar passos numerados...
---
**Solução**
1. Passo numerado para correção
2. Continuar passos numerados...
   - Indicar prints quando necessário: "Inserir print da tela [localização]"
---
**Verificação**
Como validar se o problema foi resolvido

IMPORTANTE: Sempre adicionar "---" (três hífens) entre cada seção para separação visual.
A última seção NÃO deve ter "---" após ela.

**Observações**
Informações técnicas adicionais
"""

# ==================== FORMATAÇÃO ====================

FORMATTING_RULES = """FORMATAÇÃO:
- Todos os títulos de SEÇÕES devem estar em negrito: **Nome da Seção**
- Os títulos de seções NÃO devem estar dentro de listas com marcadores (* ou -)
- O título do artigo deve estar em negrito: **Base de Conhecimento — [Tema]**
- Imediatamente após o título do artigo, incluir: Categoria: [caminho completo]
- Depois da categoria, iniciar diretamente a primeira seção: **Objetivo**
- **SEMPRE adicionar "---" (três hífens) entre cada seção para separação visual**
- A última seção do artigo NÃO deve ter "---" após ela
- Usar listas numeradas (1., 2., 3.) APENAS dentro das seções de procedimentos
- Parágrafos curtos e objetivos
- NÃO usar marcadores de lista (* ou -) antes dos títulos de seções
"""

IMAGE_RULES = """IMAGENS:
- Quando necessário, indicar o local usando o formato:
  [Inserir print da tela Menu → Submenu → Opção]
- Sempre usar colchetes [ ] ao redor da instrução completa
- Exemplos:
  * [Inserir print da tela Ferramentas → Integração]
  * [Inserir print da tela Dispositivos → DeckLink Studio 4K → Tally]
- Não descrever o conteúdo da imagem
- Não usar termos genéricos como "imagem acima"
"""

# ==================== INSTRUÇÕES FINAIS ====================

def get_final_instructions(article_type: str, category: str) -> str:
    """Retorna as instruções finais formatadas com o tipo e categoria."""
    return f"""INSTRUÇÕES FINAIS:

- Analise o contexto fornecido
- Gere APENAS o tipo de artigo solicitado ({article_type})
- Se o tipo for "conceitual":
  * Identifique todos os softwares/sistemas mencionados
  * Gere UM artigo CONCEITUAL UNITÁRIO para cada software/sistema identificado
  * Categoria: {category} > [Nome do Sistema]
- Se o tipo for "operacional":
  * Identifique procedimentos específicos mencionados no contexto
  * Gere UM artigo OPERACIONAL para cada procedimento identificado
  * Categoria: usar a categoria base ({category})
  * Foque em passos numerados e instruções práticas
  * Se o contexto mencionar prints ou telas específicas, inclua instruções para inserir prints
- Se o tipo for "troubleshooting":
  * Identifique problemas ou situações de diagnóstico mencionadas
  * Gere UM artigo TROUBLESHOOTING para cada problema identificado
  * Categoria: usar a categoria base ({category})
- Separar cada artigo com DUAS linhas em branco
- NÃO adicionar introduções ou explicações fora dos artigos
- NÃO adicionar metadados
- Usar apenas informações do contexto
- Texto pronto para copiar e colar no GLPI
"""

# ==================== FUNÇÃO PRINCIPAL ====================

def get_knowledge_base_prompt(
    article_type: str,
    category: str,
    context: str
) -> str:
    """
    Retorna o prompt completo para geração de artigos de Base de Conhecimento no GLPI.
    
    Args:
        article_type: Tipo do artigo ('conceitual', 'operacional' ou 'troubleshooting')
        category: Categoria base da Base de Conhecimento (ex: "RTV > AM > TI > Suporte > Técnicos > Jornal / Switcher")
        context: Contexto do ambiente, sistemas, servidores, softwares envolvidos
        
    Returns:
        str: Prompt formatado para geração de artigo(s) de Base de Conhecimento
    """
    return f"""{INTRO}

{MANDATORY_RULES}

{SCOPE_RULES}

CATEGORIA BASE:
{category}

TIPO DE ARTIGO SOLICITADO:
{article_type}

REGRAS CRÍTICAS POR TIPO:

- Se o tipo for "conceitual": Gere APENAS artigos conceituais. Foque em explicar O QUE É, PARA QUE SERVE e ONDE É EXECUTADO. NÃO inclua passos ou procedimentos.

- Se o tipo for "operacional": Gere APENAS artigos operacionais com procedimentos passo a passo. Foque em COMO FAZER. NÃO inclua explicações conceituais extensas. Se o contexto mencionar procedimentos específicos (como configurações, passos, prints), documente-os detalhadamente.

- Se o tipo for "troubleshooting": Gere APENAS artigos de troubleshooting. Foque em problemas, sintomas, causas e soluções. NÃO inclua explicações conceituais ou procedimentos operacionais gerais.

IMPORTANTE: Respeite rigorosamente o tipo solicitado. NÃO gere múltiplos tipos de artigo. Gere APENAS o tipo solicitado.

CONTEXTO DO AMBIENTE:
{context}

ESTRUTURAS OBRIGATÓRIAS:

{CONCEPTUAL_STRUCTURE}

{OPERATIONAL_STRUCTURE}

{TROUBLESHOOTING_STRUCTURE}

{FORMATTING_RULES}

{IMAGE_RULES}

{get_final_instructions(article_type, category)}
"""
