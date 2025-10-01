# Python env
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows

pip install -r requirements.txt
python -m app.main


# Docker
-- Levantar contenedor
docker compose up --build

-- Reconstruir
docker compose build webrtc-processor