# 🔐 SSPR - Self-Service Password Reset

## 📋 Status da Implementação

### ✅ **Fase 1: Estrutura Base - CONCLUÍDA**

- [x] Models criados (`ZohoToken`, `SystemAccount`, `PasswordResetRequest`, `OtpToken`)
- [x] Exceções customizadas (`ZohoException`, `OtpException`, `PasswordResetException`)
- [x] Constantes centralizadas
- [x] `ZohoClient` com gerenciamento automático de tokens
- [x] Configurações no `settings.py`
- [x] Auto-criação de token do .env
- [x] Documentação no `env.example`

### 🚧 **Próximas Fases**

- [ ] Services de negócio (`request_password_reset`, `generate_otp`, etc)
- [ ] Serializers
- [ ] Views/Endpoints
- [ ] Integração SMS OTP
- [ ] Frontend Angular

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

# Inicializa client (usa settings automaticamente)
client = ZohoClient()

# Obtém access token (renova automaticamente se necessário)
access_token = client.get_access_token()

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
├── exceptions.py                # ZohoException, OtpException, PasswordResetException
├── constants.py                 # Constantes do módulo
└── clients/
    ├── __init__.py
    └── zoho_client.py           # Cliente Zoho com gerenciamento automático de tokens
```

---

## ⚠️ Próximos Passos

1. **Implementar Services**:
   - `request_password_reset()` - Inicia processo
   - `generate_otp()` - Gera código OTP
   - `send_otp_email()` - Envia OTP por email
   - `validate_otp()` - Valida código
   - `reset_password_zoho()` - Executa reset

2. **Implementar Endpoints**:
   - `POST /api/accounts/password-reset/request/`
   - `POST /api/accounts/password-reset/validate-otp/`
   - `POST /api/accounts/password-reset/confirm/`

3. **Integrar SMS OTP** (Fase 2)

4. **Integrar AD** (Fase 3)

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

