# AGENTS.md

Contexto operacional do **M3U Processor / M3U Architect** para IAs, copilotos e colaboradores.

## Projeto

- Autor/titular declarado: **DeldMi**
- Licença: `LICENSE`
- Créditos: `NOTICE`
- Backend: Python + Flask
- Frontend: React + Vite + TypeScript + Tailwind + SCSS
- Banco: SQLite
- Agendamento: APScheduler
- Execução: Windows/Linux/macOS e Docker

Sistema para processar listas M3U/M3U8, validar canais, classificar metadados, gerar M3U/XMLTV em blocos, publicar arquivos e gerenciar usuários, permissões, configurações, manutenção e monitoramento.

## Funcionalidades obrigatórias

### Painel Geral

- Indicador visual Internet **ONLINE/OFFLINE**.
- Latência em ms.
- Destino utilizado no teste.
- Saúde automática dos canais sem regenerar playlists.
- Resumo operacional sem expor informações que o usuário autenticado não tenha permissão para consultar.
- Cards e métricas devem respeitar o RBAC do usuário atual.

### Canais e Editor

- Campo **CH. NO.** para editar o número do canal.
- Persistência no SQLite.
- Suporte a `tvg-chno` quando aplicável.
- Filtros por país, estado, cidade, categoria e status.
- Ordenação por cabeçalho.
- Seleção persistente de colunas.
- Upload local de logos.
- Ações de visualizar, editar, criar, excluir e alterar status devem ser controladas individualmente por permissão.
- Usuários sem permissão de edição não podem receber controles de edição apenas ocultos visualmente; a API também deve rejeitar a operação.

### Playlists/EPG

- Nome personalizado na geração.
- Prefixo/arquivo customizado.
- Renomeação pareada de playlist e XMLTV.
- `BASE_URL` permanece a base pública global.
- Servidor público deve expor somente `/playlist/...` e `/epg/...`.
- Operações de criar, regenerar, excluir, baixar/visualizar e administrar playlists devem respeitar permissões específicas.

### Configurações

- Destino do teste de Internet/ping.
- Intervalo/delay.
- Timeout.
- Resultado em tempo real.
- Configuração de limpeza e manutenção do sistema.
- Ajuda contextual e tutorial acessível para cada grupo de configuração.

## Gestão de usuários e RBAC granular

A tela **Usuários** deve deixar de tratar permissões apenas como um papel genérico. O sistema deve apresentar claramente **o que cada usuário pode visualizar, criar, editar e excluir**.

### Cadastro e edição de usuário

O formulário de criação/edição deve suportar, conforme o modelo de dados:

**Campos obrigatórios:**

- nome de usuário/login único;
- nome de exibição;
- senha no cadastro;
- papel/perfil base;
- status ativo/inativo.

**Campos opcionais:**

- nome completo;
- e-mail;
- foto/avatar;
- telefone;
- descrição/observação;
- departamento/grupo;
- data de expiração, quando habilitada;
- preferências de interface;
- outras informações não sensíveis úteis à administração.

Na edição, a senha deve ser opcional: campo vazio significa manter a senha atual. Senhas nunca devem ser exibidas em texto puro.

O formulário deve indicar visualmente quais campos são obrigatórios e quais são opcionais, validar dados no frontend e no backend e explicar cada campo por meio de ajuda contextual.

### Permissões por ação

O modelo de autorização deve permitir, no mínimo, separar:

- **Visualizar** — consultar dados e telas.
- **Criar** — adicionar registros.
- **Editar** — alterar registros existentes.
- **Excluir** — remover registros.
- **Executar** — iniciar processos potencialmente operacionais, como sincronização, geração, testes e manutenção.
- **Administrar** — alterar configurações sensíveis, usuários, permissões e integrações.

Os recursos devem ser organizados por domínio, por exemplo:

- Dashboard;
- Canais;
- Playlists;
- EPG;
- Sincronização;
- Monitoramento/saúde;
- Configurações;
- Usuários;
- Logs;
- Manutenção/limpeza;
- Arquivos públicos;
- Sistema.

