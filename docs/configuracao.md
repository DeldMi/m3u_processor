# Configuração do projeto

## Arquivo `.env`

O projeto usa o arquivo `.env` para guardar configurações principais. Se não existir, use o exemplo `exeplo.env` como base.

```bash
cp exeplo.env .env
```

### Configurações mais importantes

```env
MAX_CHANNELS_PER_FILE='400'
CONCURRENCY_LIMIT='50'
REQUEST_TIMEOUT='6'
USER_AGENT='VLC/3.0.18 LibVLC/3.0.18'
REMOTE_M3U_URLS=''
SCHEDULE_MODE='DISABLED'
SCHEDULE_INTERVAL_HOURS=12
SCHEDULE_CRON_TIME=03:00
WEB_HOST=127.0.0.1
WEB_PORT=5000
BASE_URL=http://127.0.0.1:5000
API_TOKEN=
SECRET_KEY=
```

## Explicação das variáveis

### `MAX_CHANNELS_PER_FILE`

Define o número máximo de canais por arquivo M3U/EPG gerado.

Exemplo:

```env
MAX_CHANNELS_PER_FILE='400'
```

### `CONCURRENCY_LIMIT`

Quantidade de requisições simultâneas para validar streams.

Exemplo:

```env
CONCURRENCY_LIMIT='50'
```

### `REQUEST_TIMEOUT`

Tempo limite em segundos de cada requisição de teste do canal.

### `USER_AGENT`

User-Agent usado ao consultar streams e fontes remotas.

### `REMOTE_M3U_URLS`

Lista de URLs remotas separadas por ponto e vírgula.

Exemplo:

```env
REMOTE_M3U_URLS='https://site1.com/lista.m3u;https://site2.com/lista.txt'
```

### `SCHEDULE_MODE`

Modos válidos:

- `DISABLED` — sem agendamento
- `INTERVAL` — executa em intervalos de horas
- `CRON` — executa em um horário fixo do dia

### `SCHEDULE_INTERVAL_HOURS`

Usado quando `SCHEDULE_MODE=INTERVAL`.

Exemplo:

```env
SCHEDULE_INTERVAL_HOURS=12
```

### `SCHEDULE_CRON_TIME`

Formato `HH:MM` usado no modo CRON.

Exemplo:

```env
SCHEDULE_CRON_TIME=03:00
```

### `WEB_HOST`

IP/host que o Flask vai escutar.

Exemplo:

```env
WEB_HOST=0.0.0.0
```

### `WEB_PORT`

Porta do servidor web.

Exemplo:

```env
WEB_PORT=5000
```

### `BASE_URL`

URL pública onde a aplicação será acessada.

Exemplo:

```env
BASE_URL=http://127.0.0.1:5000
```

Esse valor é importante porque os links gerados nos M3U e XMLTV apontam para esse endereço.

### `API_TOKEN`

Token usado em autenticação por Bearer para API.

Exemplo:

```env
API_TOKEN='minha-chave-secreta'
```

### `SECRET_KEY`

Chave secreta da sessão Flask.

Se vazio, a aplicação usa um valor padrão, mas em produção o ideal é definir uma chave forte.

## Como alterar configuração pela interface

No painel web, vá em:

- `Configurações`
- alterar campos
- salvar

As alterações são gravadas no arquivo `.env` e aplicadas automaticamente ao sistema.

## Como configurar fontes de origem

### Opção 1: manual via `input/`

Coloque arquivos `.m3u`, `.m3u8` ou `.txt` na pasta:

```text
input/
```

### Opção 2: URLs remotas

No `.env`:

```env
REMOTE_M3U_URLS='https://site.com/canais.m3u;https://outro.com/iptv.txt'
```

## Como configurar o agendamento

### Modo `INTERVAL`

```env
SCHEDULE_MODE='INTERVAL'
SCHEDULE_INTERVAL_HOURS=6
```

### Modo `CRON`

```env
SCHEDULE_MODE='CRON'
SCHEDULE_CRON_TIME='03:00'
```

### Desativado

```env
SCHEDULE_MODE='DISABLED'
```

## Como configurar URLs públicas de playlists

O sistema gera links como:

```text
http://127.0.0.1:5000/playlist/playlist_parte_01.m3u
http://127.0.0.1:5000/epg/epg_parte_01.xml
```

Se a aplicação estiver atrás de um proxy, use a URL pública correta em `BASE_URL`.

## Como configurar acesso externo

Para permitir acesso em rede local ou em container:

```env
WEB_HOST=0.0.0.0
WEB_PORT=5000
BASE_URL=http://SEU_IP:5000
```

## Como usar a API

Exemplo com token:

```bash
curl -H "Authorization: Bearer MINHA_CHAVE" \
  http://127.0.0.1:5000/api/status
```

## Importante

- o arquivo `.env` deve ser mantido privado
- valores em `BASE_URL` sempre devem refletir a URL pública exata
- se `REMOTE_M3U_URLS` tiver URLs inválidas, o sistema ignora as que não forem HTTP/HTTPS válidas

---

Documentação relacionada:

- [instalacao.md](instalacao.md)
- [troubleshooting.md](troubleshooting.md)
- [acesso-e-recuperacao.md](acesso-e-recuperacao.md)
