<<<<<<< HEAD
# Pinned base image (no floating "latest")
FROM python:3.12.4-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv

# 1. Dependencies first: this layer is only rebuilt when requirements.txt changes
COPY requirements.txt .
RUN pip install -r requirements.txt

# 2. Source after dependencies
COPY app ./app

# 3. Never run as root
RUN useradd --system --uid 10001 --no-create-home appuser
=======
﻿FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd --create-home --uid 10001 appuser

COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser migrations ./migrations

>>>>>>> e681e63c765d767c6e47d1063ad2759d9b708cd3
USER appuser

EXPOSE 8080

<<<<<<< HEAD
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2).status==200 else 1)"

=======
>>>>>>> e681e63c765d767c6e47d1063ad2759d9b708cd3
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
