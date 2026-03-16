# KYC Hybrid Service - Docker (Linux)
# dlib is built from source on Linux via pip (face-recognition dependency).
# ./dlib (Windows wheels) is excluded from the image; not used on Linux.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV TESSERACT_CMD=/usr/bin/tesseract

# Linux: Tesseract, PDF, and dlib/face_recognition build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    libopenblas-dev \
    liblapack-dev \
    libx11-dev \
    libgtk-3-dev \
    libboost-all-dev \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# setuptools + wheel for dlib build; use system cmake (apt) not pip cmake
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir "setuptools==70.2.0" wheel

# Limit parallel build jobs so dlib compile stays under ~2GB RAM (avoids 8GB+ OOM)
ENV CMAKE_BUILD_PARALLEL_LEVEL=1
ENV MAKEFLAGS=-j1

COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

COPY . .

RUN python manage.py collectstatic --noinput

EXPOSE 8000
# --timeout 120: KYC/face recognition can take >30s; avoid WORKER TIMEOUT
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120"]