A UI de criação/edição de usuário deve apresentar uma matriz ou estrutura equivalente **Recurso × Ação**, com descrição humana de cada permissão. O administrador deve conseguir entender exatamente o alcance de uma permissão antes de salvá-la.

### Regra crítica de segurança

O problema observado em 2026-09-16 deve ser tratado como requisito funcional e de segurança: um usuário com permissão somente de visualização não deve visualizar informações, menus, métricas ou ações fora do seu escopo.

A proteção deve existir em **duas camadas**:

1. **Frontend:** ocultar menus, botões, campos e informações que não sejam permitidos.
2. **Backend:** aplicar autorização em todas as rotas e operações, independentemente do frontend.

Não considerar seguro apenas esconder um botão. Uma requisição direta à API por usuário sem permissão deve receber resposta de autorização adequada, sem executar a operação.

O endpoint `/api/me` deve informar somente os dados e permissões necessários à interface e nunca deve vazar credenciais, hashes, tokens ou informações administrativas indevidas.

## Limpeza e manutenção do sistema

A tela **Configurações → Manutenção/Limpeza** deve oferecer ações separadas, claramente descritas e protegidas por permissão administrativa.

Categorias previstas:

- limpar cache da aplicação;
- limpar arquivos temporários;
- limpar listas/arquivos de entrada temporários;
- limpar arquivos de saída antigos;
- limpar playlists geradas, com confirmação explícita;
- limpar arquivos XMLTV/EPG gerados, com confirmação explícita;
- limpar dados temporários de processamento;
- limpar logs antigos por período;
- compactar/rotacionar logs quando aplicável;
- limpar cache do frontend/build somente quando seguro para o ambiente;
- verificar espaço em disco;
- exibir tamanho ocupado por cada categoria antes da limpeza;
- executar limpeza seletiva ou limpeza geral;
- registrar no log administrativo quem executou a limpeza, quando e quais categorias foram afetadas.

### Segurança da limpeza

- Nunca apagar banco SQLite, `.env`, arquivos de configuração essenciais ou arquivos fora dos diretórios permitidos por uma ação de limpeza.
- Nunca executar `rm -rf`, `del /s` ou equivalente sobre caminhos arbitrários derivados diretamente de entrada do usuário.
- Usar diretórios-raiz permitidos e validação de caminho.
- Operações destrutivas devem exigir confirmação explícita.
- Quando possível, mostrar quantidade de arquivos e espaço que serão liberados antes da execução.
- Operações críticas devem possuir proteção adicional para administradores.

## Tutoriais e ajuda contextual

O sistema deve possuir uma camada de **Ajuda/Tutoriais** integrada à interface, especialmente em Configurações, Usuários, Canais e Playlists.

Cada recurso complexo deve explicar, em linguagem clara:

1. **O que é**.
2. **Para que serve**.
3. **Como funciona**.
4. **Como configurar**.
5. **O que acontece quando o valor é alterado**.
6. **Exemplo de configuração**.
7. **Cuidados e possíveis impactos**.
8. **Como desfazer/restaurar**, quando aplicável.

A ajuda deve aparecer por meio de tooltip, ícone de informação, painel lateral, seção expansível ou tutorial dedicado, sem poluir a interface principal.

### Ajuda para usuários

A tela de usuários deve explicar, por exemplo:

- diferença entre papel/perfil e permissão individual;
- diferença entre visualizar, criar, editar e excluir;
- diferença entre executar e administrar;
- impacto de conceder uma permissão;
- como desativar um usuário sem apagá-lo;
- boas práticas para senhas e contas administrativas.

### Ajuda para Canais

Explicar:

- CH. NO.;
- `tvg-chno`;
- status;
- país/estado/cidade/categoria;
- validação;
- logos;
- edição individual e em massa, quando disponível.

### Ajuda para Playlists/EPG

Explicar:

- geração;
- divisão em partes;
- prefixos e nomes personalizados;
- XMLTV;
- `BASE_URL`;
- links públicos;
- regeneração e exclusão.

### Ajuda para Internet/Saúde

