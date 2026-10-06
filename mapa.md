# Mapa do projeto

## Fluxo ativo

```text
npm run setup
    ↓
npm run verify
    ↓
npm run dev
    ↓
frontend React/Vite :5173
backend Flask/API :5000
public server :8080
```

Em produção:

```text
npm run setup
    ↓
npm run build
    ↓
npm run start
```

## Estrutura atual

```text
m3u_processor/
├── src/                         # Flask, autenticação, bancos e domínios
├── frontend/react/              # React, Vite, TypeScript e Tailwind
├── scripts/                     # setup, dev, start, build, verify, test
├── data/                        # SQLite
├── input/                       # listas M3U
├── output/                      # playlists e XMLTV
├── logs/                        # auditoria e histórico
├── docs/                        # documentação
├── Dockerfile
└── docker-compose.yml
```

## Componentes principais

- `src/app.py`: aplicação Flask e integração de rotas.
- `src/domains/`: autenticação, canais, EPG, health, manutenção, playlists, sincronização e usuários.
- `frontend/react/src/features/`: páginas ativas do painel.
- `scripts/`: orquestração cross-platform do setup, dev, prod, build e verify.
- `data/app.db`: estado persistido.

## Compatibilidade

`setup_env.*`, `run_menu.*` e `run_checker.*` permanecem disponíveis como wrappers antigos. O contrato oficial é o fluxo via `package.json`.

## Limitações conhecidas

- A página EPG oferece cadastro/sincronização de fontes, edição dos metadados dos canais e CRUD de programação por canal com recorrência; ainda não há visualização em grade/calendário nem testes de navegador.
- O fluxo de canais V2 está ativo; os endpoints legados e os domínios ainda coexistem durante a migração.
- O setup possui um bloqueio de ambiente Windows ao remover o binário do esbuild, embora o fluxo tenha sido validado até a instalação do frontend.
