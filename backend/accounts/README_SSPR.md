# 🔐 SSPR - Self-Service Password Reset

## 📋 Status da Implementação

### ✅ **Fase 1: Estrutura Base - CONCLUÍDA**

- [x] Models criados (`ZohoToken`, `SystemAccount`, `PasswordResetRequest`, `OtpToken`)
- [x] Exceções customizadas (`ZohoException`)
- [x] Constantes centralizadas
- [x] `ZohoClient` com gerenciamento automático de tokens
- [x] Configurações no `settings.py`
- [x] Auto-criação de token do .env
- [x] Documentação no `env.example`

### ✅ **Fase 2: Services e API REST - CONCLUÍDA**

- [x] Services de negócio (`request_password_reset`, `generate_otp`, `validate_otp`, `confirm_password_reset`)
- [x] Serializers (validação de entrada e saída)
- [x] Views/Endpoints REST (3 endpoints funcionais)
- [x] URLs mapeadas
- [x] Testes unitários (45 testes cobrindo services e models)

### 🚧 **Próximas Fases**

- [ ] Integração SMS OTP (send_otp_sms ainda é placeholder)
- [ ] Testes de integração/E2E dos endpoints
- [ ] Frontend Angular
- [ ] Integração AD (futuro)

---

## 🚀 Como Começar

### **1. Configurar Credenciais Zoho**

1. **Obter Client ID e Client Secret**:
   - Acesse: https://api-console.zoho.com/
   - Crie um novo app
   - Copie `Client ID` e `Client Secret`

2. **Adicionar no `.env`**:
   ```env
   ZOHO_CLIENT_ID=seu_client_id_aqui
   ZOHO_CLIENT_SECRET=seu_client_secret_aqui
   ```

### **2. Gerar Refresh Token (UMA VEZ)**

1. **Gerar o code (authorization code)**:
   ```
   https://accounts.zoho.com/oauth/v2/auth?
   scope=ZohoMail.organization.READ,ZohoMail.accounts.READ
   &client_id=SEU_CLIENT_ID
   &response_type=code
   &access_type=offline
   &redirect_uri=https://localhost/callback
   ```

2. **Trocar code por tokens**:
   ```bash
   POST https://accounts.zoho.com/oauth/v2/token
   
   grant_type=authorization_code
   &client_id=SEU_CLIENT_ID
   &client_secret=SEU_CLIENT_SECRET
   &code=CODE_RECEBIDO
   &redirect_uri=https://localhost/callback
   ```

3. **Adicionar refresh_token no `.env`**:
   ```env
   ZOHO_REFRESH_TOKEN=seu_refresh_token_aqui
   ```
   
   **Importante**: O `ZohoClient` cria automaticamente no banco na primeira vez que for usado.
   Não é necessário executar nenhum comando manual!

### **3. Executar Migrações**

```bash
python manage.py makemigrations accounts
python manage.py migrate
```

### **4. Pronto!**

O `ZohoClient` criará automaticamente o token no banco na primeira vez que for usado.
Não precisa executar nenhum comando adicional! ✨

---

## 🔑 Como Funciona o Gerenciamento de Tokens

### **Fluxo Automático**

1. **Primeira vez**: Você gera o `code` manualmente (ação humana)
2. **Troca por tokens**: `code` → `refresh_token` + `access_token`
3. **Salva refresh_token**: No banco (via command) ou `.env`
4. **Renovação automática**: `ZohoClient` renova `access_token` quando expira

### **ZohoClient.get_access_token()**

Este método:
- ✅ Verifica se `access_token` ainda é válido
- ✅ Se válido: retorna direto
- ✅ Se expirado: renova automaticamente usando `refresh_token`
- ✅ Salva novo `access_token` no banco

**Você não precisa se preocupar com isso!** O client gerencia tudo automaticamente.

---

## 📝 Exemplo de Uso do ZohoClient

