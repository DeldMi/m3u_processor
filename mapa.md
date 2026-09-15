m3u_processor/
│
├── Dockerfile                  # Manifesto de compilação da imagem Docker
├── docker-compose.yml          # Orquestração de contêineres e montagem de volumes
├── .env                        # Persistência de configurações e URLs remotas
├── .env.example                # Modelo limpo para controle de versão
├── .gitignore                  # Regras de exclusão Git
├── requirements.txt            # Dependências Python
├── README.md                   # Manual técnico e operacional
│
├── setup_env.bat               # Instalação Windows
├── run_checker.bat             # Execução CLI Windows
├── run_menu.bat                # Painel Web Windows
│
├── setup_env.sh                # Instalação Linux/macOS
├── run_checker.sh              # Execução CLI Linux/macOS
├── run_menu.sh                 # Painel Web Linux/macOS
│
├── input/                      # Listas locais (.m3u, .m3u8, .txt)
├── output/                     # Listas e XMLs particionados (máx 400 canais)
├── logs/                       # Histórico de auditoria em JSON
│
└── src/
    ├── __init__.py
    ├── config.py               # Gerenciador do .env
    ├── parser.py               # Extrator de canais e metadados
    ├── checker.py              # Probing assíncrono com bypass de SSL/HTTPS
    ├── epg.py                  # Ingestão, descompressão (.gz) e fatiamento XMLTV
    ├── manager.py              # Deduplicação, expurgo e divisão em lotes
    └── app.py                  # Servidor Web, links estáticos e agendador