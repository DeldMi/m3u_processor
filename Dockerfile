FROM node:22-alpine AS frontend-build

WORKDIR /app/frontend/react
COPY frontend/react/package*.json ./
RUN npm ci
COPY frontend/react/ ./
RUN npm run build

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=frontend-build /app/frontend/react/dist ./frontend/react/dist

RUN chmod +x *.sh 2>/dev/null || true

EXPOSE 5000

CMD ["python", "-m", "src.app"]