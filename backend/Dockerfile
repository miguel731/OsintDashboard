FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl wget unzip ca-certificates git findutils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Requisitos Python
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Instalar binarios OSINT (Subfinder) + TheHarvester via git
ARG SUBFINDER_VERSION=2.6.5
ARG THEHARVESTER_VERSION=4.8.2
RUN set -eux; \
    arch="$(uname -m)"; \
    if [ "$arch" = "x86_64" ]; then ARCH=amd64; elif [ "$arch" = "aarch64" ]; then ARCH=arm64; else ARCH=amd64; fi; \
    SUB_TAR="https://github.com/projectdiscovery/subfinder/releases/download/v${SUBFINDER_VERSION}/subfinder_${SUBFINDER_VERSION}_linux_${ARCH}.tar.gz"; \
    SUB_ZIP="https://github.com/projectdiscovery/subfinder/releases/download/v${SUBFINDER_VERSION}/subfinder_${SUBFINDER_VERSION}_linux_${ARCH}.zip"; \
    if curl -fsSL -o /tmp/subfinder.tgz "$SUB_TAR"; then \
      tar -xzf /tmp/subfinder.tgz -C /tmp; \
    else \
      curl -fsSL -o /tmp/subfinder.zip "$SUB_ZIP"; \
      unzip -qo /tmp/subfinder.zip -d /tmp; \
    fi; \
    SUB_BIN="$(find /tmp -maxdepth 3 -type f -name subfinder | head -n1)"; \
    test -n "$SUB_BIN"; install "$SUB_BIN" /usr/local/bin/subfinder; \
    rm -rf /tmp/subfinder*; \
    # TheHarvester (instalar desde GitHub, versión estable)
    pip install --no-cache-dir git+https://github.com/laramies/theHarvester.git@${THEHARVESTER_VERSION}

# Usuario no root
RUN useradd -m appuser
RUN chown -R appuser:appuser /app
USER appuser

# Código
COPY app /app/app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]