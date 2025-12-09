# Iniciar
docker compose up -d
docker compose up --build
docker compose build --no-cache

# Ver en tiempo real
docker compose logs -f

# Detener
docker compose down