# Processador, Auditor e Sincronizador M3U & EPG

## Recursos Principais
1. **Deduplicação Contínua**: Remove canais duplicados cruzando listas locais (`input/`), saídas existentes (`output/`) e links remotos.
2. **Expurgo de Canais Offline**: Na revalidação, qualquer canal fora do ar é completamente descartado.
3. **Chunking Rigoroso**: Listas particionadas em no máximo 400 canais por arquivo.
4. **Bypass SSL/HTTPS**: Configuração avançada de socket TLS que contorna falhas comuns de certificados em servidores de streaming.
5. **Integração XMLTV (EPG)**: Sincroniza com fontes do `iptv-epg.org`, descompacta arquivos `.gz` e divide a programação em arquivos `.xml` correspondentes a cada lista M3U.
6. **Servidor Integrado de Links**: Gera URLs estáticas como `http://ip:5000/playlist/playlist_parte_01.m3u` e `http://ip:5000/epg/epg_parte_01.xml`.

## Como Executar

### Opção 1: Via Docker (Recomendado para servidores)
```bash
docker compose up -d --build


Acesse no navegador: http://localhost:5000
Opção 2: Local no Windows

    Execute ```setup_env.bat``` (uma vez).

    Execute ```run_menu.bat``` (abre o painel e agendador).

Opção 3: Local no Linux

```bash
chmod +x *.sh
./setup_env.sh
./run_menu.sh
```

---

```<FollowUp label="Quer suporte a múltiplos arquivos EPG simultâneos por país ou categoria?" query="Como configurar a mesclagem automática de múltiplos guias EPG de países diferentes do iptv-epg.org em cada partição de 400 canais?"/>```