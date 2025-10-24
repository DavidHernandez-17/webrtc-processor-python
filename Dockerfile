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

RUN MODEL_DIR="/app/app/models" && \
    MODEL_ZIP="${MODEL_DIR}/vosk-model-small-es-0.42.zip" && \
    MODEL_URL="https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip" && \
    mkdir -p ${MODEL_DIR} && \
    if [ ! -d "${MODEL_DIR}/vosk-model-small-es-0.42" ]; then \
        if [ ! -f "${MODEL_ZIP}" ]; then \
            echo "⬇️ Descargando modelo Vosk..." && \
            curl -L -o ${MODEL_ZIP} ${MODEL_URL}; \
        fi && \
        echo "🗜️ Descomprimiendo modelo Vosk..." && \
        unzip -q ${MODEL_ZIP} -d ${MODEL_DIR} && \
        rm ${MODEL_ZIP} && \
        echo "✅ Modelo Vosk listo."; \
    else \
        echo "✅ Modelo Vosk ya existe, no se descarga."; \
    fi && \
    chmod -R a+rx ${MODEL_DIR} && \
    echo "📂 Contenido final de /app/app/models:" && ls -la ${MODEL_DIR}

RUN VOSK_FINAL_DIR="/usr/local/lib/python3.11/site-packages/vosk_model" && \
    mkdir -p ${VOSK_FINAL_DIR} && \
    mv /app/app/models/vosk-model-small-es-0.42 ${VOSK_FINAL_DIR}/ && \
    echo "✅ Modelo movido a ${VOSK_FINAL_DIR}/vosk-model-small-es-0.42" && \
    chmod -R a+rX ${VOSK_FINAL_DIR}/vosk-model-small-es-0.42

CMD ["python", "-m", "app.main"]
