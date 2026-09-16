# AGENTS.md

Este arquivo guarda o contexto operacional do projeto para que IA, copilotos e outros chats possam entender rapidamente o que existe, como rodar, o que foi alterado e o que o usuário prioriza.

## Projeto

M3U Processor / M3U Architect

Autor e titular declarado: DeldMi
Licenca: LICENSE (uso gratuito com atribuicao obrigatoria)
Aviso de autoria: NOTICE

Sistema para:
- processar listas IPTV/M3U
- validar canais online/offline
- classificar canais por país, estado, cidade e categoria
- gerar arquivos M3U e XMLTV/EPG em blocos
- publicar links públicos para clientes/players
- gerenciar usuários, permissões e configurações

## Stack principal

- Backend: Python + Flask
- Frontend: React + Vite + TypeScript + Tailwind + SCSS
- Banco: SQLite
- Agendamento: APScheduler
- Execução: Docker + Docker Compose
- Ambiente local: scripts .bat/.sh + package.json raiz

## Estrutura do projeto

- src/ — backend e lógica de processamento
  - app.py — rotas, APIs, autenticação e servidores de arquivos
  - manager.py — geração de playlists, auditoria, validação e EPG
  - db.py — schema do banco SQLite
  - config.py — leitura e gravação do .env
  - auth.py — sessão e RBAC
  - parser.py, classifier.py, checker.py, epg.py
- frontend/react — SPA em React
  - src/main.tsx — app principal e views
  - src/styles.scss — estilo e layout
- input/ — fontes locais em .m3u/.m3u8/.txt
- output/ — listas geradas e XMLTV
- logs/ — relatórios JSON de auditoria
- data/ — banco SQLite e dados persistentes
- docs/ — documentação detalhada
- LICENSE — licença de uso, atribuição e proteção de autoria
- NOTICE — créditos e titularidade declarada
- scripts/ — scripts de setup e execução
- package.json — comando principal para ambiente raiz
- .env / .env.example — configurações
- Dockerfile / docker-compose.yml — execução em container

## Funcionalidades críticas

### Autenticação e permissões

Usuários padrão ao criar BD:
- admin / admin123

Roles:
- admin — configurações, usuários e administração
- editor — edita canais, dispara sincronização e gera listas
- viewer — leitura e consumo de listas

### Processamento

Fluxo principal:
1. lê arquivos em input/
2. lê URLs remotas em REMOTE_M3U_URLS
3. deduplica canais
4. valida conexão e status de cada canal
5. persiste no banco
6. classifica metadados
7. gera M3U e EPG em blocos
8. publica links em BASE_URL

### Interface

Páginas principais:
- / — dashboard
- /channels — canais e editor
- /playlists — listas publicadas
- /settings — configurações
- /users — gerenciamento de usuários
- /login — login

### Listas e nomes

Importante: o usuário pediu que a geração de listas permita nome personalizado e edição do nome/URL da lista, sem conflitar com a base URL global.

A lógica do projeto já foi ajustada para:
- aceitar nome de lista na geração
- gerar arquivos com prefixo customizado
- renomear playlist e XML pairados
- manter `BASE_URL` como endereço público base

### Estilos visuais

O frontend já teve correção para:
- layout do dashboard e cards
- alinhamento geral da UI
- estilos de inputs/select/textarea
- retorno visual consistente entre todas as telas

## Configuração do ambiente

Arquivo `.env` principal. Exemplo em `.env.example`.

Variáveis importantes:
- BASE_URL
- PUBLIC_BASE_URL
- WEB_HOST
- WEB_PORT
- PUBLIC_HOST
- PUBLIC_PORT
- MAX_CHANNELS_PER_FILE
- CONCURRENCY_LIMIT
- REQUEST_TIMEOUT
- USER_AGENT
- REMOTE_M3U_URLS
- SCHEDULE_MODE
- SCHEDULE_INTERVAL_HOURS
- SCHEDULE_CRON_TIME
- API_TOKEN
- SECRET_KEY

## Comandos oficiais

Na raiz do projeto:

- npm run setup
  - cria .venv
  - instala dependências Python
  - instala dependências do frontend
  - compila o build React

- npm run dev
  - inicia backend Flask e frontend Vite em modo desenvolvimento

- npm run start
  - inicia a aplicação em produção local

- npm run build
  - gera build do frontend React

- npm run open
  - abre a URL pública no navegador

- npm run docker:up
  - sobe o Docker Compose

