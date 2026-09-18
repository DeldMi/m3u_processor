# AGENTS.md

Contexto operacional e contrato de desenvolvimento do **M3U Processor / M3U Architect** para IAs, copilotos e colaboradores.

> **Regra fundamental:** funcionalidades existentes devem ser preservadas. Organização, refatoração, melhoria visual, modularização ou adequação arquitetural podem mover uma funcionalidade, mas não podem removê-la sem solicitação explícita do titular do projeto.

---

# 1. Identidade do projeto

## 1.1 Informações gerais

* **Projeto:** M3U Processor / M3U Architect
* **Autor/titular declarado:** DeldMi
* **Licença:** `LICENSE`
* **Créditos:** `NOTICE`

## 1.2 Stack principal

### Backend

* Python
* Flask
* SQLite
* APScheduler

### Frontend

* React
* Vite
* TypeScript
* Tailwind CSS
* SCSS

### Execução

* Windows
* Linux
* macOS
* Docker

## 1.3 Finalidade

O sistema deve permitir administrar todo o ciclo operacional de listas M3U/M3U8:

1. analisar listas;
2. importar canais;
3. interpretar metadados IPTV;
4. classificar canais;
5. testar disponibilidade;
6. monitorar saúde;
7. editar canais;
8. criar canais;
9. remover canais explicitamente;
10. gerar playlists;
11. gerar XMLTV/EPG;
12. dividir arquivos em blocos;
13. publicar arquivos;
14. administrar links;
15. sincronizar fontes;
16. administrar usuários;
17. controlar permissões;
18. configurar o sistema;
19. executar manutenção;
20. auditar operações;
21. diagnosticar o ambiente.

A base do projeto é:

> **analisar → testar → processar → administrar → gerar → publicar → monitorar.**

---

# 2. Princípios fundamentais

## 2.1 Preservação funcional

Nenhuma funcionalidade existente pode ser removida sem solicitação explícita.

Uma funcionalidade pode ser:

* movida;
* reorganizada;
* modularizada;
* renomeada;
* redesenhada;
* agrupada;
* transformada em componente;
* transferida para outro domínio.

Porém, seu comportamento equivalente deve continuar disponível.

## 2.2 Fonte da verdade

O backend é a fonte de verdade para:

* autenticação;
* autorização;
* permissões;
* dados;
* operações administrativas;
* estado persistido;
* segurança.

O frontend não pode ser considerado mecanismo de segurança.

Esconder um botão **não significa impedir a operação**.

## 2.3 Prioridade de desenvolvimento

Sempre priorizar:

1. integridade dos dados;
2. segurança;
3. autorização;
4. compatibilidade;
5. funcionamento;
6. testes;
7. desempenho;
8. arquitetura;
9. organização;
10. estética.

Não realizar refatorações estéticas enquanto houver erro crítico de funcionamento ou perda de funcionalidade.

---

# 3. Arquitetura semântica

## 3.1 Backend

Estrutura recomendada:

```text
src/
├── app.py
├── core/
│   └── scheduler.py
│
├── domains/
│   ├── authz/
│   ├── channels/
│   ├── epg/
│   ├── health/
│   ├── maintenance/
│   ├── playlists/
│   ├── sync/
│   ├── users/
│   └── help/
│
├── manager.py
├── parser.py
├── checker.py
├── classifier.py
└── epg.py
```

### `src/app.py`

Responsável por:

* criação/configuração da aplicação Flask;
* compatibilidade das rotas existentes;
* registro de blueprints/rotas;
* integração entre domínios.

Não adicionar lógica de negócio nova diretamente em `app.py` quando existir um domínio apropriado.

### Domínios

#### `domains/authz/`

Responsável por:

* identidade;
* autenticação;
* RBAC;
* permissões;
* autorização;
* auditoria relacionada à autorização.

#### `domains/channels/`

Responsável por:

* canais;
* CH. NO.;
* metadados IPTV;
* classificação;
* status;
* logos;
* filtros;
* edição;
* criação;
* exclusão explícita.

#### `domains/epg/`

Responsável por:

* programas;
* grades;
* horários;
* dias;
* XMLTV;
* associação programa/canal;
* sincronização EPG;
* configuração de fontes EPG.

#### `domains/health/`

Responsável por:

* Internet;
* latência;
* testes;
* disponibilidade;
* saúde dos canais.

#### `domains/maintenance/`

Responsável por:

* limpeza;
* diagnóstico;
* espaço em disco;
* retenção;
* rotação de logs;
* backup;
* restauração;
* integridade.

#### `domains/playlists/`

Responsável por:

* criação;
* geração;
* publicação;
* manifests;
* nomes;
* prefixos;
* arquivos;
* links públicos.

#### `domains/sync/`

Responsável por:

* sincronização;
* processamento;
* pipeline;
* importação;
* atualização de canais;
* execução de processos.

#### `domains/users/`

Responsável por:

* cadastro;
* edição;
* status;
* perfis;
* informações administrativas dos usuários.

#### `domains/help/`

Responsável por:

* tutoriais;
* ajuda contextual;
* documentação interna;
* conteúdo explicativo estruturado.

## 3.2 Módulos legados

Os módulos existentes devem permanecer por compatibilidade quando ainda forem utilizados:

