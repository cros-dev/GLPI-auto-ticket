# 📋 Estratégia de Testes - Feature SSPR

## 📁 Estrutura dos Testes

Os testes estão organizados por funcionalidade, seguindo o padrão AAA (Arrange-Act-Assert):

```
backend/accounts/tests/
├── test_request_password_reset.py    # Solicitação de reset de senha
├── test_generate_otp.py               # Geração de códigos OTP
├── test_validate_otp.py               # Validação de códigos OTP
├── test_confirm_password_reset.py     # Confirmação de reset de senha
└── test_models.py                     # Métodos auxiliares dos models
```

## ✅ Funcionalidades Testadas

### 1. **request_password_reset** (`test_request_password_reset.py`)

**Cenários testados:**
- ✅ Solicitação bem-sucedida (happy path)
- ✅ Sistema inválido
- ✅ Usuário não encontrado no Zoho
- ✅ Exceção do Zoho (erro na API)
- ✅ Limite de solicitações por hora excedido
- ✅ Configuração correta de `expires_at`

**Estratégia:**
- Mock do `ZohoClient` para isolar dependência externa
- Testa limites de negócio (rate limiting)
- Valida criação correta do model no banco

---

### 2. **generate_otp** (`test_generate_otp.py`)

**Cenários testados:**
- ✅ Geração bem-sucedida de OTP
- ✅ Código OTP de 6 dígitos numéricos
- ✅ Configuração correta de `expires_at`
- ✅ Solicitação expirada (não permite gerar OTP)
- ✅ Status inválido da solicitação
- ✅ Permite regenerar OTP quando status é 'otp_validated'

**Estratégia:**
- Testa geração de código único
- Valida regras de negócio (status permitidos)
- Verifica expiração configurada corretamente

---

### 3. **validate_otp** (`test_validate_otp.py`)

**Cenários testados:**
- ✅ Validação bem-sucedida de OTP
- ✅ Código OTP inválido
- ✅ Incremento de tentativas em caso de erro
- ✅ Limite de tentativas excedido (3 tentativas)
- ✅ OTP expirado
- ✅ Solicitação expirada
- ✅ Sem OTP pendente
- ✅ Código com espaços (stripped)
- ✅ Usa OTP mais recente quando há múltiplos

**Estratégia:**
- Testa lógica de validação completa
- Verifica atualização de status após validação
- Valida incremento de tentativas
- Testa comportamento com múltiplos OTPs

---

### 4. **confirm_password_reset** (`test_confirm_password_reset.py`)

**Cenários testados:**
- ✅ Confirmação bem-sucedida de reset
- ✅ Status atualizado para 'completed'
- ✅ OTP não validado (erro)
- ✅ Solicitação expirada
- ✅ Falha no Zoho (retorna False)
- ✅ Exceção do Zoho
- ✅ Sistema 'both' (chama Zoho)

**Estratégia:**
- Mock do `ZohoClient` para isolar chamadas à API
- Testa atualização de status após sucesso/falha
- Valida erros de negócio (status inválido, expirado)

---

### 5. **Models** (`test_models.py`)

**Testados:**
- `ZohoToken.is_access_token_valid()` - Token válido/expirado/ausente
- `ZohoToken.needs_refresh()` - Quando precisa renovar
- `PasswordResetRequest.is_expired()` - Verificação de expiração
- `PasswordResetRequest.generate_token()` - Geração automática no save
- `PasswordResetRequest.expires_at` - Configuração automática no save
- `OtpToken.is_expired()` - Verificação de expiração
- `OtpToken.has_exceeded_attempts()` - Verificação de tentativas
- `OtpToken.generate_code()` - Geração automática no save
- `OtpToken.increment_attempts()` - Incremento e atualização de status

**Estratégia:**
- Testa métodos auxiliares dos models
- Valida lógica de expiração
- Verifica geração automática de tokens/códigos no save

---

## 🔧 Padrões e Práticas

### Isolamento de Dependências

- **APIs externas**: Mock do `ZohoClient` usando `unittest.mock.patch`
- **Banco de dados**: Django TestCase cria banco de teste isolado
- **Tempo**: Uso de `timezone.now()` com tolerância de ~5 segundos para comparações

