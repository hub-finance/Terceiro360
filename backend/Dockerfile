# Imagem do backend TERCEIRO360.
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# libpq é exigida pelo psycopg; o resto vem das rodas. A Liberation Serif é
# usada na exportação em PDF — sem uma fonte Unicode, o gerador cai no latin-1
# e troca travessão e aspas curvas por equivalentes ASCII.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      libpq5 curl fonts-liberation \
 && rm -rf /var/lib/apt/lists/*

# O projeto inteiro vem antes da instalação: instalar um pacote cujo código
# ainda não foi copiado depende de detalhes da descoberta do setuptools, e
# quebra de formas difíceis de diagnosticar dentro da imagem.
COPY . .
RUN pip install --upgrade pip && pip install --no-cache-dir .

# Roda como usuário sem privilégio: um processo web não precisa ser root.
RUN useradd --create-home --uid 10001 terceiro360 \
 && mkdir -p /app/storage && chown -R terceiro360 /app
USER terceiro360

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS "http://localhost:${PORT:-8000}/saude" || exit 1

CMD ["./iniciar.sh"]
