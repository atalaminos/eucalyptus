FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar rclone y dependencias del sistema
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl unzip \
    && curl https://rclone.org/install.sh | bash \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY app/ /app/
ENV PYTHONPATH="/app"

CMD ["python", "main.py"]
