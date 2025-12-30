# 🧪 Como Testar Zoho API no Postman

## 📋 Pré-requisitos

1. **Access Token válido** (obtido via OAuth)
2. **Scope correto**: `ZohoMail.organization.READ` (mínimo para buscar organization)

---

## 🔍 1. Organization ID (zoid)

**Nota**: Para contas comuns, o endpoint `GET /api/organization` não está disponível.

**Recomendação**: Configure `ZOHO_ORGANIZATION_ID` no `.env`:

```env
ZOHO_ORGANIZATION_ID=873090368
```

O `ZohoClient` usará este valor automaticamente, evitando buscar via API.

---

## 👤 2. Buscar User ID (zuid) por Email

### **Request**

**Método**: `GET`

**URL**: 
```
https://mail.zoho.com/api/organization/{zoid}/accounts
```

**Headers**:
```
Authorization: Zoho-oauthtoken {SEU_ACCESS_TOKEN}
Content-Type: application/json
```

### **Exemplo no Postman**:

1. **Method**: `GET`
2. **URL**: `https://mail.zoho.com/api/organization/873090368/accounts?emailId=usuario@exemplo.com`
   (Substitua `873090368` pelo seu zoid configurado no `.env`)
3. **Headers**:
   - Key: `Authorization`
   - Value: `Zoho-oauthtoken {SEU_ACCESS_TOKEN}`
   
   - Key: `Content-Type`
   - Value: `application/json`

### **Resposta Esperada**:

```json
{
  "data": [
    {
      "zuid": 9876543210,
      "emailAddress": "usuario@exemplo.com",
      "firstName": "Nome",
      "lastName": "Sobrenome",
      ...
    },
    ...
  ]
}
```

**O `zuid` está em**: `data[].zuid` ou `data[].id` (busque pelo email)

---

## 🔐 3. Reset de Senha

### **Request**

**Método**: `PUT`

**URL**: 
```
https://mail.zoho.com/api/organization/{zoid}/accounts/{zuid}
```

**Headers**:
```
Authorization: Zoho-oauthtoken {SEU_ACCESS_TOKEN}
Content-Type: application/json
```

**Body** (JSON):
```json
{
  "password": "NovaSenha123!",
  "mode": "resetPassword"
}
```

### **Exemplo no Postman**:

1. **Method**: `PUT`
2. **URL**: `https://mail.zoho.com/api/organization/1234567890/accounts/9876543210`
   (Substitua `zoid` e `zuid` pelos valores obtidos)
3. **Headers**:
   - Key: `Authorization`
   - Value: `Zoho-oauthtoken {SEU_ACCESS_TOKEN}`
   
   - Key: `Content-Type`
   - Value: `application/json`
4. **Body** (raw JSON):
   ```json
   {
     "password": "NovaSenha123!",
     "mode": "resetPassword"
   }
   ```

### **Resposta Esperada**:

**Sucesso (200)**:
```json
{
  "status": "success",
  "message": "Password reset successfully"
}
```

**Erros Comuns**:
- **400**: Parâmetros inválidos
- **401**: Token inválido/expirado
- **403**: Sem permissão (scope incorreto)
- **404**: Usuário não encontrado

---

## 🔑 Como Obter Access Token

### **Opção 1: Via Refresh Token (Recomendado)**

**Método**: `POST`

**URL**: 
```
https://accounts.zoho.com/oauth/v2/token
```

**Body** (form-data ou x-www-form-urlencoded):
```
grant_type=refresh_token
&client_id=SEU_CLIENT_ID
&client_secret=SEU_CLIENT_SECRET
&refresh_token=SEU_REFRESH_TOKEN
```

### **Resposta**:
```json
{
  "access_token": "1000.xxx...",
  "expires_in": 3600,
  "scope": "ZohoMail.organization.READ ZohoMail.organization.accounts.ALL",
  "api_domain": "https://www.zohoapis.com",
  "token_type": "Bearer"
}
```

---

## 📝 Checklist de Teste

- [ ] Obter access token via refresh_token
- [ ] Buscar organization ID (zoid)
- [ ] Buscar user ID (zuid) por email
- [ ] Testar reset de senha (se scope permitir)

---

## ⚠️ Troubleshooting

### **Erro 401 (Unauthorized)**
- Token expirado → Renove usando refresh_token
- Token inválido → Verifique se copiou corretamente

### **Erro 403 (Forbidden)**
- Scope insuficiente → Verifique se tem `ZohoMail.organization.accounts.ALL` ou `UPDATE`
- Gere novo refresh_token com scope correto

### **Erro 404 (Not Found)**
- zoid incorreto → Busque novamente o organization ID
- zuid incorreto → Verifique se o email existe na organização

---

## 🔗 Referências

- [Zoho Mail API - Reset Password](https://www.zoho.com/mail/help/api/put-reset-user-password.html)
- [Zoho Mail API - Get Organization](https://www.zoho.com/mail/help/api/get-organization-details.html)
- [Zoho Mail API - Get All Users](https://www.zoho.com/mail/help/api/get-all-org-user-details.html)

