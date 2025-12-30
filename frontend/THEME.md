# Padronização e Centralização de Tema (PrimeNG Aura)

Este projeto usa **PrimeNG v21** com **@primeuix/themes (Aura)**. O objetivo é que **todo o visual** seja controlado por:
- **Tokens do PrimeNG** (`--p-*`) como fonte de verdade
- **Tokens do app** (`--app-*`) como camada de “ponte” para containers/layouts customizados

## Requisitos (decisões do projeto)

- **Tema**: PrimeNG **Aura**
- **Modos**: **Light e Dark**, com alternância
- **Cards e caixas (ex.: erro)**: devem ser **mais claros**, usando \(surface\) equivalente a **`surface-0`** em ambos os modos
- **Topbar e Sidenav**: devem **seguir o modo** (no light, claros; no dark, escuros)
- **Proibições**:
  - Não usar **cores hardcoded** (hex/rgb/hsl) em `src/app/**`
  - Não usar `!important`
  - Evitar `::ng-deep` fora de `layouts/` (quando necessário, sempre ancorado em `styleClass`)

## Onde o tema é configurado

- **PrimeNG**: `src/app/app.config.ts`
  - `providePrimeNG({ theme: { preset: Aura, options: { darkModeSelector: '.app-dark' }}})`
- **Aplicação do modo (classe CSS)**: aplicada no `<html>` pelo `ThemeService`
  - Classe: `.app-dark`

## Tokens do app (camada central)

Os tokens do app ficam em `src/styles.css`:

- **Base**
  - `--app-text`: texto padrão
  - `--app-text-muted`: texto secundário
  - `--app-border`: borda padrão
  - `--app-bg`: fundo da página (content-area)
  - `--app-bg-disabled`: fundo de inputs desabilitados
- **Superfícies**
  - `--app-surface-card`: **sempre** `--p-surface-0` (light e dark)
- **Layout**
  - `--app-sidebar-*`
  - `--app-topbar-*`

Regra: **componentes** devem preferir `--app-*` (ou variáveis antigas de layout que mapeiam para `--app-*`).  
Somente o `styles.css` deve “conhecer” `--p-*` diretamente.

## Checklist para PR (tema)

- [ ] Nenhum `!important`
- [ ] Nenhum hex/rgb/hsl em `src/app/**`
- [ ] Botões usam `p-button`
- [ ] Estados (erro/sucesso/aviso) usam componente PrimeNG ou tokens do app
- [ ] Não “pintar” componentes PrimeNG com cores locais; usar tokens


