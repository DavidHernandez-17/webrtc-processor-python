FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    unzip \
    libgl1 \
    libglib2.0-0 \
    libavdevice-dev \
    libavfilter-dev \
    libopus-dev \
    libvpx-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

COPY app ./app

RUN echo "📂 Contenido de /app/app/models antes de descomprimir:" && ls -la /app/app/models && \
    if [ -f /app/app/models/vosk-model-small-es-0.42.zip ]; then \
        echo "🗜️ Descomprimiendo modelo Vosk..." && \
        unzip /app/app/models/vosk-model-small-es-0.42.zip -d /app/app/models/ && \
        rm /app/app/models/vosk-model-small-es-0.42.zip; \
    else \
        echo "⚠️ No se encontró el archivo ZIP en /app/app/models"; \
    fi && \
    echo "📂 Contenido de /app/app/models después de descomprimir:" && ls -la /app/app/models

CMD ["python", "-m", "app.main"]