```python
from accounts.clients.zoho_client import ZohoClient
from accounts.exceptions import ZohoException

# Inicializa client (usa settings automaticamente)
client = ZohoClient()

# Obtém access token (renova automaticamente se necessário)
access_token = client.get_access_token()

# Busca dados completos do usuário (novo método - retorna payload completo)
try:
    user_data = client.get_user_by_email("usuario@exemplo.com")
    if user_data:
        print(f"ZUID: {user_data.get('zuid')}")
        print(f"Nome: {user_data.get('displayName')}")
        print(f"Email Principal: {user_data.get('primaryEmailAddress')}")
        # Acesso a todos os campos do payload (telefone, grupos, etc)
except ZohoException as e:
    print(f"Erro: {e.message}")

# Busca apenas o ID do usuário (zuid) - método auxiliar
try:
    zuid = client.get_user_id_by_email("usuario@exemplo.com")
    if zuid:
        print(f"User ID: {zuid}")
except ZohoException as e:
    print(f"Erro: {e.message}")

# Reseta senha de um usuário
try:
    success = client.reset_password(
        email="usuario@exemplo.com",
        new_password="NovaSenh@123"
    )
    if success:
        print("Senha resetada com sucesso!")
except ZohoException as e:
    print(f"Erro: {e.message}")
```

---

## 🏗️ Estrutura Criada

```
backend/accounts/
├── models.py                    # ZohoToken, SystemAccount, PasswordResetRequest, OtpToken
├── exceptions.py                # ZohoException
├── constants.py                 # Constantes do módulo
├── services.py                  # Lógica de negócio (request, generate_otp, validate, confirm)
├── serializers.py               # Serializers para API REST
├── views.py                     # Views/Endpoints REST (3 endpoints)
├── urls.py                      # URLs da API
├── clients/
│   ├── __init__.py
│   └── zoho_client.py           # Cliente Zoho com gerenciamento automático de tokens
├── parsers/
│   ├── __init__.py
│   └── zoho_error_parser.py     # Parser de erros da API Zoho
└── tests/
    ├── test_request_password_reset.py
    ├── test_generate_otp.py
    ├── test_validate_otp.py
    ├── test_confirm_password_reset.py
    └── test_models.py
```

---

## 🔌 Endpoints da API

### 1. Solicitar Reset de Senha
```
POST /api/accounts/password-reset/request/
Content-Type: application/json

{
  "identifier": "usuario@exemplo.com",
  "system": "zoho"
}

Response: 201 Created
{
  "message": "Código OTP enviado via SMS",
  "data": {
    "token": "...",
    "identifier": "usuario@exemplo.com",
    "system": "zoho",
    "status": "pending",
    "created_at": "...",
    "expires_at": "..."
  }
}
```

### 2. Validar OTP
```
POST /api/accounts/password-reset/validate-otp/
Content-Type: application/json

{
  "token": "token_da_solicitacao",
  "otp_code": "123456"
}

Response: 200 OK
{
  "valid": true,
  "token": "...",
  "message": "OTP validado com sucesso..."
}
```

### 3. Confirmar Reset de Senha
```
POST /api/accounts/password-reset/confirm/
Content-Type: application/json

{
  "token": "token_da_solicitacao",
  "new_password": "NovaSenh@123"
}

Response: 200 OK
{
  "success": true,
  "message": "Senha resetada com sucesso!",
  "identifier": "usuario@exemplo.com"
}
```

---

## ⚠️ Próximos Passos

1. **Testar Endpoints**:
   - Testar fluxo completo via Postman/HTTP client
   - Validar integração entre endpoints
   - Verificar tratamento de erros

2. **Integrar SMS OTP**:
   - Escolher provedor (Twilio, AWS SNS, etc)
   - Implementar `send_otp_sms()` com integração real
   - Adicionar credenciais no `.env`

3. **Frontend Angular**:
   - Criar componentes de reset de senha
   - Integrar com os endpoints
   - Implementar UI/UX do fluxo

4. **Melhorias de Segurança**:
   - Rate limiting nos endpoints
   - Auditoria de tentativas
   - Validação de senha forte (além do básico)

5. **Integrar AD** (Futuro):
   - Criar cliente AD similar ao ZohoClient
   - Implementar reset de senha no AD

---

## 🔒 Segurança

- ✅ Refresh token armazenado no banco (pode ser criptografado no futuro)
- ✅ Access token expira automaticamente
- ✅ Renovação automática sem intervenção manual
- ✅ Logs de todas as operações
- ⚠️ **TODO**: Rate limiting, validação de senha forte, auditoria

---

## 📚 Referências

- Padrões do projeto: `backend/core/clients/glpi_client.py`
- Documentação Zoho: https://www.zoho.com/mail/help/api/

