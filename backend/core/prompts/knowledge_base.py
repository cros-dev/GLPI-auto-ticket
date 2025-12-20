"""
Prompts para geração de artigos de Base de Conhecimento usando Google Gemini AI.

Este módulo contém os templates de prompts utilizados para geração de artigos
de Base de Conhecimento do GLPI.
"""

# ==================== PARTES COMUNS ====================

INTRO = """Você é um assistente técnico responsável por criar artigos de Base de Conhecimento para o GLPI, voltados ao suporte técnico."""

MANDATORY_RULES = """REGRAS OBRIGATÓRIAS:
- Linguagem técnica e corporativa
- Sem emojis
- Texto claro, objetivo e padronizado
- Público-alvo: técnicos de TI e broadcast
- Não inventar informações
- Usar apenas o contexto fornecido
- Estrutura compatível com artigos de Base de Conhecimento do GLPI
- Manter consistência com o padrão de artigos técnicos corporativos
- IMPORTANTE: Gerar APENAS UM artigo do tipo especificado, ignorando qualquer menção no contexto sobre criar múltiplos artigos"""

CONCEPTUAL_STRUCTURE = """ARTIGO CONCEITUAL:
- Título: **Base de Conhecimento — [Tema Principal]** (em negrito usando **)
- Seção: **Objetivo** (título em negrito)
  - Uma frase clara sobre o que o artigo documenta
- Seção: **[Componente Principal]** (ex: **Servidores**, **Sistemas**, **Equipamentos**, **Infraestrutura** - título em negrito)
  - Subseções conforme necessário (também em negrito)
  - Características técnicas
  - Funções e responsabilidades
- Seção: **Fluxo Geral** (se aplicável - título em negrito)
  - Passos numerados do fluxo (1., 2., 3., ...)
- Seção: **Observações** (se necessário - título em negrito)
- NÃO incluir passo a passo operacional
- Usar seções bem definidas com títulos descritivos em negrito"""

OPERATIONAL_STRUCTURE = """ARTIGO OPERACIONAL:
- Título: **Base de Conhecimento — [Procedimento Específico]** (em negrito usando **)
- Seção: **Objetivo** (título em negrito)
  - Uma frase clara sobre o que o procedimento realiza
- Seção: **Servidores/Sistemas Aplicáveis** (se aplicável - título em negrito)
- Seção: **Procedimento de [Nome do Procedimento]** (título em negrito)
  - Passos numerados (1., 2., 3., ...)
  - Cada passo deve ser claro e objetivo
  - Indicar claramente onde inserir prints: "Inserir print da tela [localização exata]"
  - Não descrever a imagem, apenas indicar o local
- Seção: **Resultado Esperado** (título em negrito)
  - Descrever o resultado final esperado após o procedimento
- Seção: **Observações** (título em negrito)
  - Informações técnicas relevantes
  - Pontos de atenção
  - Dependências ou pré-requisitos"""

TROUBLESHOOTING_STRUCTURE = """ARTIGO TROUBLESHOOTING:
- Título: **Base de Conhecimento — [Problema/Diagnóstico]** (em negrito usando **)
- Seção: **Objetivo** (título em negrito)
  - Descrever o problema que o artigo ajuda a resolver
- Seção: **Sintomas** (título em negrito)
  - Lista de sintomas ou indicadores do problema
- Seção: **Causas Possíveis** (título em negrito)
  - Lista de causas potenciais
- Seção: **Procedimento de Diagnóstico** (título em negrito)
  - Passos numerados para identificar a causa
- Seção: **Solução** (título em negrito)
  - Passos numerados para resolver o problema
  - Indicar prints quando necessário
- Seção: **Verificação** (título em negrito)
  - Como verificar se o problema foi resolvido
- Seção: **Observações** (título em negrito)
  - Informações adicionais relevantes"""

FORMATTING_RULES = """FORMATAÇÃO DE TEXTOS:
- OBRIGATÓRIO: Use títulos de seções em negrito usando formato Markdown: **Título da Seção**
- OBRIGATÓRIO: Use o título principal do artigo em negrito: **Base de Conhecimento — [Tema]**
- Use subtítulos para seções principais (também em negrito)
- Use listas numeradas (1., 2., 3., ...) para procedimentos e fluxos
- Use listas com marcadores (* ou -) para características ou itens
- Mantenha parágrafos curtos e objetivos
- Use termos técnicos corretos e consistentes
- IMPORTANTE: Todos os títulos de seções devem estar em negrito usando **texto**"""

IMAGE_RULES = """IMAGENS:
- Quando necessário, apenas indicar: "Inserir print da tela [localização exata]"
- Exemplos:
  * "Inserir print da tela Ferramentas → Integração"
  * "Inserir print da tela Configurações → Dispositivos → [Nome do Dispositivo]"
  * "Inserir print da tela [Menu] → [Submenu] → [Opção]"
- Não descrever o conteúdo da imagem, apenas o local onde deve ser inserida
- Adapte os exemplos conforme o software/sistema documentado"""

