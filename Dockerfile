FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1


ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
        pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu \
            torch torchvision torchaudio && \
        pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000


ENV FLASK_ENV=production \
    VIDEO_SOURCE=0


CMD ["python", "flask_app.py"]
