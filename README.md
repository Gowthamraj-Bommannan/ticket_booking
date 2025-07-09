# Django Train Booking System

A modular, production-ready train booking system built with Django and Django REST Framework. This project supports robust user management, train and station administration, route planning, booking workflows, and secure authentication, with a focus on clean architecture, validation, and structured logging.

## Features
  - Role-based access control: admin, station master, and regular user.
  - Admin approval workflow for staff or station master accounts.
  - Enforce business rules: unique sequences, increasing distances, valid timings, and only active trains/stations.
  - Centralized exception handler for all API errors.
  - Standardized error codes and messages for all business and validation errors.

## Project Structure
```
sample/
  booking/
    accounts/      # User management, registration, login, roles
    trains/        # Train models, CRUD, soft delete, admin endpoints
    stations/      # Station models, CRUD, soft delete, admin endpoints
    routes/        # Route templates, train route management
    booking/       # Django project settings, URLs, middleware, logging
    utils/         # Middleware, constants, helpers
    exceptions/    # Custom exception classes and handlers
    manage.py      # Django management script
  env/             # Python virtual environment (not included in repo)
  logs/            # Rotating log files for all API activity
```

## Setup Instructions
1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd sample
   ```
2. **Create and activate a virtual environment**
   ```bash
   python -m venv env
   source env/bin/activate  # On Windows: env\Scripts\activate
   ```
3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
4. **Configure environment variables**
   - Copy `.env.example` to `.env` and set values for:
     - `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`
     - PostgreSQL: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`
5. **Apply migrations**
   ```bash
   python manage.py migrate
   ```
6. **Create a superuser**
   ```bash
   python manage.py createsuperuser
   ```
7. **Run the development server**
   ```bash
   python manage.py runserver
   ```

## Logging
- All API requests and responses are logged to `logs/logs.log` with rotation.
- Sensitive fields (tokens, secrets) are masked in logs.
- Each app (accounts, trains, stations, routes) uses its own logger for clarity.
- Middleware logs every request/response with user context.

## API Overview
- All endpoints use JWT authentication (`Authorization: Bearer <token>`)
- Admin-only endpoints for activating/deactivating trains and stations
- Custom exception responses with standardized error codes/messages
- See each app's `views.py` and `serializers.py` for endpoint and validation details

## Extending & Customizing
- Add new apps (e.g., notifications, reports) as needed
- Update `INSTALLED_APPS` and `urls.py` to register new modules
- Use the provided logging and exception patterns for consistency
