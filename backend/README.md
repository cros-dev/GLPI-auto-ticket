# auto-ticket (backend)

Este diretório contém o backend Django do projeto `auto-ticket`.

## Pré-requisitos

- Python 3.11/3.12
- Git (opcional)

Recomenda-se usar uma virtualenv para isolar dependências.

## Setup rápido (Windows / PowerShell)

Abra o PowerShell na pasta `backend/` e execute:

```powershell
# (opcional) criar venv se ainda não existir
python -m venv venv

# ativar venv (pode precisar ajustar ExecutionPolicy)
.\venv\Scripts\Activate.ps1

# instalar dependências
pip install -r requirements.txt

# criar/migrar banco
python manage.py migrate

# criar superuser (opcional)
python manage.py createsuperuser

# rodar servidor de desenvolvimento
python manage.py runserver
```

Se o PowerShell bloquear execução de scripts, execute (uma vez):

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## Arquivos importantes

- `manage.py` — utilitário Django
- `config/` — projeto Django (settings, urls, wsgi/asgi)
- `core/` — app principal com modelos e endpoints iniciais
- `requirements.txt` — dependências do ambiente
- `.gitignore` — padrões para ignorar arquivos

## Autenticação

Todos os endpoints `/api/*` requerem autenticação por token DRF. Use o header:

```
Authorization: Token <seu_token_aqui>
```

**Token para n8n**: `b0cdfd8b96b6d643a94278785678483c44ce8e3c`

### Obter token

Para obter um novo token, faça um POST em `/api/accounts/token/` com username e password:

```powershell
curl -X POST http://localhost:8000/api/accounts/token/ `
  -H "Content-Type: application/x-www-form-urlencoded" `
  -d "username=seu_usuario&password=sua_senha"
```

Resposta:
```json
{"token":"<seu_token_aqui>"}
```

Ou use o shell Django para gerar/consultar tokens:

```powershell
python manage.py shell
```

Dentro do shell:
```python
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

User = get_user_model()
u = User.objects.get(username='seu_usuario')
t, created = Token.objects.get_or_create(user=u)
print(t.key)
```

## Endpoints API implementados

- `GET /api/glpi-categories/`
  - Retorna lista de categorias GLPI salvas localmente.

- `POST /api/glpi-categories/sync/`
  - Recebe um arquivo CSV exportado do GLPI (colunas `Nome completo` e `ID`) e faz upsert no banco, preservando os IDs originais.
  - Exemplo de uso (PowerShell):

```powershell
curl -X POST http://localhost:8000/api/glpi-categories/sync/ `
  -H "Authorization: Token b0cdfd8b96b6d643a94278785678483c44ce8e3c" `
  -F "file=@categorias_glpi.csv"
```

- `POST /api/tickets/classify/`
  - Classifica um ticket e sugere categoria usando Google Gemini AI (quando disponível). Sem IA configurada, nenhum resultado é retornado.
  - Se não encontrar categoria exata, gera uma sugestão de nova categoria e salva para revisão manual.
  - Payload esperado:

```json
{
  "title": "Impressora não funciona",
  "content": "A impressora do setor não puxa papel...",
  "glpi_ticket_id": 123
}
```

Resposta de exemplo (categoria encontrada):

```json
{
  "suggested_category_name": "TI > Incidente > Equipamentos > Hardware > Impressoras > Não Imprime",
  "suggested_category_id": 15,
  "confidence": "high",
  "classification_method": "ai",
  "ticket_type": 1,
  "ticket_type_label": "incidente"
}
```

Resposta de exemplo (categoria não encontrada - status 400):

```json
{
  "detail": "Não foi possível classificar o ticket. Verifique se há categorias cadastradas. Uma sugestão de categoria foi criada e está aguardando revisão no admin."
}
```

- `GET /api/category-suggestions/`
  - Lista todas as sugestões de categorias geradas pela IA, com filtros por status (pending, approved, rejected).

- `POST /api/category-suggestions/preview/`
  - Gera uma prévia de sugestão de categoria sem salvar no banco. Útil para testar e validar antes de criar categorias no GLPI.
  - Payload esperado:

```json
{
  "title": "Apoio para transmissão",
  "content": "Preciso de suporte para montagem de setup de vídeo conferência..."
}
```

Resposta:

```json
{
  "suggested_path": "TI > Requisição > Administrativo > Montagem de Setup > Transmissão/Vídeo Conferência",
  "ticket_type": 2,
  "ticket_type_label": "requisição",
  "note": "Esta é apenas uma prévia. Para salvar a sugestão, use o endpoint de classificação de ticket."
}
```

- `POST /api/category-suggestions/<id>/approve/`
  - Aprova uma sugestão de categoria pendente.

- `POST /api/category-suggestions/<id>/reject/`
  - Rejeita uma sugestão de categoria pendente.

## Integração com n8n (exemplo rápido)

