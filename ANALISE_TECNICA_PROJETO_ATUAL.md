## 1. Visão Geral do Projeto
- Objetivo do sistema: Automatizar classificação de tickets GLPI, sugerir/espelhar categorias, gerar artigos de base de conhecimento e coletar pesquisa de satisfação, integrando-se a GLPI (legacy API) e n8n; frontend Angular para operação e revisão.
- Tipo de aplicação: Backend Django REST (API) + frontend Angular SPA; integrações externas (GLPI Legacy API, Google Gemini AI, webhooks n8n).
- Público-alvo: Equipes de suporte/operadores GLPI e revisores de categorias/artigos.
- Contexto corporativo: Ambiente ITSM/GLPI com automação via IA e orquestração n8n; autenticação via token DRF; consumo interno.

## 2. Estrutura do Projeto
- Pastas principais:
  - `backend/`: Django (apps `accounts`, `core`, `config`).
    - `config/`: settings/urls/asgi/wsgi.
    - `accounts/`: endpoints de token DRF (app básico).
    - `core/`: models (tickets, categorias, sugestões, KB, surveys), services (regras de negócio e IA), clients (GLPI legacy, Gemini, n8n), serializers, views, prompts, utils, templates de survey.
  - `frontend/`: Angular (guards, interceptors, services, componentes UI).
  - `docker/`: compose e Dockerfile.
- Responsabilidade por camada:
  - Models/serializers/views (Django REST) seguindo DRF.
  - Services centralizam regras de classificação, sugestão, KB, survey.
  - Clients encapsulam integrações externas (GLPI legacy API, Gemini, n8n).
  - Frontend: `auth.interceptor` injeta token; `auth.guard` protege rotas; `api.service` consome endpoints de sugestões/KB/sync.
- Avaliação da organização: Estrutura clara e separação razoável; prompts e parsers isolados; integrações encapsuladas. App `accounts` ainda vazio (model/view), apenas URL de token.

## 3. Padrões Arquiteturais Identificados
- Uso de Django + DRF (APIView, generics) com serializers e models; Service Layer para regras de negócio em `core/services.py`.
- Clients dedicados para integrações externas (GLPI Legacy, Gemini, n8n) encapsulam auth/chamadas/erros.
- Padrão REST simples; autenticação Token DRF em `/api/*`; sessões CSRF não usadas para API.
- Angular: interceptor + guard; serviço API centralizado; componentes específicos para UX.
- Consistência geral boa no core; app `accounts` minimalista (sem extensão de User).

## 4. Consistência e Qualidade do Código
- Nomenclatura clara e em português; docstrings extensivas; constantes centralizadas.
- Coesão: services concentram lógica; views finas; serializers adequados. Acoplamento moderado a Django ORM e DRF.
- Reutilização: prompts centralizados, parsers reutilizados; utils para HTML/Markdown.
- Tratamento de erros: clients capturam/propagam; GeminiClient classifica tipos; views retornam status adequados. Ausente padronização de exceções HTTP customizadas; poucos testes (tests.py vazios).
- Código do frontend limpo; usa BehaviorSubject para token; porém sem refresh/expiração/claims.

## 5. Segurança e Autenticação
- Backend: TokenAuthentication + SessionAuthentication habilitados globalmente; permissão padrão `IsAuthenticated` em `/api/*`. Endpoints públicos apenas survey (GET).
- MFA: Não identificado.
- Gestão de segredos via `.env`; `SECRET_KEY` obrigatório; DEBUG controlado.
- CORS restrito a `http://localhost:4200`; permite credenciais.
- Riscos/pontos:
  - Não há throttling/rate limit DRF configurado.
  - SessionAuthentication ligada sem CSRF especial para API; mas uso típico é Token (ok se clientes usarem token).
  - Tokens DRF não expiram (padrão); sem logout server-side/rotina de revogação.
  - `accounts` não customiza usuário/perfis; sem política de senha além dos validators padrão.
  - Frontend armazena token em `localStorage` (vulnerável a XSS).
  - Sem MFA ou SSO corporativo/AD; integração de identidade externa não identificada.

## 6. Pontos Fortes
- Serviços bem separados para IA/classificação, sugestões, KB e survey.
- Clients isolam integrações (GLPI, Gemini, n8n) com logging e validações.
- Prompts e parsing centralizados; lógica de fallback/sugestão estruturada.
- Modelagem cobre tickets, categorias espelho, sugestões, KB e satisfação com tokens anti-fraude.
- Frontend com interceptor/guard e serviço API único; endpoints bem documentados no README.

## 7. Pontos Frágeis e Dívida Técnica
- Ausência de testes automatizados (unit/integration) para services, clients e views.
- Rate limiting e políticas de segurança adicionais não configurados (brute force, abuso de webhooks).
- Tokens DRF sem expiração/rotatividade; SessionAuth habilitada sem necessidade clara.
- Armazenamento do token no frontend em `localStorage` (risco XSS); sem renovação/refresh.
- `accounts` minimalista: sem gestão de usuários/perfis/SSO/AD; sem fluxo de MFA.
- Dependência total do Gemini para classificação (sem fallback local além de sugestão); erro retorna 400/503, mas não há mecanismo alternativo robusto.
- Falta de validação de escopo/permissões por recurso; apenas `IsAuthenticated`.
- Não identificado: hardening HTTP (HSTS, CSP) no Django (só flags SSL quando DEBUG=False).

## 8. Recomendações Técnicas
- Segurança/Identidade: Configurar throttling DRF; considerar expiração/rotatividade de tokens ou migrar para JWT curto com refresh; remover SessionAuth se não usada; avaliar MFA/SSO (AD/IdP) para operadores.
- Frontend: Armazenar token em `sessionStorage` ou usar cookies HttpOnly (se backend suportar); tratar renovação/expiração; monitorar XSS.
- Testes: Criar suíte mínima para services (classificação, sugestão, KB), clients (GLPI, Gemini, n8n com mocks) e views críticas (webhook, classify, approvals).
- Observabilidade: Expandir logging com correlação de requisição; métricas de chamadas externas (timeout/retry/backoff no requests).
- Resiliência: Adicionar fallback de classificação por keywords simples ou regras quando Gemini indisponível; validar timeouts e retries em clients.
- Segurança HTTP: Ativar HSTS/CSP quando em produção (via middleware ou proxy); revisar CORS para domínios reais.
- Governança de dados: Sanitizar/limitar payload salvo em `raw_payload`; validar tamanho/HTML.

## 9. Diretrizes Arquiteturais Extraídas
- Organização de código: Separar regras de negócio em services; integrações em clients dedicados; prompts/parsers centralizados; serializers/views finas.
- Responsabilidade de camadas: Models apenas dados; services fazem orquestração; views chamam services e cuidam do HTTP; frontend usa interceptor/guard para auth e serviço API central.
- Padrões para integrações externas: Clients encapsulam auth, timeouts e parsing; uso de `.env` para chaves e URLs; logging de erros.
- Boas práticas de segurança adotadas: `SECRET_KEY` obrigatório; DEBUG controlado; CSRF/Session cookies seguros em produção; CORS restrito por padrão (dev).
- Ausências a observar: MFA/SSO não identificado; rate limit ausente; tokens sem expiração; teste automatizado inexistente.


