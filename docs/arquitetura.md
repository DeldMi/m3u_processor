# Arquitetura do projeto

## Visão geral

Este projeto é uma plataforma para processar listas IPTV/M3U, validar canais, classificar metadados, gerar arquivos M3U/XMLTV e expor links públicos para consumo por clientes, players e integradores.

Ele combina:

- Flask no backend
- SQLite como banco local
- React + Vite + Tailwind + SCSS no frontend
- APScheduler para agendamento
- múltiplas fontes de entrada (.m3u, .m3u8, .txt, URLs remotas)
- geração de listas e EPG em blocos
- autenticação por sessão e controle de acesso RBAC

## Componentes principais

### 1. Backend Python

Localizados em `src/`.

Principais módulos:

- `src/app.py` — rotas HTTP, autenticação, APIs e servidores estáticos
- `src/manager.py` — lógica principal de processamento e geração de playlists
- `src/db.py` — acesso ao SQLite e schema inicial
- `src/config.py` — leitura/gravação do `.env`
- `src/auth.py` — autenticação, sessões e RBAC
- `src/parser.py` — leitura e parse de arquivos M3U
- `src/classifier.py` — organização por país/estado/cidade/categoria
- `src/checker.py` — verificação de disponibilidade de canais
- `src/epg.py` — geração de XMLTV/EPG por partição

### 2. Frontend React

Localizado em `frontend/react`.

A interface servida pela aplicação usa Vite para build e entrega estática para o Flask.

Estrutura:

- `src/main.tsx` — app React principal
- `src/styles.scss` — estilos globais, layout e temas
- `index.html` — ponto de entrada da SPA

### 3. Pastas de runtime

- `input/` — arquivos de origem M3U/M3U8/TXT colocados manualmente
- `output/` — playlists geradas e arquivos XMLTV
- `logs/` — relatórios JSON de auditoria
- `data/` — banco SQLite e dados persistentes
- `frontend/react/dist/` — build do React para produção

## Fluxo de funcionamento

### Entrada

A aplicação lê canais de:

1. arquivos em `input/`
2. arquivos já existentes em `output/`
3. URLs remotas definidas em `REMOTE_M3U_URLS`

### Validação

Cada canal é testado por HTTP/HTTPS para verificar disponibilidade, latência e status HTTP.

### Persistência

Os canais são salvos no banco SQLite e atualizados conforme status online/offline/desconhecido.

### Classificação

O `StreamClassifier` tenta atribuir dados como:

- país
- estado
- cidade
- categoria
- grupo/título do canal

### Particionamento

Os canais ativos são divididos em grupos com limite configurado por arquivo (`MAX_CHANNELS_PER_FILE`).

Exemplo:

- 700 canais ativos
- limite 400 por arquivo
- geração de 2 arquivos M3U + 2 XMLTV

### Geração final

Para cada partição:

- um `.m3u` é gerado
- um `.xml` EPG correspondente é gerado
- URLs públicas são montadas com `BASE_URL`

## Estrutura de dados principal

### Tabela `users`

Campos:

- id
- username
- password_hash
- role
- created_at

Roles válidas:

- `admin`
- `editor`
- `viewer`

### Tabela `channels`

Campos relevantes:

- url
- name
- metadata
- tvg_id
- logo
- group_title
- country
- state
- city
- category
- status
- latency_ms
- http_status
- auto_remove_if_offline

### Tabelas de processo

- `process_events`
- `process_runs`

Essas tabelas registram:

- inicio/fim de execução
- mensagens logadas
- total de canais
- canais online/offline
- arquivos gerados

## Permissões e acessos

O sistema usa RBAC:

- `admin`: acessa usuários, configurações, agendamento, endpoints administrativos
- `editor`: pode editar canais, gerar listas e iniciar/parar sincronização
- `viewer`: pode ver dashboards, listas e reprodução, mas não alterar

## URLs principais

### Aplicação web

- `/` — dashboard principal
- `/channels` — catálogo de canais e editor
- `/playlists` — listas publicadas
- `/settings` — configurações
- `/users` — usuários
- `/login` — login
- `/logout` — logout

### Endpoints públicos de arquivos

- `/playlist/<arquivo>.m3u`
- `/epg/<arquivo>.xml`

### API

- `/api/me`
- `/api/status`
- `/api/config`
- `/api/v1/channels`
- `/api/v1/users`
- `/api/v1/playlists`
- `/api/v1/playlists/generate`
- `/api/v1/sync`

## Segurança

- Sessões Flask em `secret_key`
- senhas em hash com `werkzeug.security`
- controle de acesso por função
- tokens Bearer suportados em endpoints de API por `API_TOKEN`

## Observações importantes

- O frontend React é servido a partir do build em `frontend/react/dist`.
- O Flask chama `send_file` para o `index.html` quando a build existe.
- Sem build do React, a aplicação pode abrir apenas as páginas antigas ou falhar na UI moderna.
- O projeto depende de um `.env` com configurações locais.

## Modelo operacional recomendado

Em produção real, o ideal é:

- usar um servidor Linux ou container Docker
- manter `BASE_URL` acessível publicamente
- proteger `.env` e o banco SQLite
- usar um reverse proxy com HTTPS
- limitar acesso administrativo com autenticação forte

---

Documentação complementar:

- [instalacao.md](instalacao.md)
- [configuracao.md](configuracao.md)
- [troubleshooting.md](troubleshooting.md)
- [acesso-e-recuperacao.md](acesso-e-recuperacao.md)

## Organização semântica e automação

A partir da atualização estrutural de setembro de 2026, o projeto passou a adotar uma organização incremental por domínio, preservando os endpoints existentes.

### Backend

```text
src/
├── core/
│   └── scheduler.py             # configuração do APScheduler
├── domains/
│   ├── health/
│   │   └── internet.py         # teste de conectividade e latência
│   ├── playlists/
│   │   └── service.py          # descoberta e publicação de manifests
│   └── sync/
│       └── service.py           # pipeline e saúde dos canais
├── app.py                       # composição Flask + compatibilidade das rotas
├── manager.py                   # processamento legado mantido compatível
└── ...
```

### Frontend

```text
frontend/react/src/
├── app/App.tsx                  # composição e roteamento da SPA
├── components/Common.tsx        # layout e componentes compartilhados
├── features/
│   ├── dashboard/DashboardPage.tsx
│   ├── channels/ChannelsPage.tsx
│   ├── playlists/PlaylistsPage.tsx
│   ├── settings/SettingsPage.tsx
│   ├── users/UsersPage.tsx
│   └── player/Player.tsx
├── services/api.ts              # cliente HTTP único
├── types/index.ts               # contratos TypeScript
├── styles.scss
└── main.tsx                     # entrypoint mínimo
```

### Verificação automatizada

O comando `npm run verify` executa, em ordem:

1. compilação/sintaxe Python;
2. testes Python;
3. build TypeScript/Vite;
4. conferência de arquivos estruturais obrigatórios.

As dependências do frontend não fazem parte do repositório: execute `npm run setup` antes da verificação em uma instalação nova.