```text
manager.py
parser.py
checker.py
classifier.py
epg.py
```

Eles podem ser gradualmente incorporados aos novos domínios, mas não devem ser removidos sem migração funcional comprovada.

---

# 4. Arquitetura do frontend

Estrutura:

```text
frontend/react/src/
├── app/
│   └── App.tsx
│
├── features/
│   ├── channels/
│   ├── epg/
│   ├── health/
│   ├── maintenance/
│   ├── playlists/
│   ├── settings/
│   ├── sync/
│   └── users/
│
├── components/
├── services/
│   └── api.ts
│
├── types/
├── main.tsx
└── styles.scss
```

### `App.tsx`

Responsável principalmente pela composição da aplicação.

Não concentrar lógica de negócio.

### `main.tsx`

Deve permanecer como entrypoint.

Não adicionar regras de domínio.

### `services/api.ts`

Responsável pelo cliente HTTP.

Deve diferenciar claramente:

* erro de rede;
* erro HTTP;
* resposta JSON inválida;
* erro operacional da API.

### `types/`

Deve conter os contratos TypeScript utilizados pelo frontend.

### Autorização no frontend

Criar utilitários/hooks/componentes reutilizáveis para:

* verificar permissões;
* ocultar menus;
* ocultar ações;
* proteger componentes;
* controlar recursos administrativos.

Não duplicar a mesma regra de autorização em cada página.

A autorização definitiva permanece no backend.

---

# 5. Regras de dados e banco

## 5.1 SQLite

O banco deve ser persistente e funcionar como fonte de verdade dos dados administrativos e operacionais.

## 5.2 Canais

Os canais existentes no banco **não devem desaparecer automaticamente**.

Durante:

* sincronização;
* atualização;
* health check;
* processamento;
* regeneração de playlist;

um canal OFFLINE não deve ser automaticamente apagado.

### Regra

```text
OFFLINE ≠ EXCLUÍDO
```

A exclusão persistida deve ser uma ação explícita do usuário e exigir a permissão correspondente.

## 5.3 Visualização do banco

A página **Canais e Editor** deve permitir visualizar os canais persistidos no banco mesmo quando nenhuma lista externa estiver sendo processada.

O usuário deve conseguir:

* visualizar o conteúdo do banco;
* pesquisar;
* filtrar;
* ordenar;
* editar;
* criar;
* alterar status;
* excluir explicitamente;
* realizar limpeza administrativa do banco quando autorizado.

Deve existir uma opção administrativa para:

> **Excluir todos os canais do banco**

Essa operação deve:

* exigir permissão;
* exigir confirmação;
* ser auditada;
* informar a quantidade afetada;
* nunca ocorrer automaticamente.

## 5.4 Estado dos canais

Cada canal deve possuir estado operacional coerente.

Estados devem distinguir, quando aplicável:

* não verificado;
* ONLINE;
* OFFLINE;
* removido/excluído.

Quando um canal ainda não tiver sido verificado:

```text
status = não verificado
```

Após a verificação:

```text
ONLINE
ou
OFFLINE
```

O health check pode atualizar automaticamente o estado persistido.

### Exceções

Um canal recém-adicionado manualmente ou importado pode permanecer como **não verificado** até que o sistema execute sua primeira verificação.

---

# 6. Painel Geral

O Dashboard deve apresentar informações operacionais respeitando RBAC.

## 6.1 Monitoramento de Internet

O indicador:

```text
🟢 ONLINE
Ping 34.63 ms
```

não deve ficar exclusivamente no Dashboard.

Ele deve aparecer centralizado no `<header>` e permanecer visível em todas as páginas.

Deve apresentar:

* ONLINE/OFFLINE;
* latência;
* destino utilizado no teste.

O valor é apenas exemplo visual. O sistema deve exibir o resultado real.

## 6.2 Pipeline

O indicador de progresso do pipeline não deve ocupar espaço permanente no Dashboard.

O componente deve:

* aparecer próximo à borda inferior da tela;
* mostrar carregamento/progresso;
* apresentar a etapa atual;
* mostrar percentual;
* permanecer discreto;
* permitir acompanhar operações sem bloquear a navegação quando tecnicamente seguro.

O indicador anterior de pipeline no Dashboard pode ser removido **somente porque foi remanejado para a interface global**, preservando a funcionalidade.

## 6.3 Organização do Dashboard

A ordem visual deve ser:

### 1. Monitoramento ao vivo

Primeiro bloco principal.

### 2. Indicadores operacionais

Acima da área inferior:

* Status do processo;
* Canais catalogados;
* Online;
* Offline/removidos.

### 3. Distribuição

Deve aparecer abaixo de **Monitoramento ao Vivo**.

### 4. Atividade

Deve aparecer abaixo de **Monitoramento ao Vivo**.

---

# 7. Canais e Editor

A página deve permitir administração completa dos canais.

## 7.1 Dados

Suportar:

* CH. NO.;
* `tvg-chno`;
* nome;
* grupo;
* país;
* estado;
* cidade;
* categoria;
* URL;
* logo;
* status;
* demais metadados IPTV compatíveis.

## 7.2 CH. NO.

O campo **CH. NO.** deve:

* ser editável;
* persistir no SQLite;
* ser utilizado quando aplicável na geração;
* manter compatibilidade com `tvg-chno`.

