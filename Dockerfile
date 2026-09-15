FROM python:3.11-slim

# Evita geracao de arquivos .pyc e forca flush imediato de logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalacao de dependencias essenciais do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Exclusao de quebras de linha Windows dos scripts caso migrados via host
RUN chmod +x *.sh 2>/dev/null || true

EXPOSE 5000

CMD ["python", "-m", "src.app"]