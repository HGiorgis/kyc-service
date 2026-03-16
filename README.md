# kyc_hybrid_service

A Django project created with automated setup tool.

## Project Structure

- `config/` - Main project configuration
- `apps/` - Django applications
  - `api/` - api app
  - `core/` - core app
  - `dashboard/` - dashboard app
  - `authentication/` - authentication app
  - `verification/` - verification app

## Setup Instructions

1. **Create virtual environment**
   ```bash
   python -m venv venv
   ```

2. **Activate virtual environment**
   - Windows:
     ```bash
     venv\Scripts\activate
     ```
   - Linux/Mac:
     ```bash
     source venv/bin/activate
     ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run migrations**
   ```bash
   python manage.py migrate
   ```

5. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run development server**
   ```bash
   python manage.py runserver
   ```

## Environment Variables

Create a `.env` file in the root directory with:

```
DEBUG=True
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///db.sqlite3
```

## Features

- Django 4.2.0
- Django REST Framework
- Multiple apps structure
- Environment variables support
- Docker support (if selected)