## 7.3 Filtros

Filtros mínimos:

* país;
* estado;
* cidade;
* categoria;
* status.

## 7.4 Tabela

Deve possuir:

* ordenação por cabeçalho;
* seleção persistente de colunas;
* paginação quando necessário;
* virtualização quando o volume justificar.

## 7.5 Logos

Permitir:

* upload local;
* validação;
* nome seguro;
* diretório permitido;
* associação ao canal.

## 7.6 Ações

Permitir, conforme RBAC:

* visualizar;
* criar;
* editar;
* excluir;
* alterar status;
* ações em lote.

---

# 8. Playlists

A administração de playlists deve suportar:

* criar;
* editar;
* regenerar;
* visualizar;
* baixar;
* excluir;
* publicar;
* administrar links.

## 8.1 Personalização

Permitir:

* nome personalizado;
* prefixo;
* nome do arquivo;
* divisão em partes;
* quantidade máxima de canais por arquivo.

## 8.2 M3U/XMLTV

Quando uma playlist tiver XMLTV associado, a renomeação deve permanecer pareada quando aplicável.

Exemplo:

```text
playlist:
meus-canais.m3u

EPG:
meus-canais.xml
```

## 8.3 BASE_URL

`BASE_URL` continua sendo a base pública global.

Não substituir `BASE_URL` por valores específicos de cada playlist sem requisito explícito.

## 8.4 Servidor público

O servidor público deve expor somente recursos públicos necessários, especialmente:

```text
/playlist/...
/epg/...
```

Não expor APIs administrativas pelo servidor público.

---

# 9. EPG — Guia de Programação

Deve existir uma página específica para administração de EPG, mantendo a mesma qualidade estrutural das demais áreas.

## 9.1 Objetivo

Permitir administrar a grade de programação de cada canal.

## 9.2 Funcionalidades

Permitir:

* visualizar programação;
* criar programa;
* editar programa;
* excluir programa;
* definir horário inicial;
* definir horário final;
* definir duração;
* definir dias;
* definir recorrência;
* definir título;
* definir descrição;
* categoria;
* temporada;
* episódio;
* classificação indicativa quando aplicável;
* imagem/logo quando aplicável;
* identificadores XMLTV;
* associação com canal.

## 9.3 Associação com canais

A programação deve estar associada ao canal correspondente.

A interface deve permitir administrar:

```text
Canal
 └── Grade
      ├── Programa
      ├── Programa
      ├── Programa
      └── Programa
```

## 9.4 Sincronização

A página deve permitir sincronizar o EPG:

* com o canal;
* com o link da playlist;
* com uma fonte EPG;
* com um novo link criado;
* manualmente, quando aplicável.

Quando houver uma fonte externa, a associação deve permanecer identificável.

## 9.5 XMLTV

A geração deve preservar compatibilidade com XMLTV.

Deve ser possível:

* gerar;
* regenerar;
* visualizar;
* publicar;
* baixar;
* excluir;
* administrar permissões.

---

# 10. Internet e Saúde

## 10.1 Teste de Internet

Configurações:

* destino;
* intervalo;
* timeout;
* método utilizado;
* resultado;
* latência.

## 10.2 Saúde dos canais

O health check deve:

* testar canais automaticamente;
* atualizar status;
* preservar canais OFFLINE;
* não regenerar playlists desnecessariamente;
* não excluir dados.

## 10.3 Limitações

A interface deve explicar que:

* ICMP pode ser bloqueado;
* HTTP/HTTPS pode apresentar comportamento diferente;
* disponibilidade do servidor não garante disponibilidade do conteúdo;
* latência não representa necessariamente qualidade completa do stream.

---

# 11. RBAC e autorização

## 11.1 Ações

Permissões mínimas:

```text
view
create
edit
delete
execute
admin
```

## 11.2 Recursos

Recursos mínimos:

```text
dashboard
channels
playlists
epg
sync
health
settings
users
logs
maintenance
public_files
system
```

## 11.3 Matriz

A UI deve apresentar:

| Recurso           | Visualizar | Criar | Editar | Excluir | Executar | Administrar |
| ----------------- | ---------: | ----: | -----: | ------: | -------: | ----------: |
| Dashboard         |          ✓ |     — |      — |       — |        — |           — |
| Canais            |          ✓ |     ✓ |      ✓ |       ✓ |        ✓ |           ✓ |
| Playlists         |          ✓ |     ✓ |      ✓ |       ✓ |        ✓ |           ✓ |
| EPG               |          ✓ |     ✓ |      ✓ |       ✓ |        ✓ |           ✓ |
| Sincronização     |          ✓ |     — |      — |       — |        ✓ |           ✓ |
| Saúde             |          ✓ |     — |      — |       — |        ✓ |           ✓ |
| Configurações     |          ✓ |     — |      ✓ |       — |        ✓ |           ✓ |
| Usuários          |          ✓ |     ✓ |      ✓ |       ✓ |        — |           ✓ |
| Logs              |          ✓ |     — |      — |       — |        — |           ✓ |
| Manutenção        |          ✓ |     — |      — |       — |        ✓ |           ✓ |
| Arquivos públicos |          ✓ |     ✓ |      ✓ |       ✓ |        ✓ |           ✓ |
| Sistema           |          ✓ |     — |      ✓ |       — |        ✓ |           ✓ |

