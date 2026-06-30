# CivicConnect AI Authentication

Production-shaped authentication scaffold for CivicConnect AI using Vite, React, TypeScript, Tailwind CSS, Shadcn-style UI primitives, FastAPI, and PostgreSQL.

## Structure

- `frontend/` - Vite React auth UI, route guards, role-aware dashboard
- `backend/` - FastAPI auth API, PostgreSQL models, bcrypt hashing, JWT cookies
- `docker-compose.yml` - local PostgreSQL service

## Run Locally

1. Start PostgreSQL:

```bash
docker compose up -d postgres
```

2. Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

3. Frontend:

```bash
cd frontend
npm install
copy .env.example .env.local
npm run dev
```

Open `http://localhost:3000/login`.

## API

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/forgot-password`
- `POST /auth/logout`
- `GET /auth/me`

JWT access tokens are issued as HTTP-only cookies. `Remember me` extends the cookie lifetime.
