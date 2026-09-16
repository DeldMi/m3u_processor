# M3U Architect / Processador IPTV

Sistema para processar listas M3U/IPTV, validar canais em tempo real, classificar metadados, gerar playlists M3U e EPG XMLTV, e publicar links públicos para distribuição.

**Autor e titular do projeto:** DeldMi

Este projeto é gratuito e possui licença própria de uso livre com atribuição.
Consulte [LICENSE](LICENSE), [NOTICE](NOTICE) e [docs/direitos-e-doacoes.md](docs/direitos-e-doacoes.md)
antes de redistribuir ou criar um produto derivado. Doações são voluntárias e
ajudam a manter a infraestrutura e as atualizações.

## O que é este projeto

Este projeto combina:

- Flask para backend e APIs
- SQLite para dados
- React + Vite + Tailwind + SCSS para interface web
- processamento de listas M3U e XMLTV
- validação de canais online/offline
- geração de arquivos em blocos
- autenticação por usuário e roles
- agendamento automático via APScheduler

## Estrutura do projeto

- `src/` — backend e lógica principal
- `frontend/react/` — frontend React
- `input/` — listas de canais locais
- `output/` — playlists e XMLTV gerados
- `logs/` — relatórios de auditoria JSON
- `data/` — banco SQLite
- `docs/` — documentação detalhada
- `Dockerfile` — imagem para Docker
- `docker-compose.yml` — ambiente de execução em container

## Como funciona

O fluxo geral é:

1. lê canais de arquivos locais e URLs remotas
2. deduplica entradas
3. valida disponibilidade dos canais
4. persiste dados no banco SQLite
5. classifica cada canal por país, cidade, categoria e grupo
6. gera M3U e EPG em partições
7. publica os links na web com `BASE_URL`
8. disponibiliza operação via painel web e APIs

## Acesso inicial

Credenciais padrão:

- usuário: `admin`
- senha: `admin123`

## Instalação rápida

### Linux

```bash
chmod +x *.sh
./setup_env.sh
./run_menu.sh
```

### Windows

```bat
setup_env.bat
run_menu.bat
```

### Docker

```bash
docker compose up -d --build
```

## Como acessar

```text
Menu: http://127.0.0.1:5000
Links M3U/EPG: http://127.0.0.1:8080
```

## Configuração principal

O projeto usa `.env` e inclui o exemplo `exeplo.env`.

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
- `REMOTE_M3U_URLS`
- `SCHEDULE_MODE`
- `API_TOKEN`
- `SECRET_KEY`

## Login, usuários e recuperação

Mais detalhes em:

- [docs/acesso-e-recuperacao.md](docs/acesso-e-recuperacao.md)
- [docs/direitos-e-doacoes.md](docs/direitos-e-doacoes.md)

## Documentação detalhada

- [docs/arquitetura.md](docs/arquitetura.md)
- [docs/instalacao.md](docs/instalacao.md)
- [docs/configuracao.md](docs/configuracao.md)
- [docs/troubleshooting.md](docs/troubleshooting.md)
- [docs/acesso-e-recuperacao.md](docs/acesso-e-recuperacao.md)

## Como rodar em produção

- configure `BASE_URL` correto
- configure `WEB_HOST=0.0.0.0`
- use HTTPS em reverse proxy
- proteja `.env` e o banco SQLite
- mantenha o sistema atualizado com backup regular

## Possíveis erros e solução

Para problemas comuns, consulte:

- [docs/troubleshooting.md](docs/troubleshooting.md)

## Observações importantes

- O build do frontend precisa existir em `frontend/react/dist`
- a aplicação usa o `SQLite` em `data/app.db`
- o menu usa `BASE_URL` e `WEB_PORT`
- os links exportados usam `PUBLIC_BASE_URL` e `PUBLIC_PORT`
- o `admin` padrão deve ser trocado imediatamente em ambientes reais

## Exemplos de uso da API

### Status do sistema

```bash
curl http://127.0.0.1:5000/api/status
```

### Iniciar sincronização

```bash
curl -X POST http://127.0.0.1:5000/api/v1/sync
```

### Consultar playlists

```bash
curl http://127.0.0.1:5000/api/v1/playlists
```

## Resumo

Este projeto foi pensado para operar como um processador IPTV completo: ingestão, validação, classificação, geração de listas, publicação e gestão de usuários e configurações.

Se quiser, o próximo passo pode ser criar também um guia de uso específico para:

- usuário admin
- usuário editor
- usuário viewer
- operação em Docker em produção
- backup e restauração do banco SQLite
- migração para Linux server/VM
- configuração de domínio e HTTPS

## Verificação automática

Depois de instalar o ambiente, use:

```bash
npm run verify
```

O comando valida Python, testes do backend, TypeScript/Vite e a estrutura mínima do projeto.