A matriz acima representa a estrutura conceitual. A implementação deve respeitar o modelo real de dados e permitir permissões granulares.

## 11.4 Backend

Toda operação protegida deve validar:

1. autenticação;
2. usuário;
3. recurso;
4. ação;
5. escopo.

Usuário sem permissão deve receber:

```http
403 Forbidden
```

Não executar parcialmente a operação.

## 11.5 Frontend

O frontend deve:

* esconder menus não autorizados;
* esconder botões;
* esconder métricas;
* esconder campos;
* impedir fluxos não autorizados.

Porém:

> Frontend nunca substitui autorização do backend.

## 11.6 `/api/me`

Pode retornar apenas informações necessárias à interface, como:

* usuário;
* nome de exibição;
* perfil;
* permissões;
* preferências permitidas.

Nunca retornar:

* senha;
* hash;
* token;
* `SECRET_KEY`;
* `API_TOKEN`;
* `ADMIN_INITIAL_PASSWORD`;
* segredos;
* informações administrativas desnecessárias.

---

# 12. Usuários

## 12.1 Cadastro

Campos obrigatórios:

* login único;
* nome de exibição;
* senha no cadastro;
* papel/perfil-base;
* status ativo/inativo.

Campos opcionais:

* nome completo;
* e-mail;
* avatar;
* telefone;
* descrição;
* departamento/grupo;
* expiração;
* preferências;
* informações administrativas não sensíveis.

## 12.2 Senha

Na edição:

* campo vazio = manter senha atual;
* nunca exibir senha;
* nunca armazenar senha em texto puro;
* nunca retornar senha pela API.

## 12.3 Perfil x permissão

A interface deve explicar claramente:

```text
Perfil
↓
conjunto inicial de permissões

Permissão
↓
capacidade específica

Recurso + ação
↓
escopo real da operação
```

---

# 13. Configurações

## 13.1 Princípio

O `.env` deve conter somente informações necessárias ao ambiente de execução.

Não usar `.env` como banco de configurações funcionais.

## 13.2 `.env`

Deve conter apenas:

* informações de ambiente;
* portas;
* hosts;
* URLs necessárias;
* segredos;
* configurações necessárias para inicialização.

Configurações funcionais devem ficar no SQLite quando apropriado.

## 13.3 Banco pré-configurado

Novas instalações devem possuir valores padrão seguros e campos obrigatórios já preenchidos quando possível.

Objetivo:

> o usuário executa o setup e consegue iniciar o sistema sem precisar preencher manualmente configurações que possuam valores padrão válidos.

---

# 14. Temas

## 14.1 Temas do sistema

Temas fornecidos pelo sistema devem:

* possuir design consistente;
* ser recomendados;
* não permitir alteração destrutiva direta;
* poder ser copiados.

## 14.2 Temas personalizados

O usuário deve poder:

* criar tema;
* editar tema criado;
* excluir tema criado;
* duplicar tema;
* selecionar tema por usuário.

Fluxo:

```text
Tema do sistema
      ↓
Copiar
      ↓
Tema personalizado
      ↓
Editar
```

O usuário deve conseguir perceber visualmente que o tema é:

* sistema;
* personalizado;
* ativo;
* disponível para cópia.

---

# 15. Manutenção e limpeza

A manutenção deve ser seletiva, segura e auditável.

## 15.1 Categorias

Permitir:

* cache;
* temporários;
* arquivos de entrada temporários;
* arquivos de saída antigos;
* playlists geradas;
* XMLTV/EPG;
* dados temporários de processamento;
* logs antigos;
* rotação/compactação de logs;
* cache frontend/build quando seguro.

## 15.2 Diagnóstico

Exibir:

* espaço total;
* espaço utilizado;
* espaço livre;
* tamanho por categoria;
* quantidade de arquivos;
* integridade do banco;
* estado dos serviços;
* estado do processamento.

## 15.3 Segurança

Nunca apagar automaticamente:

```text
database
.env
configuração essencial
arquivos fora da raiz permitida
```

Nunca executar operações destrutivas arbitrárias derivadas diretamente da entrada do usuário.

Evitar:

```text
rm -rf <entrada-do-usuario>
del /s <entrada-do-usuario>
```

## 15.4 Operações destrutivas

Devem exigir:

* permissão;
* confirmação;
* validação de escopo;
* auditoria.

Sempre que possível mostrar:

* arquivos afetados;
* espaço liberado estimado;
* categorias selecionadas.

---

# 16. Ajuda e tutoriais

Toda área complexa deve possuir ajuda contextual.

## 16.1 Estrutura

Cada ajuda deve explicar:

1. o que é;
2. para que serve;
3. como funciona;
4. como configurar;
5. impacto da alteração;
6. exemplo;
7. cuidados;
8. como restaurar.

## 16.2 Áreas obrigatórias

* Configurações;
* Usuários;
* Canais;
* Playlists;
* EPG;
* Internet;
* Saúde;
* Manutenção;
* Sincronização.

A ajuda pode aparecer como:

* tooltip;
* ícone `i`;
* painel lateral;
* accordion;
* modal;
* tutorial dedicado.

---

# 17. Segurança

## 17.1 TLS