Explicar:

- destino do teste;
- diferença entre disponibilidade e latência;
- intervalo;
- timeout;
- interpretação de ONLINE/OFFLINE;
- limitações de testes ICMP/HTTP e da rede local.

## Funcionalidades úteis adicionais previstas

Avaliar e implementar de forma incremental, sem comprometer compatibilidade:

- pesquisa global no painel;
- filtros e ordenação persistentes por usuário;
- ações em lote para canais e playlists;
- confirmação antes de operações destrutivas;
- desfazer/restaurar quando tecnicamente seguro;
- histórico/auditoria de ações administrativas;
- logs filtráveis por usuário, ação, recurso, data e resultado;
- exportação de relatórios administrativos;
- indicadores de espaço em disco e tamanho das listas;
- histórico de sincronizações e gerações;
- última execução e duração de cada processo;
- identificação clara de processos em andamento;
- prevenção de execuções duplicadas concorrentes;
- notificações de sucesso, alerta e erro;
- mensagens de erro compreensíveis, sem expor stack trace ao usuário final;
- modo de manutenção controlado;
- backup/restore do SQLite com confirmação e validação;
- validação de integridade do banco;
- diagnóstico do ambiente;
- página de status técnico para administradores;
- documentação interna da instalação e operação;
- importação/exportação segura das configurações não secretas;
- controle de sessão e logout seguro;
- proteção contra ações administrativas por requisições forjadas;
- limites e validação de uploads;
- paginação para grandes volumes de canais;
- virtualização de tabelas quando necessária para listas muito grandes.

Novas funcionalidades devem ser adicionadas somente quando houver benefício operacional claro e devem respeitar o modelo de autorização.

## Organização semântica

Backend:

- `src/app.py` — aplicação Flask e compatibilidade das rotas.
- `src/core/scheduler.py` — APScheduler.
- `src/domains/health/internet.py` — Internet/ping.
- `src/domains/playlists/service.py` — publicação/manifests.
- `src/domains/sync/service.py` — pipeline/sincronização/saúde.
- módulos legados (`manager.py`, `parser.py`, `checker.py`, `classifier.py`, `epg.py`) permanecem por compatibilidade.
- novo domínio de usuários/autorização deve concentrar regras de identidade, RBAC, permissões e auditoria, evitando espalhar regras de autorização em `app.py`.
- novo domínio de manutenção deve concentrar limpeza, diagnóstico, espaço em disco, retenção e operações de manutenção.
- ajuda/tutorial deve possuir conteúdo estruturado e reutilizável, separado da lógica de negócio.

Frontend:

- `frontend/react/src/app/App.tsx` — composição da SPA.
- `frontend/react/src/features/` — funcionalidades por domínio.
- `frontend/react/src/components/` — componentes compartilhados.
- `frontend/react/src/services/api.ts` — cliente HTTP.
- `frontend/react/src/types/` — contratos TypeScript.
- `frontend/react/src/main.tsx` — entrypoint.
- `frontend/react/src/styles.scss` — estilos globais.
- autorização deve possuir utilitários/hooks/componentes reutilizáveis para verificar permissões sem duplicar regras em cada página.
- ajuda/tutorial deve ser reutilizável e receber conteúdo estruturado por recurso/campo.

Novas funcionalidades devem entrar no domínio correspondente; não aumentar `app.py` ou `main.tsx` com lógica de negócio.

## Instalação oficial

Na raiz do projeto:

```text
npm run setup
npm run verify
npm run dev
```

Produção:

```text
npm run setup
npm run build
npm run start
```

Docker:

```text
docker compose up -d --build
docker compose logs -f
docker compose down
```

### `npm run setup`

O setup é idempotente, cross-platform e não pode depender de caminhos absolutos da máquina.

