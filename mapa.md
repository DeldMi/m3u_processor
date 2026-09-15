m3u\_processor/

│

├── .env                    # Variáveis de ambiente e parâmetros de persistência

├── requirements.txt        # Dependências do ecossistema Python

├── setup\_env.bat           # Script de instalação e configuração da .venv

├── run\_checker.bat         # Execução direta via terminal (CLI)

├── run\_menu.bat            # Execução do painel web e agendador

├── README.md               # Documentação técnica completa

│

├── input/                  # Arquivos locais (.m3u, .m3u8, .txt)

├── output/                 # Listas saneadas (limite estrito de 400 canais)

├── logs/                   # Histórico de auditoria em JSON

│

└── src/

&#x20;   ├── \_\_init\_\_.py

&#x20;   ├── config.py           # Leitura e persistência dinâmica do arquivo .env

&#x20;   ├── parser.py           # Análise sintática (\*parsing\*) de listas locais e remotas

&#x20;   ├── checker.py          # Probing assíncrono (\*stream probing\* / sondagem de fluxo)

&#x20;   ├── manager.py          # Coleta, deduplicação, validação e particionamento

&#x20;   └── app.py              # API Flask e interface gráfica web integrada

