# Auto-Ticket

Sistema de classificação automática de tickets do GLPI usando Django REST Framework e Google Gemini AI.

## 📋 Sobre o Projeto

Este projeto automatiza a classificação de tickets do GLPI (Gestionnaire Libre de Parc Informatique) através de:
- **Classificação por IA**: Utiliza Google Gemini AI para análise inteligente do conteúdo dos tickets
- **Integração com n8n**: Webhook para receber tickets do GLPI via n8n
- **Sincronização de categorias**: API para sincronizar categorias hierárquicas do GLPI

## 🚀 Tecnologias

- **Django 5.2** - Framework web
- **Django REST Framework** - API REST
- **Google Gemini AI** - Classificação inteligente de tickets
- **SQLite** - Banco de dados (desenvolvimento)

## 📁 Estrutura do Projeto

```
auto-ticket/
├── backend/              # Aplicação Django
│   ├── accounts/        # App de autenticação
│   ├── core/            # App principal (tickets, categorias)
│   ├── config/          # Configurações do Django
│   └── manage.py
└── README.md
```

## 🛠️ Instalação

### Pré-requisitos

- Python 3.11 ou 3.12
- Git (opcional)

### Setup

1. Clone o repositório:
```bash
git clone https://github.com/seu-usuario/auto-ticket.git
cd auto-ticket
```

2. Entre na pasta do backend:
```bash
cd backend
```

3. Crie e ative um ambiente virtual:
```powershell
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1
```

4. Instale as dependências:
```bash
pip install -r requirements.txt
```

5. Configure as variáveis de ambiente:
Crie um arquivo `.env` na pasta `backend/`:
```env
DJANGO_SECRET_KEY=sua_chave_secreta_aqui
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
GEMINI_API_KEY=sua_chave_gemini_aqui  # Opcional
```

6. Execute as migrações:
```bash
python manage.py migrate
```

7. Crie um superusuário (opcional):
```bash
python manage.py createsuperuser
```

8. Inicie o servidor:
```bash
python manage.py runserver
```

## 🔑 Configuração do Google Gemini (Opcional)

Para usar classificação com IA:

1. Obtenha uma API key gratuita em: https://makersuite.google.com/app/apikey
2. Adicione no arquivo `.env`:
   ```
   GEMINI_API_KEY=sua_chave_aqui
   ```

**Nota**: Se `GEMINI_API_KEY` não estiver configurada, o endpoint de classificação não retornará sugestões. O sistema depende exclusivamente do Google Gemini AI para classificação.

## 📡 Endpoints da API

### Autenticação

Todos os endpoints `/api/*` requerem autenticação por token DRF:
```
Authorization: Token <seu_token_aqui>
```

### Endpoints Disponíveis

- `GET /api/glpi-categories/` - Lista categorias GLPI
- `POST /api/glpi-categories/sync/` - Sincroniza categorias do GLPI via upload CSV (`Nome completo`, `ID`)
- `POST /api/tickets/webhook/` - Webhook para receber tickets do GLPI via n8n
- `POST /api/tickets/classify/` - Classifica um ticket e sugere categoria
- `GET /api/category-suggestions/` - Lista sugestões de categorias pendentes
- `POST /api/category-suggestions/preview/` - Gera prévia de sugestão de categoria (sem salvar)
- `POST /api/category-suggestions/<id>/approve/` - Aprova uma sugestão de categoria
- `POST /api/category-suggestions/<id>/reject/` - Rejeita uma sugestão de categoria

Para mais detalhes, consulte o [README do backend](backend/README.md).

## 🔄 Fluxo de Trabalho

1. **Recebimento de Ticket**: n8n envia ticket do GLPI via webhook
2. **Classificação**: Sistema classifica o ticket usando IA (Gemini)
   - Se encontrar categoria exata: retorna sugestão e atualiza ticket
   - Se não encontrar: gera sugestão de nova categoria e salva para revisão manual
3. **Atualização**: Ticket é atualizado com a categoria sugerida (se encontrada)
4. **Tickets não classificados**: Status alterado para "Aprovação" (status 10) no GLPI
5. **Revisão de Sugestões**: Administrador revisa sugestões no Django Admin e aprova/rejeita

## 📝 Licença

Este projeto é privado e de uso interno.

## 👥 Contribuidores

- Desenvolvido para automatizar a classificação de tickets do GLPI

---

Para mais informações sobre o backend, consulte [backend/README.md](backend/README.md).

