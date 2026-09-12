FROM python:3.11-slim

WORKDIR /app

# System deps for Pillow (zlib/libjpeg for image decode)
RUN apt-get update && apt-get install -y --no-install-recommends \
        zlib1g-dev libjpeg62-turbo-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

# Non-root for running in production
RUN useradd --create-home --uid 1000 probe
USER probe

ENTRYPOINT ["lumina-probe"]
CMD ["--config", "/app/config.yaml"]