- npm run docker:down
  - derruba o container

- npm run docker:logs
  - mostra logs do Docker

Comandos em shell legado:
- ./setup_env.sh
- ./run_menu.sh
- ./run_checker.sh
- setup_env.bat
- run_menu.bat
- run_checker.bat

## Execução local

Linux/macOS:
- chmod +x *.sh
- ./setup_env.sh
- ./run_menu.sh

Windows:
- setup_env.bat
- run_menu.bat

Docker:
- docker compose up -d --build
- acessar menu: http://localhost:5000
- acessar links: http://localhost:8080

## Observações importantes sobre ambiente

- O projeto precisa do Node instalado para o frontend e do Python para o backend.
- O build do React precisa existir em frontend/react/dist para que o Flask sirva a SPA corretamente.
- O arquivo .env deve existir antes da aplicação rodar.
- Em produção, `BASE_URL` deve apontar para a URL pública real do projeto, não para localhost.

## Correções já aplicadas e guardadas como contexto

O usuário já pediu e validou as seguintes melhorias:
- frontend em React + Vite + TypeScript + Tailwind + SCSS
- scripts e setup raiz para iniciar sem depender de passos manuais
- docker e .gitignore e .env ajustados
- documentação detalhada em docs/
- correção de inputs sem estilo
- restauração de páginas e fluxos de canais/usuarios/configurações
- ajuste de listagem e criação de playlist com nome personalizado
- correção de PATH/npm no modo dev (`ENOENT` resolvido com uso de npm_execpath / npm.cmd)

## Troubleshooting

### Erro `spawn npm ENOENT`

Causa: processo filho sem PATH correto em Git Bash / VS Code. Solução: usar `process.env.npm_execpath` ou `npm.cmd`/`npm` explicitamente.

### Frontend não renderiza

Verificar:
- `npm --prefix frontend/react run build`
- existencia de `frontend/react/dist/index.html`

### Login ou senha não funcionam

Credenciais padrão:
- admin / admin123

Se necessário, resetar via SQLite.

### .env ausente

Usar:
- cp .env.example .env
ou:
- copy .env.example .env

## Documentação do projeto

- README.md — guia inicial
- docs/arquitetura.md — arquitetura
- docs/instalacao.md — instalação
- docs/configuracao.md — configuração
- docs/troubleshooting.md — problemas comuns
- docs/acesso-e-recuperacao.md — senhas e recuperação de acesso
- docs/direitos-e-doacoes.md — autoria, licença, créditos e doações

## Regras para agentes e chats

- Não recomeçar do zero o contexto do projeto.
- Preservar os padrões já validados: Flask + React + SQLite + root scripts + documentação.
- Sempre que uma alteração relevante for feita em setup, Docker, .env, .gitignore, .sh, .bat, .md ou txt, atualizar os arquivos correspondentes e manter consistência.
- Quando o usuário pedir ajustes no frontend, manter a lógica do backend e os endpoints compatíveis.
- Quando o usuário pedir nomear, editar ou gerar listas, priorizar a lógica de nome e link público sem quebrar `BASE_URL`.
- O menu roda em `WEB_PORT`/`BASE_URL`; playlists e EPG rodam em servidor separado usando `PUBLIC_PORT`/`PUBLIC_BASE_URL`.
- O servidor público deve aceitar somente `/playlist/...` e `/epg/...`, sem expor menu ou APIs.
- Alterações de `WEB_PORT` ou `PUBLIC_PORT` exigem reiniciar os processos ou os serviços Docker.
- Alterações no projeto devem preservar os créditos de DeldMi, o arquivo LICENSE e o arquivo NOTICE.
- Componentes de terceiros devem manter suas próprias licenças e créditos.

## Resumo do que o usuário prioriza

- app funcionando localmente em Windows e Linux
- root package.json para iniciar tudo em um comando
- ambiente consistente em Docker e local
- documentação completa que possa ser consultada sem repetir contexto
- UI visualmente coerente e funcional
- geração de playlists com nome e edição
- sem perda de funcionalidade entre Flask e React

## Dica final

Se qualquer IA ou outro chat precisar entender o projeto rapidamente, deve começar por:
1. ler este arquivo AGENTS.md
2. ler README.md
3. revisar o stack e scripts de raiz
4. verificar docs/ e os endpoints relevantes
5. seguir as convenções de uso do usuário: root command-first, UI consistente, listas com nome e link público
