# 🚀 Próximos Passos - SSPR

## ✅ O que já foi feito

- [x] Models criados (`ZohoToken`, `SystemAccount`, `PasswordResetRequest`, `OtpToken`)
- [x] Exceptions criadas
- [x] Constants criadas
- [x] `ZohoClient` criado (gerenciamento automático de tokens)
- [x] Admin configurado
- [x] Configurações no `settings.py`
- [x] Migrações executadas
- [x] Variáveis no `.env` configuradas

---

## 🎯 Próximo Passo: **TESTAR ZOHO CLIENT**

Antes de implementar services e endpoints, é importante garantir que o `ZohoClient` está funcionando corretamente.

### **Como testar:**

1. **Execute o script de teste:**
   ```bash
   python manage.py shell
   ```
   
   Dentro do shell:
   ```python
   exec(open('accounts/test_zoho_client.py').read())
   ```

2. **Ou teste manualmente:**
   ```python
   from accounts.clients.zoho_client import ZohoClient
   from accounts.models import ZohoToken
   
   # Verifica se token foi criado do .env
   token = ZohoToken.objects.first()
   print(f"Token no banco: {token}")
   
   # Testa client
   client = ZohoClient()
   access_token = client.get_access_token()
   print(f"Access token: {access_token}")
   ```

### **O que verificar:**

- ✅ Token foi criado automaticamente do `.env` no banco
- ✅ `get_access_token()` retorna um token válido
- ✅ Token é salvo no banco com `expires_at` correto
- ✅ `is_access_token_valid()` retorna `True`

---

## 📋 Após testar o ZohoClient

### **1. Implementar Services** (`backend/accounts/services.py`)

Funções de negócio seguindo padrão do `core/services.py`:

- `request_password_reset(identifier: str, system: str) -> PasswordResetRequest`
  - Cria solicitação de reset
  - Gera token único
  - Valida se usuário existe no sistema
  
- `generate_otp(reset_request: PasswordResetRequest, method: str) -> OtpToken`
  - Gera código OTP de 6 dígitos
  - Salva no banco com expiração
  - Retorna token OTP
  
- `send_otp_email(otp_token: OtpToken) -> bool`
  - Envia OTP por email (TODO: implementar envio real)
  
- `validate_otp(reset_request: PasswordResetRequest, code: str) -> bool`
  - Valida código OTP
  - Incrementa tentativas
  - Atualiza status
  
- `reset_password_zoho(reset_request: PasswordResetRequest, new_password: str) -> bool`
  - Usa `ZohoClient.reset_password()`
  - Atualiza status da solicitação

### **2. Implementar Serializers** (`backend/accounts/serializers.py`)

- `PasswordResetRequestSerializer`
- `OtpValidationSerializer`
- `PasswordResetConfirmSerializer`

### **3. Implementar Views/Endpoints** (`backend/accounts/views.py`)

- `POST /api/accounts/password-reset/request/`
  - Recebe: `identifier` (email), `system` (zoho/ad/both)
  - Retorna: `token` da solicitação
  
- `POST /api/accounts/password-reset/validate-otp/`
  - Recebe: `token`, `code`
  - Retorna: sucesso/erro
  
- `POST /api/accounts/password-reset/confirm/`
  - Recebe: `token`, `new_password`
  - Retorna: sucesso/erro

### **4. Configurar URLs** (`backend/accounts/urls.py`)

Registrar endpoints no router.

---

## 🔄 Ordem de Implementação Recomendada

1. ✅ **Testar ZohoClient** ← **VOCÊ ESTÁ AQUI**
2. ⏭️ **Implementar Services** (lógica de negócio)
3. ⏭️ **Implementar Serializers** (validação de dados)
4. ⏭️ **Implementar Views** (endpoints da API)
5. ⏭️ **Configurar URLs**
6. ⏭️ **Testar endpoints** (Postman/curl)

---

## 📝 Notas

- O `ZohoClient.reset_password()` ainda tem `TODO` - precisa implementar chamada real à API do Zoho
- SMS OTP será implementado depois (Fase 2)
- AD será implementado depois (Fase 3)

---

**Comece testando o ZohoClient!** 🚀