TLS deve ser verificado por padrão.

Certificados inválidos somente podem ser aceitos quando:

```text
ALLOW_INSECURE_TLS=1
```

## 17.2 Segredos

Nunca expor:

* `SECRET_KEY`;
* `API_TOKEN`;
* `ADMIN_INITIAL_PASSWORD`;
* senhas;
* hashes;
* tokens;
* credenciais.

## 17.3 Logs

Logs devem redigir credenciais presentes em URLs.

Não registrar o ambiente inteiro.

Não registrar segredos.

## 17.4 Uploads

Validar:

* extensão;
* nome;
* tamanho;
* caminho;
* diretório permitido;
* tipo de arquivo quando aplicável.

## 17.5 Arquivos públicos

Aceitar somente nomes e formatos permitidos.

Nunca permitir path traversal.

## 17.6 Exclusões

Nunca permitir que uma entrada de usuário determine arbitrariamente o caminho de exclusão.

---

# 18. Autenticação inicial

Novas instalações não devem depender de senha pública fixa.

O setup deve gerar:

```text
ADMIN_INITIAL_PASSWORD
```

de forma aleatória quando necessário.

A senha inicial deve:

* ser tratada como segredo;
* não aparecer na API;
* não aparecer em logs;
* não ser incorporada ao código.

Bancos criados manualmente devem possuir mecanismo seguro para gerar credencial inicial única.

---

# 19. Variáveis de ambiente

Variáveis principais:

```text
BASE_URL
PUBLIC_BASE_URL

WEB_HOST
WEB_PORT

PUBLIC_HOST
PUBLIC_PORT

MAX_CHANNELS_PER_FILE
CONCURRENCY_LIMIT
REQUEST_TIMEOUT
USER_AGENT

REMOTE_M3U_URLS

SCHEDULE_MODE
SCHEDULE_INTERVAL_HOURS
SCHEDULE_CRON_TIME

HEALTH_CHECK_INTERVAL_SECONDS

API_TOKEN
SECRET_KEY
ALLOW_INSECURE_TLS
```

Novas variáveis devem ser adicionadas somente quando forem realmente necessárias ao ambiente.

Configurações funcionais devem preferencialmente permanecer no banco.

---

# 20. Instalação

## 20.1 Instalação oficial

Na raiz:

```bash
npm run setup
npm run verify
npm run dev
```

## 20.2 Produção

```bash
npm run setup
npm run build
npm run start
```

## 20.3 Docker

```bash
docker compose up -d --build
docker compose logs -f
docker compose down
```

---

# 21. `npm run setup`

O setup deve ser:

* idempotente;
* cross-platform;
* relativo à raiz;
* seguro;
* reproduzível.

## 21.1 Etapas

1. verificar Node.js;
2. localizar Python 3;
3. criar `.venv` se necessário;
4. validar o `.venv`;
5. recriar `.venv` inválido;
6. instalar `requirements.txt`;
7. criar `.env` a partir de `.env.example`;
8. instalar dependências frontend;
9. executar build;
10. validar `frontend/react/dist/index.html`;
11. preparar banco;
12. preparar configuração inicial;
13. garantir que o sistema possa iniciar.

## 21.2 Python

Windows:

```text
.venv\Scripts\python.exe
```

Linux/macOS:

```text
.venv/bin/python
```

Nunca usar caminhos absolutos da máquina.

Não confiar apenas na existência do executável.

O ambiente deve ser validado executando Python.

## 21.3 Dependências frontend

Se existir:

```text
frontend/react/package-lock.json
```

usar:

```bash
npm ci
```

Caso contrário:

```bash
npm install
```

## 21.4 Regras históricas

O setup não pode:

* chamar `main()` inexistente;
* executar `installFrontendDeps()` recursivamente;
* depender de `.venv` de outra máquina;
* usar `/usr/bin/python.exe`;
* usar caminhos absolutos.

---

# 22. Desenvolvimento local

## 22.1 Portas

```text
5173 = Vite
5000 = Flask/API
8080 = servidor público M3U/EPG
```

## 22.2 `npm run dev`

Deve:

1. validar `.venv`;
2. corrigir/recriar ambiente se necessário;
3. validar build;
4. iniciar Flask;
5. iniciar servidor público;
6. iniciar Vite.

## 22.3 Windows

Ao executar `.cmd`, utilizar estratégia compatível com `spawn`.

Evitar:

```text
spawnSync npm.cmd EINVAL
```

Não utilizar `shell: true` desnecessariamente.

Quando `shell: true` for indispensável:

* argumentos devem ser controlados;
* nenhuma entrada não confiável pode ser incorporada ao comando.

---

# 23. Produção

`npm run start` deve:

1. validar `.venv`;
2. validar build;
3. iniciar backend;
4. iniciar servidor público;
5. encerrar processos irmãos de maneira controlada.

---

# 24. Frontend e caminhos de build

## 24.1 Vite

Desenvolvimento:

```text
base: "/"
```

Build local servido pelo Flask:

```text
/app-assets/
```

Cloudflare Pages:

```text
/
```

## 24.2 Compatibilidade

`App.tsx` deve normalizar o prefixo legado `/app-assets`.

Flask deve aceitar:

```text
/app-assets/*
/assets/*
```

