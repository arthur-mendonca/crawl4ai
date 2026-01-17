# Usa uma imagem base Python oficial e leve
FROM python:3.11-slim-bookworm

# Define variáveis de ambiente para evitar arquivos .pyc e logs presos
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Define o diretório de trabalho
WORKDIR /app

# 1. Instala dependências do SO necessárias para o Playwright e compilação
# (Baseado no oficial, mas removendo coisas de GPU/Redis desnecessárias)
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Copia o arquivo de requisitos que você já tem
COPY requirements.txt .

# 3. Instala as dependências Python (Crawl4AI, FastAPI, Uvicorn, etc.)
# O seu requirements.txt já tem tudo o que precisamos
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# 4. Instala os navegadores do Playwright e suas dependências de SO
# O comando "playwright install-deps" é crucial no Linux
RUN playwright install --with-deps chromium

# 5. Copia o restante do seu código (incluindo o main.py)
COPY . .

# Expõe a porta que definimos no main.py
EXPOSE 8000

# Comando para iniciar sua API
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
