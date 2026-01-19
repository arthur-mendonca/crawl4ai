# Usa uma imagem base Python oficial e leve
FROM python:3.11-slim-bookworm

# Define variáveis de ambiente para evitar arquivos .pyc e logs presos
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    # Define onde os navegadores do Playwright serão instalados para serem acessíveis
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Define o diretório de trabalho
WORKDIR /app

# 1. Instala dependências do SO (como root)
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Instala as dependências Python (como root)
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# 3. Instala os navegadores do Playwright e dependências de SO (como root)
RUN playwright install --with-deps chromium

# 4. Criar o usuário e preparar as pastas
# Criamos a pasta de navegadores e a /app com as permissões para o appuser
RUN useradd -m appuser && \
    mkdir -p /ms-playwright && \
    chown -R appuser:appuser /app /ms-playwright

# 5. Copia o restante do seu código definindo o dono como appuser
COPY --chown=appuser:appuser . .

# Instala as dependências do projeto (definidas no pyproject.toml)
RUN pip install .

# Agora sim, mudamos para o usuário não-root para rodar a aplicação
USER appuser

# Expõe a porta (Coolify usará a variável PORT=8000)
EXPOSE 8000

# Comando para iniciar sua API
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