quando necessário para compatibilidade com builds existentes.

---

# 25. Problema crítico de acesso local

O ambiente local deve corrigir o problema:

```text
Loading module from
"http://localhost:5000/assets/index-DRRGoslW.js"
was blocked because of a disallowed MIME type ("text/html")
```

Esse erro normalmente indica que o navegador solicitou um módulo JavaScript, mas o Flask devolveu HTML.

A correção deve garantir:

```text
/assets/*.js
```

e:

```text
/app-assets/*.js
```

retornem o arquivo JavaScript real com MIME adequado.

Não utilizar fallback HTML para arquivos estáticos existentes.

## 25.1 Porta 5173

O Vite deve permitir acesso direto às rotas SPA.

Não deve ocorrer:

```text
The server is configured with a public base URL of /app-assets/
```

ao acessar:

```text
http://localhost:5173/channels
```

O desenvolvimento deve utilizar:

```text
base: "/"
```

e permitir navegação direta/reload das páginas.

## 25.2 Rotas

Devem funcionar diretamente:

```text
/
channels
playlists
epg
settings
settings/themes
settings/resources
users
...
```

Após alterações de navegação, testar:

1. navegação pelo menu;
2. acesso direto;
3. reload;
4. voltar/avançar do navegador;
5. build;
6. servidor Flask;
7. Vite.

---

# 26. Rotas de Configurações

O Flask deve permitir acesso direto a:

```text
/settings/<subpath>
```

incluindo:

```text
/settings/themes
/settings/resources
```

e futuras subseções.

---

# 27. Temas — estado conhecido

A página:

```text
/settings/themes
```

possui:

* temas embutidos;
* criação de temas personalizados;
* exclusão de temas personalizados;
* tema individual por usuário.

Essas funções devem ser preservadas.

Temas de sistema devem ser tratados como modelos protegidos.

---

# 28. Funcionalidades existentes que não podem desaparecer

Antes de alterar qualquer página, comparar a implementação atual com versões anteriores quando necessário.

Se uma página possuía:

* botão;
* filtro;
* tabela;
* ação;
* configuração;
* indicador;
* modal;
* menu;
* campo;
* processo;

e ele não está mais presente, deve-se determinar se:

1. foi removido acidentalmente;
2. foi deslocado;
3. foi substituído;
4. foi incorporado a outro fluxo.

Somente considerar removido quando houver solicitação explícita.

---

# 29. Pipeline

O pipeline deve permitir acompanhar operações como:

```text
entrada
↓
análise
↓
processamento
↓
validação
↓
classificação
↓
geração
↓
publicação
```

Deve informar:

* etapa atual;
* percentual;
* progresso;
* sucesso;
* aviso;
* erro;
* duração quando possível.

Evitar execuções concorrentes duplicadas quando isso puder corromper resultados.

---

# 30. Sincronização

A sincronização deve:

* preservar dados válidos existentes;
* atualizar canais;
* detectar novos canais;
* atualizar metadados;
* executar health check quando configurado;
* não apagar canais OFFLINE;
* registrar resultado;
* permitir consulta do histórico.

---

# 31. Auditoria e logs

Registrar operações administrativas relevantes.

Exemplos:

```text
usuário
ação
recurso
data/hora
resultado
quantidade afetada
```

Não registrar:

* senha;
* token;
* segredo;
* ambiente inteiro;
* credenciais.

Logs devem permitir filtros por:

* usuário;
* ação;
* recurso;
* data;
* resultado.

---

# 32. Diagnóstico

Administradores devem possuir diagnóstico técnico contendo, quando apropriado:

* versão;
* Python;
* Node;
* banco;
* espaço em disco;
* diretórios;
* serviços;
* portas;
* estado do scheduler;
* estado do backend;
* estado do frontend;
* estado do servidor público;
* integridade do banco;
* últimos erros relevantes.

Informações sensíveis devem ser ocultadas.

---

# 33. Melhorias operacionais previstas

Implementar incrementalmente, sem comprometer compatibilidade:

* pesquisa global;
* filtros persistentes;
* ordenação persistente;
* ações em lote;
* confirmação destrutiva;
* desfazer/restaurar;
* auditoria;
* relatórios;
* espaço em disco;
* histórico de sincronização;
* histórico de geração;
* duração de processos;
* estado de processos;
* notificações;
* mensagens de erro compreensíveis;
* modo de manutenção;
* backup/restore SQLite;
* diagnóstico;
* importação/exportação de configurações não secretas;
* controle de sessão;
* logout seguro;
* proteção contra requisições forjadas;
* limites de upload;
* paginação;
* virtualização.

---

# 34. Compatibilidade

Não remover endpoints existentes sem:

1. identificar dependências;
2. criar migração;
3. preservar compatibilidade;
4. documentar alteração;
5. testar fluxo anterior.

Preservar:

```text
Flask
React
SQLite
scripts da raiz
LICENSE
NOTICE
créditos DeldMi
```

---

# 35. Git e segredos

O histórico remoto foi limpo em:

```text
2026-09-15
```

Se um segredo for publicado novamente:

1. revogar/trocar o segredo;
2. remover o arquivo do controle de versão;
3. limpar o histórico quando necessário.

Comandos de referência:

```bash
git ls-files -ci --exclude-standard
git rm --cached -- caminho/do/arquivo
```

