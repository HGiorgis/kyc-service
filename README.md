# KYC Hybrid Service

Django app for KYC (Know Your Customer) with face recognition, document verification, Tesseract OCR, and REST API. Static and media files are served in production via WhiteNoise and Django.

## Prerequisites

- **Python 3.11** (or 3.10–3.12)
- **Windows (local):** Pre-built dlib wheels in the `dlib/` folder (e.g. from [Dlib_Windows_Python3.x](https://github.com/z-mahmud22/Dlib_Windows_Python3.x)) if you use `face-recognition`
- **Linux/macOS (local):** CMake and build tools for building dlib from source, or use Docker
- **Docker (optional):** Docker and Docker Compose for running the full stack in Linux containers

---

## Local setup

All commands below assume you are in the project root (`kyc_hybrid_service/`).

### 1. Virtual environment

```bash
python -m venv venv
```

**Activate:**

- **Windows (PowerShell / CMD):**
  ```bash
  venv\Scripts\activate
  ```
- **Linux / macOS:**
  ```bash
  source venv/bin/activate
  ```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

- **Windows:** If `dlib` / `face-recognition` fail to install, install a matching wheel from the `dlib/` folder first, then install the rest:
  ```bash
  pip install dlib/*.whl
  pip install -r requirements.txt
  ```
- **Linux / macOS:** System CMake and build-essential may be required; `pip install -r requirements.txt` will build dlib from source.

### 3. Environment variables

Create a `.env` file in the project root (optional; defaults work for local dev):

```env
DEBUG=True
SECRET_KEY=your-secret-key-change-in-production
# Optional: SQLite is default
# DATABASE_URL=sqlite:///db.sqlite3
```

For production, set `DEBUG=False` and a strong `SECRET_KEY`.

### 4. Database and superuser

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 5. Run the development server

```bash
python manage.py runserver
```

Open **http://127.0.0.1:8000/** (landing). Log in at **http://127.0.0.1:8000/auth/login/**.

---

## Docker setup

Uses Linux containers: Tesseract, dlib, and face-recognition are built inside the image. The `dlib/` folder (Windows wheels) is ignored in Docker.

### Build and run

```bash
docker compose up -d --build
```

- App: **http://localhost:8000**
- The compose command runs `migrate` then `gunicorn`; static files are collected at build time and served with WhiteNoise; media is served by Django.

### Optional: Postgres

Edit `docker-compose.yml`: uncomment the `db` service and the `depends_on` / `DATABASE_URL` under `web`, then:

```bash
docker compose up -d --build
```

### Volumes

- `.:/app` – app code (for local dev; remove or replace in production images if you prefer a copy)
- `media_volume:/app/media` – uploaded media
- `static_volume:/app/staticfiles` – collected static files

---

## Deploy to Render (free tier)

1. **New Web Service** → connect your repo and select this project (e.g. root or `kyc_hybrid_service` if monorepo).

2. **Build command:**
   ```bash
   pip install -r requirements-docker.txt
   python manage.py collectstatic --noinput
   ```
   If your repo root is the Django project, run these from that root. If the app lives in a subfolder (e.g. `kyc_hybrid_service`), use:
   ```bash
   cd kyc_hybrid_service && pip install -r requirements-docker.txt && python manage.py collectstatic --noinput
   ```

3. **Start command:**
   ```bash
   python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
   ```
   Again, add `cd kyc_hybrid_service &&` if the Django app is in a subfolder.

4. **Environment variables** (Render dashboard):
   - `SECRET_KEY` – strong random key
   - `DEBUG` – `False`
   - `ALLOWED_HOSTS` – your Render host, e.g. `your-service.onrender.com`
   - `DATABASE_URL` – if you add a Render Postgres instance, set this and use `dj-database-url` in settings if needed.

5. **Static and media:** WhiteNoise serves static files from `STATIC_ROOT` after `collectstatic`. Media is served by Django from `MEDIA_ROOT`. On Render’s free tier the filesystem is ephemeral, so uploaded files in `media/` are lost on redeploy; for persistent uploads use external storage (e.g. S3).

---

## Project structure

```
kyc_hybrid_service/
├── config/           # Django settings, URLs, WSGI
├── apps/
│   ├── users/        # User model, landing, dashboard, admin
│   ├── authentication/
│   ├── verification/
│   ├── core/         # Core services (e.g. verifier)
│   └── api/          # REST API (API key auth)
├── templates/
├── static/           # CSS, JS, images (e.g. logos) – collected to staticfiles
├── media/            # User uploads (created at runtime)
├── requirements.txt
├── requirements-docker.txt
├── Dockerfile
├── docker-compose.yml
└── manage.py
```

---

## Features

- Django 4.2+
- User auth, dashboard, and admin
- Face recognition and document verification (dlib, face-recognition, Tesseract, OpenCV)
- REST API with API key authentication
- Static files served via WhiteNoise in production; media served by Django
- Docker and Docker Compose support (Linux; dlib built in image)
- Ready for Render with `requirements-docker.txt` and `collectstatic` + gunicorn