No n8n, após extrair os campos do e-mail (como seu código JS), envie um POST para o endpoint `classify-email` com o JSON mostrado acima e **inclua o token no header**.

### Configuração no n8n

1. Crie ou abra um nó "HTTP Request".
2. Defina:
   - **Method**: POST
   - **URL**: `http://localhost:8000/api/classify-email/`
   - **Headers**: `Authorization: Token b0cdfd8b96b6d643a94278785678483c44ce8e3c`
   - **Body**: JSON com `from_email`, `to_email`, `subject`, `body`
3. Salve e teste.

Exemplo JSON para o body:

```json
{
  "from_email": "user@example.com",
  "to_email": "helpdesk@example.com",
  "subject": "Problema com impressora",
  "body": "A impressora do setor não puxa papel..."
}
```

Se quiser sincronizar as categorias do GLPI, o n8n pode chamar `POST /api/glpi-categories/sync/` com a lista de categorias obtidas do GLPI.

### Exemplos de teste (curl)

**Classificar um e-mail**:
```powershell
curl -X POST http://localhost:8000/api/classify-email/ `
  -H "Authorization: Token b0cdfd8b96b6d643a94278785678483c44ce8e3c" `
  -H "Content-Type: application/json" `
  -d "{\"from_email\":\"user@example.com\",\"subject\":\"Impressora\",\"body\":\"Não funciona\"}"
```

**Listar categorias GLPI**:
```powershell
curl -X GET http://localhost:8000/api/glpi-categories/ `
  -H "Authorization: Token b0cdfd8b96b6d643a94278785678483c44ce8e3c"
```

**Sincronizar categorias do GLPI (via CSV)**:
```powershell
curl -X POST http://localhost:8000/api/glpi-categories/sync/ `
  -H "Authorization: Token b0cdfd8b96b6d643a94278785678483c44ce8e3c" `
  -F "file=@categorias_glpi.csv"
```

**Gerar prévia de sugestão de categoria**:
```powershell
curl -X POST http://localhost:8000/api/category-suggestions/preview/ `
  -H "Authorization: Token b0cdfd8b96b6d643a94278785678483c44ce8e3c" `
  -H "Content-Type: application/json" `
  -d "{\"title\":\"Problema com impressora\",\"content\":\"A impressora não funciona\"}"
```

### Exemplo em Python (requests)

```python
import requests

url = "http://localhost:8000/api/classify-email/"
headers = {
    "Authorization": "Token b0cdfd8b96b6d643a94278785678483c44ce8e3c",
    "Content-Type": "application/json"
}
payload = {
    "from_email": "user@example.com",
    "to_email": "helpdesk@example.com",
    "subject": "Problema com impressora",
    "body": "A impressora do setor não puxa papel..."
}

response = requests.post(url, json=payload, headers=headers)
print(response.json())
```

## Variáveis de ambiente

Configure as seguintes variáveis de ambiente no arquivo `.env` (incluído no `.gitignore`):

- `DJANGO_SECRET_KEY` — chave secreta do Django (gere com `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`)
- `DJANGO_DEBUG` — True/False
- `DJANGO_ALLOWED_HOSTS` — hosts separados por vírgula
- `GEMINI_API_KEY` — chave para Google Gemini API (opcional, para classificação com IA)
- `GLPI_API_URL` — URL base da API do GLPI (futuro)
- `GLPI_API_TOKEN` — token para autenticação na API do GLPI (futuro)

### Configuração do Google Gemini (Opcional)

Para usar classificação com IA via Google Gemini:

1. Obtenha uma API key gratuita em: https://makersuite.google.com/app/apikey
2. Adicione no arquivo `.env`:
   ```
   GEMINI_API_KEY=sua_chave_aqui
   ```

**Nota**: Se `GEMINI_API_KEY` não estiver configurada, o endpoint de classificação não retorna sugestões. O sistema depende exclusivamente do Google Gemini AI para classificação.

## Funcionalidades Implementadas

✅ **Classificação Automática de Tickets**
- Classificação usando Google Gemini AI
- Geração automática de sugestões quando não encontra categoria exata
- Metadados de classificação (método e confiança) armazenados no ticket

✅ **Sugestões de Categorias**
- Geração automática de sugestões hierárquicas quando categoria exata não é encontrada
- Endpoint de prévia para testar sugestões sem salvar
- Revisão manual via Django Admin
- Aprovação/rejeição de sugestões via API

✅ **Sincronização de Categorias**
- Importação via CSV com preservação de IDs do GLPI
- Suporte a hierarquias complexas (até 6 níveis)
- Tratamento do prefixo "TI" nos caminhos

✅ **Gerenciamento de Tickets Não Classificados**
- Tickets sem classificação são automaticamente marcados com status "Aprovação" (status 10) no GLPI
- Integração com n8n para atualização automática de status

---

**Status**: Sistema completo de classificação automática com IA, geração de sugestões e revisão manual. Pronto para produção.