Nunca adicionar ao Git:

```text
.env
*.sqlite
*.db
logs/
output/
dist/
node_modules/
.venv/
cache/
```

---

# 36. Versionamento e fluxo de desenvolvimento

Toda atualização funcional deve seguir o fluxo:

```text
VERSÃO ATUAL
     ↓
DESENVOLVIMENTO
     ↓
BRANCH/AMBIENTE DE TESTE
     ↓
VALIDAÇÃO
     ↓
AUDITORIA
     ↓
BREVE RESUMO DA VERSÃO
     ↓
MERGE/RELEASE
     ↓
VERSÃO ESTÁVEL
```

A branch principal deve permanecer funcional.

Durante a evolução do projeto, deve-se priorizar uma branch/ambiente separado para testes.

A raiz/projeto principal deve representar a versão atual funcional após validação.

## 36.1 Breve resumo obrigatório

Após cada atualização relevante, registrar:

```text
Versão:
Data:
Alterações:
Correções:
Novas funcionalidades:
Testes realizados:
Resultado:
Pendências:
```

---

# 37. Testes

## 37.1 Comandos oficiais

```bash
npm run test
npm run typecheck
npm run build
npm run verify
```

## 37.2 `npm run test`

Executar testes Python usando o `.venv`.

Nunca utilizar o Python global quando o ambiente virtual estiver disponível.

## 37.3 `npm run typecheck`

Validar:

* TypeScript;
* Vite;
* contratos;
* imports;
* componentes.

## 37.4 `npm run build`

Validar o build completo do frontend.

## 37.5 `npm run verify`

Deve validar:

1. sintaxe Python;
2. testes;
3. TypeScript;
4. build React;
5. arquivos obrigatórios;
6. estrutura essencial.

---

# 38. Testes obrigatórios de segurança

Criar testes para:

* usuário autorizado;
* usuário não autorizado;
* `viewer`;
* `editor`;
* `admin`;
* `403`;
* acesso direto à API;
* acesso direto sem frontend;
* `/api/me`;
* segredos;
* upload;
* path traversal;
* manutenção;
* exclusão;
* canais OFFLINE;
* configuração pública.

O caso crítico deve possuir teste explícito:

```text
viewer
↓
requisição administrativa
↓
403
↓
nenhuma alteração executada
```

---

# 39. Testes de regressão

Devem existir testes para:

* parser M3U;
* atributos IPTV;
* aspas simples;
* aspas duplas;
* RBAC;
* configuração pública;
* segurança;
* preservação de canais OFFLINE;
* geração de playlist;
* XMLTV;
* publicação;
* rotas `/assets`;
* rotas `/app-assets`;
* navegação SPA;
* setup;
* `.venv`;
* Windows;
* Docker.

---

# 40. Correções críticas já registradas

As seguintes correções fazem parte do contrato atual do projeto:

* preservação de canais OFFLINE;
* RBAC granular por recurso/ação;
* proteção de segredos;
* TLS seguro por padrão;
* senha administrativa inicial aleatória;
* compatibilidade `/assets` e `/app-assets`;
* parser M3U com metadados IPTV;
* tratamento estruturado de erros HTTP no frontend;
* pipeline de publicação preservando saída anterior;
* domínio semântico de manutenção;
* verificação cross-platform;
* testes de regressão;
* canais OFFLINE não são removidos durante sincronização;
* remoção persistida exige ação explícita;
* rotas críticas usam autorização granular;
* API de configuração não retorna credenciais;
* chaves desconhecidas são rejeitadas;
* auditoria não registra ambiente inteiro;
* Flask aceita prefixes antigos;
* parser aceita aspas simples e duplas;
* TLS exige `ALLOW_INSECURE_TLS=1` para certificados inválidos;
* bancos novos não dependem de `admin123`;
* `ADMIN_INITIAL_PASSWORD` é segredo;
* cliente HTTP diferencia rede/HTTP/JSON;
* setup não depende de caminhos absolutos;
* `.venv` inválido é recriado;
* `npm ci` somente quando existe lockfile;
* `npm install` quando não existe lockfile;
* `main is not defined` corrigido;
* recursão de `installFrontendDeps()` removida;
* `/usr/bin/python.exe` removido;
* `ModuleNotFoundError: dotenv` tratado usando `.venv`;
* `spawnSync npm.cmd EINVAL` tratado;
* `run-dev.js` valida o ambiente;
* `run-prod.js` encerra processos de forma controlada;
* erro `send` em `ChannelsPage.tsx` corrigido;
* variável Sass `$text` corrigida;
* navegação `/settings/*` preservada;
* temas personalizados preservados;
* temas do sistema tratados como modelos;
* compatibilidade de build React preservada.

---

# 41. Prioridades atuais de implementação

Implementar nesta ordem:

## P0 — Crítico

1. Corrigir execução local Flask/Vite.
2. Corrigir `/assets` e `/app-assets`.
3. Corrigir navegação direta e reload.
4. Garantir instalação reproduzível.
5. Garantir integridade do banco.
6. Garantir preservação dos canais OFFLINE.
7. Implementar RBAC real no backend.
8. Garantir que `viewer` não consiga acessar operações indevidas.

## P1 — Segurança e administração

