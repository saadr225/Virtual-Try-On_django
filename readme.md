# Virtual Try-On Django

A scalable backend service that lets users upload a person image and a garment image and receive a photorealistic try-on result powered by **Google Vertex AI**. The platform exposes two REST APIs — a public **Client API** for e-commerce integrations and a private **Internal API** for user and key management — with a full request-based approval workflow, per-key rate limiting, and audit trails.

---

## Table of Contents

- [Features](#features)
- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Local Setup](#local-setup)
  - [Docker Setup](#docker-setup)
- [Environment Variables](#environment-variables)
- [API Overview](#api-overview)
  - [Client API](#client-api)
  - [Internal API](#internal-api)
- [User & Access Flow](#user--access-flow)
- [Role System](#role-system)
- [Rate Limiting](#rate-limiting)
- [Running Tests](#running-tests)
- [Project Structure](#project-structure)

---

## Features

- **AI-powered try-on** via Google Vertex AI (`virtual-try-on-preview-08-04`)
- **Two separate API surfaces** — public Client API (API-key authenticated) and internal management API (JWT authenticated)
- **Request-based API key approval** — users apply for access; staff/admin approves with custom quotas
- **Fine-grained rate limiting** — per-minute, per-hour, per-day, and monthly quotas at both the key and user level
- **Domain & IP whitelisting** per API key
- **Full audit trail** — request history, approval/rejection records, payment proof uploads
- **Staff delegation** — admins can assign staff users to handle approval queues
- **Docker-ready** with Gunicorn + WhiteNoise for production

---

## Architecture Overview

```
Client / E-commerce Site
        │
        │  X-API-Key header
        ▼
┌─────────────────────┐
│    Client API        │  /api/v1/...   (rate-limited, domain/IP whitelisted)
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│   VTON Controller    │  Calls Google Vertex AI Virtual Try-On
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│    Internal API      │  /internal/api/...  (JWT, staff/admin only for mgmt)
│  - User management   │
│  - API key mgmt      │
│  - Quota & billing   │
└─────────────────────┘
         │
         ▼
  PostgreSQL Database
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web framework | Django 5.2, Django REST Framework 3.16 |
| Auth | JWT (`djangorestframework-simplejwt`) |
| AI / Try-on | Google GenAI SDK (`google-genai`), Vertex AI |
| Database | PostgreSQL (`psycopg2-binary`) |
| Server | Gunicorn (gthread worker) |
| Static files | WhiteNoise |
| Image processing | Pillow |
| Container | Docker |

---

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- A Google Cloud project with the **Vertex AI** Virtual Try-On API enabled
- A Google GenAI API key

### Local Setup

```bash
# 1. Clone the repo
git clone https://github.com/saadr225/Virtual-Try-On_django.git
cd Virtual-Try-On_django

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your database credentials and API keys

# 5. Apply migrations
cd VTON_APP
python manage.py migrate

# 6. Create a superuser
python manage.py createsuperuser

# 7. Run the development server
python manage.py runserver
```

The server starts at `http://localhost:8000`.

### Docker Setup

```bash
# Build the image
docker build -t vton-django .

# Run (pass env vars via --env-file)
docker run -p 8080:8080 --env-file .env vton-django
```

The container runs Gunicorn on port **8080** with 3 workers x 8 threads, optimised for I/O-bound Vertex AI calls.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the values:

| Variable | Description |
|---|---|
| `DEBUG` | `True` for development, `False` for production |
| `ALLOWED_HOSTS` | Comma-separated hostnames |
| `DB_HOST` / `DB_PORT` | PostgreSQL host and port |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` | Database credentials |
| `GOOGLE_GENAI_API_KEY` | Google GenAI API key for Vertex AI calls |
| `VERTEX_AI_API_KEY` | Vertex AI API key (if separate) |
| `HOST_URL` | Public base URL with trailing slash, used for media file URLs |
| `DEBUG_LOG_*` | Fine-grained debug logging flags (see `.env.example`) |

---

## API Overview

Full OpenAPI specs live in `docs/api/openapi/`.

### Client API

Authenticated with `X-API-Key: <key>` header. Intended for e-commerce platforms integrating the try-on feature.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/healthcheck/` | Service health check |
| `POST` | `/api/v1/tryon/` | Submit a try-on request (person + garment images) |
| `GET` | `/api/v1/tryon/{id}/` | Retrieve a try-on result |

**Image requirements**: JPG/JPEG/PNG, max 10 MB per file, multipart/form-data.

### Internal API

JWT-authenticated. Covers user registration, API key management, quota tracking, and staff approval workflows.

#### Authentication

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/internal/api/auth/register/` | Register a new user |
| `POST` | `/internal/api/auth/login/` | Obtain JWT tokens |
| `POST` | `/internal/api/auth/refresh/` | Refresh access token |

#### API Key Management (requires approval)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/internal/api/api-keys/create/` | Create an API key |
| `GET` | `/internal/api/api-keys/` | List own API keys |
| `DELETE` | `/internal/api/api-keys/{id}/` | Revoke an API key |
| `GET` | `/internal/api/quota/me/` | View own quota and usage |

#### Access Request Flow (users)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/internal/api/api-key-requests/submit/` | Submit an access request |
| `GET` | `/internal/api/api-key-requests/my-requests/` | View own requests |

#### Staff / Admin Management

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/internal/api/staff/api-key-requests/` | List all access requests |
| `POST` | `/internal/api/staff/api-key-requests/{id}/approve/` | Approve a request |
| `POST` | `/internal/api/staff/api-key-requests/{id}/reject/` | Reject a request |

---

## User & Access Flow

```
1. Register & log in
2. Submit an API key access request (business info, use case, expected usage)
3. Staff/admin reviews the request
4. On approval, quotas are set and the user can create API keys
5. Use API keys to call the Client API from your application
```

Access requests capture:

- Business name and email
- Use case description
- Expected monthly request volume
- Optional website and additional notes
- Payment proof (file upload, attached by staff on approval)

---

## Role System

| Role | Capabilities |
|---|---|
| **Superuser** | Full access; manage staff, users, keys, quotas |
| **Admin** (`user_type = "admin"`) | Approve/reject requests; manage users and keys |
| **Staff** (`is_staff = True`) | View and act on pending access requests; set quotas on approval |
| **Regular User** | Submit requests; manage own API keys after approval |

---

## Rate Limiting

Each API key carries independent limits (configurable by admin at approval time):

| Window | Default limit |
|---|---|
| Per minute | 100 requests |
| Per hour | 1,000 requests |
| Per day | 10,000 requests |
| Monthly quota | 500 requests |

A user-level monthly quota also caps usage across all of a user's keys (`USR022` error when exceeded). Rate limit headers are included on every response.

Keys can additionally be restricted to specific **domains** and/or **IP addresses**.

---

## Running Tests

```bash
cd tests/scripts/test_suite
pip install pytest
pytest
```

The test suite covers authentication, API key management, quota enforcement, admin/staff workflows, permissions, and general endpoint behaviour.

---

## Project Structure

```
Virtual-Try-On_django/
├── VTON_APP/
│   ├── api/
│   │   ├── client_api/          # Public try-on API
│   │   └── internal_api/        # User, key & approval management API
│   ├── app/
│   │   ├── Controllers/         # VTON & helper business logic
│   │   ├── models/              # Django ORM models
│   │   ├── utils/               # Middleware, logging utilities
│   │   └── views/
│   └── VTON_APP/                # Django project settings & routing
├── docs/
│   └── api/openapi/             # OpenAPI 3.0 specs (client & internal)
├── tests/
│   └── scripts/test_suite/      # pytest integration tests
├── .env.example                 # Environment variable template
├── Dockerfile                   # Production Docker image
├── entrypoint.sh                # Container startup (migrate + gunicorn)
└── requirements.txt
```

---

## License

MIT