1. verifica Node.js;
2. localiza Python 3 (`py -3`/`python` no Windows; `python3`/`python` em Unix);
3. cria `.venv` na raiz quando necessário;
4. verifica se o `.venv` realmente consegue iniciar o Python;
5. recria automaticamente um `.venv` inválido ou criado em outra pasta;
6. instala `requirements.txt` no `.venv`;
7. cria `.env` a partir de `.env.example` quando necessário;
8. usa `npm ci` se `frontend/react/package-lock.json` existir, caso contrário usa `npm install`;
9. executa o build React;
10. confirma `frontend/react/dist/index.html`.

**Não confiar somente na existência de `.venv/Scripts/python.exe`.** Um virtualenv pode ter sido criado em outro diretório e conservar referência ao Python antigo. O setup deve validar o executável antes de usá-lo.

O `setup.js` não pode chamar `main()` inexistente nem `installFrontendDeps()` recursivamente.

### Desenvolvimento

`npm run dev` usa sempre o Python de:

- Windows: `.venv\\Scripts\\python.exe`
- Linux/macOS: `.venv/bin/python`

O caminho é calculado relativo à raiz do projeto. Nunca usar caminhos como `C:\\www\\...` ou `/usr/bin/python.exe`.

Antes de iniciar os processos, `run-dev.js` deve validar o `.venv` e o build. Se o ambiente estiver incompleto ou o virtualenv estiver inválido, executa o setup.

São iniciados backend Flask, servidor público e Vite. No Windows, `npm.cmd` deve ser iniciado de maneira compatível com `spawn`, evitando `EINVAL`.

### Produção

`npm run start` valida `.venv` e `frontend/react/dist/index.html` antes de iniciar backend e servidor público.

## Validação

- `npm run test` — executa os testes Python usando o `.venv` do projeto.
- `npm run typecheck` — executa o build TypeScript/Vite através de script cross-platform.
- `npm run build` — build TypeScript/Vite.
- `npm run verify` — sintaxe Python, testes, build React e arquivos obrigatórios.

Os scripts de validação não devem executar os testes com o Python global quando `.venv` estiver disponível, pois isso causa falsos erros como `ModuleNotFoundError: dotenv`.

No Windows, chamadas a `npm.cmd` devem usar uma estratégia compatível com processos `.cmd` e não devem reintroduzir `spawnSync npm.cmd EINVAL`. Evitar `shell: true` quando não for necessário, pois versões recentes do Node podem emitir o aviso `DEP0190`; quando `shell: true` for tecnicamente indispensável para `.cmd`, os argumentos devem ser controlados e não derivados de entrada não confiável.

## Ambiente

Variáveis principais:

- `BASE_URL`
- `PUBLIC_BASE_URL`
- `WEB_HOST`
- `WEB_PORT`
- `PUBLIC_HOST`
- `PUBLIC_PORT`
- `MAX_CHANNELS_PER_FILE`
- `CONCURRENCY_LIMIT`
- `REQUEST_TIMEOUT`
- `USER_AGENT`
- `REMOTE_M3U_URLS`
- `SCHEDULE_MODE`
- `SCHEDULE_INTERVAL_HOURS`
- `SCHEDULE_CRON_TIME`
- `HEALTH_CHECK_INTERVAL_SECONDS`
- `API_TOKEN`
- `SECRET_KEY`

## Autenticação

Banco novo cria, conforme a documentação atual:

- `admin / admin123`

Roles iniciais:

- `admin` — administração, usuários e configurações.
- `editor` — canais, sincronização e geração.
- `viewer` — leitura/consumo.

Esses papéis são perfis-base. A arquitetura deve permitir permissões granulares adicionais sem depender exclusivamente do nome do papel.

## Compatibilidade e segurança

- Não remover endpoints existentes sem migração documentada.
- Preservar Flask + React + SQLite + scripts de raiz.
- Preservar `LICENSE`, `NOTICE` e créditos de DeldMi.
- Componentes de terceiros mantêm suas licenças/créditos.
- `.env`, bancos SQLite, logs, `output`, `dist`, `node_modules`, `.venv` e caches Python não devem entrar no Git.
- Nunca gravar caminhos absolutos da máquina nos scripts.
- O servidor público não pode expor menu ou APIs administrativas.
- Toda rota administrativa deve validar autenticação e autorização no backend.
- Não confiar em permissões enviadas pelo frontend.
- Não expor hashes de senha, tokens ou segredos em APIs de usuário.
- Operações destrutivas devem possuir autorização, validação de escopo e confirmação apropriada.

