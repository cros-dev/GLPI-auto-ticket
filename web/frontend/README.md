# 🔐 GRAM-SSPR Frontend

Frontend Angular para o serviço **GRAM-SSPR (Self-Service Password Reset)**.

## 📋 Sobre o Projeto

O **GRAM-SSPR Frontend** é uma aplicação Angular standalone dedicada exclusivamente ao fluxo de reset de senha, oferecendo uma interface simples e intuitiva para:

- **Solicitação de reset**: Usuário informa email e recebe código OTP via SMS
- **Validação de OTP**: Usuário informa código recebido para validação
- **Confirmação de senha**: Usuário define nova senha após validação

## 🏗️ Arquitetura

O projeto segue o mesmo padrão arquitetural do GLPI Auto-Ticket:

- **Services**: Comunicação com API e lógica de negócio
- **Components**: Componentes de UI (password-reset, success)
- **Utils**: Utilitários reutilizáveis (error-handler)
- **Interceptors**: Interceptação de requisições HTTP
- **Models**: Interfaces TypeScript para tipagem

## 🚀 Tecnologias

- **Angular 21** - Framework frontend
- **PrimeNG 21** - Componentes UI
- **PrimeIcons** - Ícones
- **RxJS** - Programação reativa
- **TypeScript** - Tipagem estática

## 📁 Estrutura do Projeto

```
GRAM-sspr/
├── src/
│   ├── app/
│   │   ├── components/
│   │   │   ├── password-reset/    # Componente principal de reset
│   │   │   └── success/            # Componente de sucesso
│   │   ├── services/
│   │   │   ├── password-reset.service.ts  # Serviço de reset
│   │   │   ├── notification.service.ts    # Notificações toast
│   │   │   └── theme.service.ts            # Gerenciamento de tema
│   │   ├── models/
│   │   │   └── password-reset.interface.ts  # Interfaces TypeScript
│   │   ├── utils/
│   │   │   └── error-handler.utils.ts      # Tratamento de erros
│   │   ├── interceptors/
│   │   │   └── auth.interceptor.ts         # Interceptor HTTP
│   │   ├── app.config.ts                   # Configuração do app
│   │   ├── app.routes.ts                   # Rotas da aplicação
│   │   ├── app.ts                          # Componente raiz
│   │   └── app.html                        # Template raiz
│   ├── environments/
│   │   ├── environment.ts                  # Ambiente dev
│   │   └── environment.prod.ts             # Ambiente prod
│   ├── styles/
│   │   ├── variables.css                   # Variáveis CSS
│   │   ├── reset.css                       # Reset CSS
│   │   ├── utilities.css                   # Classes utilitárias
│   │   ├── typography.css                  # Tipografia
│   │   ├── components.css                  # Componentes globais
│   │   ├── forms.css                       # Estilos de formulários
│   │   └── primeng-overrides.css           # Overrides PrimeNG
│   ├── index.html                          # HTML principal
│   ├── main.ts                             # Bootstrap
│   └── styles.css                          # Estilos globais
├── public/                                 # Assets estáticos
├── angular.json                            # Configuração Angular
├── package.json                            # Dependências
└── tsconfig.json                           # Configuração TypeScript
```

## 🔄 Fluxo de Reset de Senha

1. **Solicitação**: Usuário informa email → Sistema valida e envia OTP via SMS
2. **Validação**: Usuário informa código OTP → Sistema valida código
3. **Confirmação**: Usuário define nova senha → Sistema reseta senha

## 🚀 Como Executar

### Pré-requisitos

- Node.js 18+ e npm
- Backend GRAM-SSPR rodando (porta 8000 por padrão)

### Instalação

```bash
# Instalar dependências
npm install
```

### Desenvolvimento

```bash
# Iniciar servidor de desenvolvimento
npm start

# Acessar em: http://localhost:4200
```

### Build

```bash
# Build de produção
npm run build
```

## ⚙️ Configuração

### Variáveis de Ambiente

Edite `src/environments/environment.ts` para desenvolvimento:

```typescript
export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000/api'
};
```

Edite `src/environments/environment.prod.ts` para produção:

```typescript
export const environment = {
  production: true,
  apiUrl: 'https://api.gram-sspr.com/api'  // URL de produção
};
```

## 📡 Endpoints Utilizados

O frontend consome os seguintes endpoints do backend:

- `POST /api/accounts/password-reset/request/` - Solicitar reset
- `POST /api/accounts/password-reset/validate-otp/` - Validar OTP
- `POST /api/accounts/password-reset/confirm/` - Confirmar reset

## 🎨 Estilos e Tema

O projeto utiliza:

- **PrimeNG Aura Theme** - Tema base
- **CSS Variables** - Design tokens centralizados
- **Dark Mode** - Suporte a tema escuro (via `.app-dark`)
- **Responsive Design** - Layout adaptável

## 📦 O Que Foi Reaproveitado

### ✅ Arquivos Copiados e Adaptados

- **Services**: `notification.service.ts`, `theme.service.ts`, `password-reset.service.ts`
- **Utils**: `error-handler.utils.ts`
- **Models**: `password-reset.interface.ts`
- **Components**: `password-reset` (adaptado)
- **Interceptors**: `auth.interceptor.ts` (simplificado para SSPR público)
- **Estilos**: Todos os arquivos de `styles/` (variáveis, reset, utilities, etc.)
- **Configurações**: `angular.json`, `tsconfig.json`, `package.json`

### ❌ Arquivos Não Copiados (Específicos do GLPI)

- **Components**: `category-suggestions`, `category-preview`, `glpi-sync`, `knowledge-base`, `breadcrumb`, `login`, `main-layout`
- **Services**: `api.service.ts` (específico de tickets/categorias), `auth.service.ts` (não necessário para SSPR público), `cache.service.ts`
- **Models**: `category-suggestion.interface.ts`, `knowledge-base-article.interface.ts`
- **Utils**: `date.utils.ts`, `html.utils.ts`, `status.utils.ts` (específicos de tickets)
- **Guards**: `auth.guard.ts` (não necessário para SSPR público)

## 🔐 Segurança

- **Validação de formulários**: Validação client-side antes de enviar
- **Validação de senha**: Mínimo 8 caracteres, maiúscula, minúscula e número
- **Tratamento de erros**: Mensagens claras e seguras
- **HTTPS em produção**: Recomendado para produção

## 🚫 Independência

Este frontend é **totalmente independente** do GLPI Auto-Ticket:

- ✅ Projeto Angular separado
- ✅ Sem dependências do projeto original
- ✅ Pode rodar isoladamente
- ✅ Pronto para evolução independente

## 📚 Documentação Adicional

Para mais detalhes sobre o backend, consulte:
- `GRAM-sspr/backend/README.md`

## 🛠️ Desenvolvimento

### Estrutura de Componentes

- **PasswordResetComponent**: Componente principal com fluxo em 3 etapas
- **SuccessComponent**: Componente de confirmação de sucesso

### Services

- **PasswordResetService**: Comunicação com API de reset
- **NotificationService**: Notificações toast (PrimeNG)
- **ThemeService**: Gerenciamento de tema claro/escuro

### Utils

- **error-handler.utils.ts**: Análise e tratamento centralizado de erros HTTP

## 📝 Notas

- O frontend assume que o backend está configurado com JWT (embora não seja usado para SSPR público)
- Todas as requisições são públicas (não requerem autenticação)
- O interceptor HTTP mantém tratamento de erros, mas não adiciona tokens

---

**Status**: ✅ **Frontend criado e pronto para uso**