9. Tela completa de usuários.
10. Matriz Recurso × Ação.
11. Autorização em todas as APIs.
12. Auditoria.
13. Manutenção segura.
14. Diagnóstico.
15. Controle de sessão.

## P2 — Dados e processamento

16. Canais e Editor completo.
17. Playlists.
18. EPG.
19. Sincronização.
20. Health check.
21. Pipeline.
22. Histórico de operações.

## P3 — Experiência

23. Dashboard.
24. Header global de Internet.
25. Pipeline inferior.
26. Distribuição.
27. Atividade.
28. Tutoriais.
29. Temas.
30. Pesquisa global.
31. Filtros persistentes.
32. Operações em lote.

## P4 — Escala

33. Paginação.
34. Virtualização.
35. otimização de SQLite;
36. otimização de processamento;
37. prevenção de concorrência;
38. relatórios.

---

# 42. Critério de pronto

O projeto somente deve ser considerado pronto quando:

* instalação limpa funcionar;
* `npm run setup` funcionar;
* `npm run test` funcionar;
* `npm run typecheck` funcionar;
* `npm run build` funcionar;
* `npm run verify` funcionar;
* execução local funcionar;
* Vite funcionar;
* Flask funcionar;
* servidor público funcionar;
* Docker funcionar;
* navegação direta funcionar;
* reload funcionar;
* `/assets` funcionar;
* `/app-assets` funcionar;
* autenticação funcionar;
* RBAC funcionar;
* `viewer` estiver corretamente limitado;
* APIs rejeitarem operações não autorizadas;
* canais persistirem corretamente;
* OFFLINE não for apagado automaticamente;
* exclusão explícita funcionar;
* playlists funcionarem;
* EPG funcionar;
* XMLTV funcionar;
* health check funcionar;
* pipeline funcionar;
* manutenção funcionar;
* auditoria funcionar;
* segredos não forem expostos;
* temas funcionarem;
* funcionalidades existentes permanecerem disponíveis.

---

# 43. Regra final de desenvolvimento

Antes de modificar qualquer parte do projeto:

1. entender o comportamento atual;
2. identificar dependências;
3. localizar funcionalidades existentes;
4. verificar requisitos deste arquivo;
5. preservar compatibilidade;
6. implementar a alteração;
7. testar;
8. executar auditoria;
9. verificar regressões;
10. atualizar este `AGENTS.md` quando o comportamento ou arquitetura mudar.

## Regra absoluta

> **A funcionalidade vem antes da aparência. A segurança vem antes da conveniência. A integridade dos dados vem antes da refatoração.**

Uma funcionalidade existente somente pode ser retirada quando o titular do projeto solicitar explicitamente sua remoção.

Se a funcionalidade puder ser organizada, modularizada ou melhor apresentada sem perda de comportamento, essa deve ser a abordagem preferencial.

---

# 44. Estado operacional atual

Data de referência:

```text
2026-09-17
```

Estado conhecido:

* projeto possui backend Flask;
* frontend React/Vite;
* banco SQLite;
* suporte a Windows/Linux/macOS;
* Docker;
* navegação por configurações;
* temas;
* processamento M3U;
* playlists;
* EPG/XMLTV;
* health check;
* RBAC em evolução;
* manutenção em evolução;
* auditoria em evolução;
* instalação cross-platform em evolução.

Problemas locais conhecidos:

```text
localhost:5000
/assets/index-*.js
→ retornando HTML em vez de JavaScript
```

```text
localhost:5173
→ base /app-assets/ sendo aplicada indevidamente ao desenvolvimento
```

Esses problemas devem ser tratados como prioridade P0 antes de considerar o ambiente local funcional.

---

# 45. Resumo arquitetural

```text
                         ┌──────────────────────┐
                         │       FRONTEND       │
                         │ React + Vite + TS    │
                         └──────────┬───────────┘
                                    │
                              HTTP / API
                                    │
                         ┌──────────▼───────────┐
                         │        FLASK         │
                         │     API / Routes     │
                         └──────────┬───────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
      ┌───────▼───────┐    ┌────────▼────────┐   ┌──────▼───────┐
      │     AUTHZ     │    │     DOMAINS      │   │    CORE      │
      │ RBAC / Users  │    │ Channels / EPG   │   │ Scheduler    │
      │ / Audit       │    │ Sync / Playlist  │   │              │
      └───────┬───────┘    │ Health / Maint.  │   └──────────────┘
              │             └────────┬────────┘
              │                      │
              └──────────────┬───────┘
                             │
                    ┌────────▼────────┐
                    │     SQLite      │
                    │ Fonte de dados  │
                    └─────────────────┘

                         ┌─────────────────┐
                         │ Public Server   │
                         │ /playlist/...   │
                         │ /epg/...        │
                         └─────────────────┘
```

---

# 46. Princípio de evolução

O M3U Processor / M3U Architect deve evoluir de forma incremental.

Cada versão deve:

```text
preservar
    +
corrigir
    +
testar
    +
organizar
    +
documentar
    +
melhorar
```

Nunca:

```text
reescrever
→ perder funcionalidades
→ quebrar compatibilidade
→ corrigir depois
```

O objetivo é manter uma base estável, modular, segura e semanticamente organizada, capaz de crescer sem perder as funcionalidades já construídas.