## Histórico Git

O histórico remoto foi limpo em 2026-09-15. Se um segredo voltar a ser publicado, revogar/trocar o segredo primeiro e somente depois limpar o histórico.

```bash
git ls-files -ci --exclude-standard
git rm --cached -- caminho/do/arquivo
```

## Problemas corrigidos nesta versão

- `npm ci` sem lockfile: o setup usa `npm ci` quando há lockfile e `npm install` quando não há.
- `main is not defined`: corrigido em `scripts/setup.js`.
- Recursão de `installFrontendDeps()`: removida.
- `/usr/bin\\python.exe`: não é mais usado pelo projeto.
- `.venv` em outro diretório: o setup detecta virtualenv inválido e recria o ambiente local.
- `ModuleNotFoundError: dotenv` nos testes: `verify` e `npm test` usam o Python do `.venv`.
- `spawnSync npm.cmd EINVAL`: scripts de npm no Windows usam execução compatível com `.cmd`.
- `run-dev.js`: valida/repara o ambiente antes de iniciar e não aceita um `.venv` quebrado apenas porque o arquivo existe.
- `run-prod.js`: valida ambiente e encerra processos irmãos de forma controlada.
- erro TypeScript por `send` ausente em `ChannelsPage.tsx`: corrigido.
- erro Sass por variável `$text` ausente: build estabilizado sem alterar a paleta existente.

## Recuperação de ambiente Windows

Se um projeto tiver sido movido de uma pasta para outra, por exemplo de `C:\\www\\m3u_processor` para outra unidade, o `.venv` antigo pode continuar apontando internamente para o Python da instalação anterior. **Não copiar `.venv` entre máquinas ou diretórios.**

A ação oficial é:

```text
npm run setup
```

O próprio setup deve detectar e recriar o ambiente virtual. Não é necessário alterar scripts para apontar para `/usr/bin/python.exe` ou para um caminho absoluto do computador.

## Estado atual — navegação local e Configurações (2026-09-17)

- Vite em desenvolvimento usa `base: "/"`; build local servido pelo Flask usa `/app-assets/`; Cloudflare Pages usa `/`.
- `App.tsx` também normaliza o prefixo legado `/app-assets` para manter compatibilidade.
- Flask serve `/settings/<subpath>` para permitir acesso direto/recarregamento de `/settings/themes`, `/settings/resources` e futuras subseções.
- A tela `/settings/themes` possui seleção de temas embutidos, criação/exclusão de temas personalizados e tema individual por usuário. Essas funções devem ser preservadas em futuras alterações.
- Portas locais: `5173` = Vite frontend; `5000` = Flask/API; `8080` = servidor público de playlists/EPG.
- Validação obrigatória após mudanças de navegação: `npm run verify`, `npm run dev`, testar todas as rotas e recarregar diretamente cada página.

## Próxima implementação prioritária

A próxima etapa do projeto deve implementar e validar, nesta ordem:

1. **RBAC granular de verdade**, corrigindo o caso em que `viewer` consegue receber informações ou ações além do permitido.
2. Tela de criação/edição de usuários com campos obrigatórios/opcionais e documentação contextual.
3. Matriz detalhada de permissões por recurso e ação: visualizar, criar, editar, excluir, executar e administrar.
4. Proteção equivalente no backend para todas as APIs.
5. Tela de Configurações → Manutenção/Limpeza geral com operações seletivas, estimativa de espaço, confirmação e auditoria.
6. Sistema de tutoriais/ajuda contextual para configurações, usuários, canais, playlists, EPG e monitoramento.
7. Auditoria/logs administrativos e histórico das operações relevantes.
8. Diagnóstico de integridade, espaço em disco, banco, processamento e serviços.
9. Melhorias de usabilidade para grandes listas e operações em lote.
10. Testes automatizados cobrindo permissões permitidas e negadas, incluindo testes de API com usuário `viewer`.
11. Testes de segurança para garantir que ocultar elementos no frontend não seja a única proteção.
12. Revalidar `npm run test`, `npm run typecheck`, `npm run verify`, execução real e Docker após cada conjunto de mudanças.
13. Só considerar a versão pronta após validar instalação limpa, execução, funcionalidades, autorização e empacotamento.
14. no .env so tem que ter informaçoes de abiente o que precisa para o projeto inicia e ja fica fuionado o resto pode fica no db e o projeto ja vem pre configurado com campos obrigatorios penenchido para iviatr erros na intalação do db.
15. A parte de tema onde voce criar tem que ser parecido com o do usuario so que com foco diferente tipo voce cai criando e vai apareseno pode ser editado as ciação novas as do sitema recomando nao ser editavel pode ser copiada.
16. na pagina tinha alguma fuções e opiçoes antes e agora nao tem mas .
nao consigo acesa o porjeto localmente so remoto (Loading module from “http://localhost:5000/assets/index-DRRGoslW.js” was blocked because of a disallowed MIME type (“text/html”). localhost:5000
Layout was forced before the page was fully loaded. If stylesheets are not yet loaded this may cause a flash of unstyled content. index.js:1583:1
Loading failed for the module with source “http://localhost:5000/assets/index-DRRGoslW.js”. localhost:5000:9:69
Loading module from “http://localhost:5000/assets/index-DRRGoslW.js” was blocked because of a disallowed MIME type (“text/html”). }. e na porta 5173 so fuciona a pagina principal {The server is configured with a public base URL of /app-assets/ - did you mean to visit /app-assets/channels instead?}.
17. uma pagina nova com as mesma fuionalidades so que convertida para EPG. para adiministrar as guia de cada canal administrar e configura guia dos canas com horarios dias e entre outras informaçoes de progamação de canasl sempre siconizando com o canal e o link que foi criado (se quiser) ou os novos que vai ser criado (se quiser.) . tudo bem estuturado com todas is requisito que tem neste arquivo e documentos.

18. a pagina incial a "🟢 ONLINE Ping 34.63 ms" pode na teg <header> no sento da tela mostrando em todas as paginas e o PIPELINE o Progresso da operação pode fica pegando da borda de baixo so o caregamento  e a etapa que esta no sentro do caregamento com %. essas duas informaçoes pode trira ta pagina pricipal.
19. DISTRIBUIÇÃO e ATIVIDADE deixa a baixo de MONITORAMENTO AO VIVO e Status do processo, Canais catalogados, Online e Offline / removidos fica assima

20. A lista de canas nuca se apaga do db tem que ter uma fomrma de o usuario remover tbm do db porque seme mostra la mesmo eu nao colocando lista de canas. opção para apaga tudo do banco visualizar o que tem no banco ele deve sempre apareser na pagina Canais e editor verificando ou nao se nao verificado vai fica com o estado verificado se verificado ou vai esta on ou off. mas como ele ja verifica em tempo real ele vai esta mundado altomaticamente. a nao ser que eu coloque uma lista nova de canas com o link ou adicione um canal novo e nao coloque como on ou off.


## Prioridades gerais

1. Instalação reproduzível.
2. Execução confiável em Windows e Linux.
3. Segurança e autorização correta no backend.
4. Compatibilidade Flask/React.
5. Integridade dos dados e operações destrutivas seguras.
6. UI coerente, acessível e compreensível.
7. Playlists/EPG com nome personalizado.
8. Monitoramento de Internet e canais.
9. Organização semântica e documentação atualizada.
10. Tutoriais e ajuda contextual.
11. Manutenção, diagnóstico e auditoria.
12. Desempenho para grandes volumes.
13. as fuionablidade sempre tem que continuar a nao ser que eu pessa para tirar. ela pode ser remanejada com intuito de organização, sematico, desigino e requisito basico de progamação.

14. A base deste porjeto e analizar, testar, prosesalo e gera links tem que ter uma administrção compreta (Analise teste edição criação etc).