EXAMPLES = """EXEMPLOS DE ESTRUTURA (apenas referência - adapte conforme o contexto fornecido):

EXEMPLO CONCEITUAL - Ambiente de Broadcast:

**Base de Conhecimento — Visão Geral do Ambiente de Jornal**

**Objetivo**
Documentar a arquitetura e o fluxo de funcionamento do ambiente de jornal, incluindo servidores, sistemas e componentes envolvidos.

**Servidores de Playout**
[Descrição dos servidores e suas funções]

**Servidor de Arquivos**
[Descrição do servidor e suas funções]

**Sistema Editorial**
[Descrição do sistema e suas funções]

**Fluxo Geral**
1. [Passo 1 do fluxo]
2. [Passo 2 do fluxo]
[...]

**Observações**
[Informações técnicas relevantes, se necessário]

EXEMPLO OPERACIONAL - Configuração de Equipamento:

**Base de Conhecimento — Configuração de [Equipamento/Sistema]**

**Objetivo**
Documentar o procedimento de configuração de [equipamento/sistema] para [objetivo específico].

**Servidores/Sistemas Aplicáveis**
[lista de servidores ou sistemas onde o procedimento se aplica]

**Procedimento de Configuração**
1. [Primeiro passo]
   - [Subpasso detalhado]
   - [Subpasso detalhado]
   - Inserir print da tela [localização exata]

2. [Segundo passo]
   - [Subpasso detalhado]
   - Inserir print da tela [localização exata]

**Resultado Esperado**
[Descrição do resultado esperado após a configuração]

**Observações**
[Informações técnicas relevantes, pontos de atenção, dependências]"""

FINAL_INSTRUCTIONS = """INSTRUÇÕES FINAIS:
- CRÍTICO: Gere APENAS UM artigo do tipo especificado no campo "TIPO DE ARTIGO SOLICITADO"
- NÃO gere múltiplos artigos, mesmo que o contexto mencione "duas bases de conhecimento" ou "vários artigos"
- Se o tipo for "conceitual", gere APENAS o artigo conceitual sobre a arquitetura/visão geral
- Se o tipo for "operacional", gere APENAS o artigo operacional sobre procedimentos
- Se o tipo for "troubleshooting", gere APENAS o artigo de troubleshooting
- Use apenas as informações fornecidas no contexto
- Mantenha linguagem técnica e profissional
- O artigo deve estar pronto para ser copiado e colado diretamente no GLPI
- NÃO adicione texto introdutório como "A seguir são apresentados..." ou "Segue o artigo..."
- NÃO adicione metadados ou explicações antes do artigo
- Comece DIRETAMENTE com o título do artigo em negrito: **Base de Conhecimento — [Tema]**
- Certifique-se de que todos os passos estão numerados corretamente (se operacional)
- Inclua todas as seções obrigatórias conforme o tipo de artigo
- Todos os títulos de seções devem estar em negrito usando **texto**

Gere agora APENAS o artigo do tipo especificado, começando DIRETAMENTE com o título em negrito, sem nenhum texto introdutório."""

# ==================== FUNÇÕES ====================

def get_knowledge_base_prompt(
    article_type: str,
    category: str,
    context: str
) -> str:
    """
    Retorna o prompt para geração de artigos de Base de Conhecimento.
    
    Args:
        article_type: Tipo do artigo ('conceitual', 'operacional' ou 'troubleshooting')
        category: Categoria da Base de Conhecimento (ex: "RTV > AM > TI > Suporte > Técnicos > Jornal / Switcher > Playout")
        context: Contexto do ambiente, sistemas, servidores, softwares envolvidos
        
    Returns:
        str: Prompt formatado para geração de artigo de Base de Conhecimento
    """
    return f"""{INTRO}

{MANDATORY_RULES}

CATEGORIA DA BASE DE CONHECIMENTO:
{category}

TIPO DE ARTIGO SOLICITADO:
{article_type}

IMPORTANTE: Você deve gerar APENAS UM artigo do tipo "{article_type}". 
Se o contexto mencionar a necessidade de múltiplos artigos, IGNORE essa sugestão e gere apenas o artigo do tipo especificado acima.

CONTEXTO DO AMBIENTE:
{context}

ESTRUTURA OBRIGATÓRIA POR TIPO DE ARTIGO:

{CONCEPTUAL_STRUCTURE}

{OPERATIONAL_STRUCTURE}

{TROUBLESHOOTING_STRUCTURE}

{FORMATTING_RULES}

{IMAGE_RULES}

{EXAMPLES}

{FINAL_INSTRUCTIONS}"""