### Estrutura dos Testes

Cada teste segue o padrão AAA:

```python
def test_exemplo(self):
    # Arrange - Configurar dados e mocks
    mock_client = MagicMock()
    mock_client.method.return_value = value
    
    # Act - Executar ação sendo testada
    result = function_under_test(params)
    
    # Assert - Validar resultado
    self.assertTrue(result)
    mock_client.method.assert_called_once()
```

### Casos de Teste

Cada funcionalidade cobre:
- ✅ **Happy path** (caminho feliz)
- ✅ **Validações** (dados inválidos)
- ✅ **Erros esperados** (exceções, falhas)
- ✅ **Limites de negócio** (rate limiting, tentativas)
- ✅ **Estados inválidos** (expirado, status incorreto)

---

## 🚫 O que NÃO foi testado (e por quê)

### 1. **ZohoClient diretamente**
- **Motivo**: O `ZohoClient` faz chamadas HTTP reais e tem lógica complexa de token OAuth
- **Alternativa**: Mockado nos testes de services, que testam o comportamento esperado
- **Recomendação**: Testes de integração separados (usando scripts manuais existentes)

### 2. **Views/Endpoints REST**
- **Motivo**: Requer setup completo do Django (URLs, serializers, permissões)
- **Alternativa**: Testes de integração via Postman ou testes E2E
- **Recomendação**: Criar `test_views.py` separado com `APITestCase` se necessário

### 3. **send_otp_sms**
- **Motivo**: Ainda é um placeholder (TODO)
- **Quando implementar**: Criar testes após integração real com provedor SMS

### 4. **Integração com AD**
- **Motivo**: Funcionalidade futura (não implementada)
- **Quando implementar**: Criar testes após implementação do cliente AD

### 5. **Parsers (zoho_error_parser.py)**
- **Motivo**: Funções utilitárias simples que são testadas indiretamente
- **Alternativa**: Testados via testes de services que usam o parser
- **Recomendação**: Pode adicionar testes unitários se necessário

---

## 🚀 Como Executar os Testes

```bash
# Todos os testes do app accounts
python manage.py test accounts.tests

# Teste específico
python manage.py test accounts.tests.test_request_password_reset

# Com verbosidade
python manage.py test accounts.tests --verbosity=2

# Apenas uma classe de teste
python manage.py test accounts.tests.test_request_password_reset.RequestPasswordResetTest

# Apenas um método
python manage.py test accounts.tests.test_request_password_reset.RequestPasswordResetTest.test_request_password_reset_success
```

---

## 📊 Cobertura de Testes

### Services (lógica de negócio)
- ✅ `request_password_reset` - Coberto
- ✅ `generate_otp` - Coberto
- ⚠️ `send_otp_sms` - Placeholder (não testado)
- ✅ `validate_otp` - Coberto
- ✅ `confirm_password_reset` - Coberto

### Models (métodos auxiliares)
- ✅ `ZohoToken` - Coberto
- ✅ `PasswordResetRequest` - Coberto
- ✅ `OtpToken` - Coberto
- ⚠️ `SystemAccount` - Não testado (model simples, sem lógica complexa)

### Clients
- ⚠️ `ZohoClient` - Não testado diretamente (mockado nos services)

### Views
- ⚠️ Views REST - Não testadas (recomendação: testes E2E)

### Parsers
- ⚠️ `zoho_error_parser` - Testado indiretamente via services

---

## 🔍 Pontos de Atenção

1. **Mocks**: Os testes mockam `ZohoClient` completamente. Certifique-se de que os mocks refletem o comportamento real ao modificar o client.

2. **Tempo**: Comparações de tempo usam tolerância de ~5 segundos devido ao tempo de execução. Ajustar se necessário.

3. **Banco de teste**: Django cria banco isolado para cada teste. Não há conflito entre testes.

4. **Dados de teste**: Cada teste é independente e usa `setUp()` para criar dados necessários.

---

## 📝 Notas

- Testes seguem padrão Django (herdam de `TestCase`)
- Uso de `unittest.mock` para isolar dependências
- Todos os testes são determinísticos (sem chamadas externas reais)
- Foco em testar comportamento, não implementação

