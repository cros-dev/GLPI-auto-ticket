"""
Mapeamento de palavras-chave para classificação de tickets.

Este módulo contém o dicionário de palavras-chave e sinônimos usados
para classificar tickets automaticamente nas categorias GLPI corretas.

Estrutura: (keyword, synonyms, weight)
- keyword: Palavra-chave que deve aparecer no caminho da categoria
- synonyms: Lista de sinônimos que podem aparecer no texto do ticket
- weight: Peso da correspondência (maior = mais específico)
"""

# Palavras-chave específicas ordenadas por especificidade (mais específicas primeiro)
# Cada item tem: (keyword, synonyms, weight)
KEYWORD_MAPPING = [
    # ===== REQUISIÇÕES =====
    # Requisições de Acesso
    ('acesso remoto / vpn', ['acesso remoto', 'vpn', 'conexão remota', 'acesso vpn', 'conectar remotamente'], 25),
    ('criação de usuário / conta', ['criar usuário', 'criar conta', 'nova conta', 'novo usuário', 'criação de usuário'], 25),
    ('liberação de rede / wi-fi', ['liberar rede', 'liberar wi-fi', 'liberar wifi', 'acesso à rede', 'acesso wi-fi'], 25),
    ('pastas de rede', ['acesso a pasta', 'pasta de rede', 'compartilhamento', 'pasta compartilhada'], 20),
    ('acesso', ['acesso', 'permissão', 'login', 'senha'], 15),
    ('ad', ['ad', 'active directory', 'diretório ativo', 'domínio'], 12),
    
    # Requisições de Equipamentos
    ('novo equipamento', ['novo equipamento', 'novo computador', 'novo notebook', 'novo pc', 'equipamento novo'], 25),
    ('mudança de local', ['mudança de local', 'trocar de lugar', 'mudar localização', 'mudar de sala'], 25),
    ('reparo / substituição', ['reparo', 'substituição', 'trocar', 'consertar', 'manutenção'], 25),
    ('nova impressora / instalação', ['nova impressora', 'instalar impressora', 'configurar impressora'], 25),
    ('solicitação de toner', ['toner', 'solicitar toner', 'preciso de toner', 'toner acabou'], 25),
    ('manutenção / reparo', ['manutenção', 'reparo', 'conserto'], 20),
    ('novo servidor / vm', ['novo servidor', 'nova vm', 'nova máquina virtual', 'criar servidor'], 25),
    ('ajuste de configuração', ['ajuste de configuração', 'configurar servidor', 'ajustar servidor'], 25),
    ('instalação / substituição de equipamento', ['instalar equipamento', 'substituir equipamento', 'novo ponto de rede'], 25),
    ('novo ponto de rede', ['novo ponto de rede', 'instalar ponto', 'ponto de rede novo'], 25),
    ('equipamentos', ['equipamento', 'equipamentos', 'hardware'], 10),
    
    # Requisições de Sistemas
    ('acesso a sistema', ['acesso a sistema', 'acesso ao sistema', 'permissão no sistema', 'acesso sistema'], 25),
    ('atualização / parametrização', ['atualização', 'parametrização', 'atualizar sistema', 'configurar sistema'], 25),
    ('solicitação geral de sistema', ['solicitação de sistema', 'pedido de sistema'], 20),
    ('sistemas', ['sistema', 'sistemas', 'salesforce', 'rp', 'siscom', 'anews', 'arion', 'backstage', 'emam'], 10),
    
    # Requisições de Software
    ('instalação', ['instalar', 'instalação', 'instalar programa', 'instalar software', 'instalar aplicativo'], 25),
    ('atualização', ['atualizar', 'atualização', 'atualizar software', 'atualizar programa'], 25),
    ('licenciamento / renovação', ['licenciamento', 'renovação', 'renovar licença', 'nova licença'], 25),
    ('software', ['software', 'programa', 'aplicativo', 'app'], 10),
    
    # ===== INCIDENTES =====
    # Problemas específicos de impressora
    ('não imprime', ['não imprime', 'não imprimiu', 'não está imprimindo', 'não imprime nada'], 25),
    ('falha de conexão', ['falha de conexão', 'spooler', 'erro de conexão'], 25),
    ('papel preso', ['papel preso', 'papel travado', 'papel enroscado'], 25),
    ('qualidade de impressão', ['qualidade ruim', 'borrão', 'manchado', 'claro demais', 'escuro demais'], 20),
    ('impressoras', ['impressoras', 'impressora', 'printer', 'printers', 'impressão', 'imprimir', 'papel', 'toner', 'tinta'], 20),
    
    # Problemas específicos de computadores
    ('não liga', ['não liga', 'não liga mais', 'não inicia', 'não inicia o computador'], 25),
    ('travando', ['computador travando', 'pc travando', 'notebook travando', 'máquina travando'], 25),  # Mais específico para hardware
    ('lentidão', ['lentidão', 'lento', 'muito lento', 'está lento', 'demora muito'], 25),
    ('tela azul', ['tela azul', 'blue screen', 'erro de sistema', 'crash do sistema'], 25),
    ('falha após atualização', ['falha após atualização', 'problema após atualização', 'erro após atualizar'], 25),
    
    # Problemas de rede/Wi-Fi
    ('sem conexão', ['sem conexão', 'sem internet', 'sem wifi', 'sem wi-fi', 'não conecta', 'não conecta à internet'], 25),
    ('switch / roteador', ['switch', 'roteador', 'router', 'equipamento de rede'], 20),
    ('infraestrutura de rede', ['infraestrutura de rede', 'equipamento de rede', 'ponto de rede'], 15),
    
    # Problemas de servidores
    ('inacessível', ['inacessível', 'sem resposta', 'não responde', 'indisponível'], 25),
    ('serviço indisponível', ['serviço indisponível', 'vm indisponível', 'máquina virtual indisponível'], 25),
    ('servidores', ['servidor', 'servidores', 'server', 'vm', 'virtual', 'máquina virtual'], 15),
    
    # Problemas de acesso/AD
    ('falha de login', ['falha de login', 'senha inválida', 'senha incorreta', 'não consegue fazer login'], 25),
    ('usuário bloqueado', ['usuário bloqueado', 'conta bloqueada', 'conta desativada'], 25),
    ('acesso remoto', ['acesso remoto', 'vpn', 'remoto', 'remote', 'erro de conexão vpn'], 15),
    ('pastas de rede', ['pastas de rede', 'pasta de rede', 'não acessível', 'não consegue acessar pasta'], 20),
    ('ad', ['ad', 'active directory', 'diretório ativo', 'domínio', 'domain'], 12),
    
    # Problemas de sistemas
    ('indisponibilidade de sistema', ['indisponível', 'sistema fora do ar', 'sistema não está funcionando', 'sistema inacessível'], 25),
    ('falha em processo', ['falha em processo', 'erro no processo', 'processo com erro'], 25),
    ('problema geral de sistema', ['problema geral', 'sistema com problema'], 20),
    ('sistema', ['sistema', 'sistemas', 'salesforce', 'rp', 'siscom', 'anews', 'arion', 'backstage', 'emam'], 10),
    
    # Problemas de software
    ('travamento', ['travamento', 'travado', 'travou', 'congelou', 'congelado'], 30),  # Aumentado peso para software
    ('falha ao abrir / travamento', ['falha ao abrir', 'não abre', 'não consegue abrir'], 25),
    ('erro de execução', ['erro de execução', 'erro ao executar', 'não executa'], 25),
    ('desempenho lento', ['desempenho lento', 'software lento', 'programa lento'], 25),
    ('atualização com problema', ['atualização com problema', 'problema após atualizar software'], 25),
    ('office', ['office', 'word', 'excel', 'powerpoint', 'outlook'], 25),  # Software específico tem peso maior
    ('software', ['software', 'programa', 'aplicativo', 'app'], 10),
    
    # Outros equipamentos
    ('periféricos', ['periféricos', 'periférico', 'mouse', 'teclado', 'monitor', 'headset'], 15),
    ('monitor sem sinal', ['monitor sem sinal', 'monitor não liga', 'tela preta'], 25),
    ('mouse com falha', ['mouse com falha', 'mouse não funciona', 'mouse quebrado'], 25),
    ('teclado com falha', ['teclado com falha', 'teclado não funciona', 'teclado quebrado'], 25),
    
    # Genéricos (menor prioridade)
    ('hardware', ['hardware'], 8),
    ('computadores', ['computador', 'computadores', 'notebook', 'pc'], 8),
    ('equipamento', ['equipamento', 'equipamentos'], 5),
    ('incidente', ['incidente'], 3),
    ('requisição', ['requisição', 'solicitação', 'pedido', 'novo'], 3),
]

