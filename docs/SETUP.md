# Love Backend – Complete setup and run (step-by-step)

Follow these steps if you have **not** run migrations or installed dependencies yet.

---

## Prerequisites

- **Python 3.10+** installed.
- **PostgreSQL** running (for the database).
- **Redis** running (for session store).
- (Optional) **AWS CLI** configured if you use Secrets Manager; otherwise set DB and Cognito in `.env` (see below).

---

## Step 1: Open the project and use a virtual environment

```bash
cd e:\mair\love-backend-python
```

Create and activate a virtual environment (recommended):

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

**macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

You should see `(.venv)` in your prompt.

---

## Step 2: Install dependencies from requirements.txt

```bash
pip install -r requirements.txt
```

This installs FastAPI, SQLAlchemy, Alembic, Pillow, opencv-python-headless, Redis client, boto3, etc. Wait for it to finish without errors.

---

## Step 3: Configure environment variables

Copy the example env file and edit it:

```bash
copy .env.example .env
```

Then edit `.env` and set at least:

- **Database** (so the app does not need AWS Secrets Manager for local dev):
  - `DB_HOST=localhost` (or your PostgreSQL host)
  - `DB_PORT=5432`
  - `DB_NAME=your_database_name`
  - `DB_USER=your_db_user`
  - `DB_PASS=your_db_password`

- **Redis** (if not using defaults):
  - `REDIS_HOST=localhost`
  - `REDIS_PORT=6379`

- **Cognito** (if you use auth): either leave unset to load from AWS Secrets Manager, or set:
  - `COGNITO_USER_POOL_ID=...`
  - `COGNITO_CLIENT_ID=...`
  - `COGNITO_CLIENT_SECRET=...` (if required)

- **Optional:**
  - `DEBUG=true` (enables auto-create of tables in dev and reload)
  - `UPLOAD_DIR=uploads` (default; where postcard files are stored)

Save the file.

---

## Step 4: Create the database (if it doesn’t exist)

In PostgreSQL, create a database if you haven’t already:

```sql
CREATE DATABASE your_database_name;
```

Use the same name as `DB_NAME` in `.env`.

---

## Step 5: Run Alembic migrations

From the project root:

```bash
alembic upgrade head
```

This creates or updates tables (e.g. `users`, `postcards`). You should see output like “Running upgrade … -> b2c3d4e5f6789, create postcards table” (or “already at head”).

To confirm in the DB:

```sql
\dt
```

You should see `users` and `postcards` (and possibly `alembic_version`).

---

## Step 6: Start the application

```bash
python main.py
```

Or with uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

You should see something like “Uvicorn running on http://0.0.0.0:8000”. The `uploads` directory will be created automatically when the first postcard is created.

---

## Step 7: Quick health check

Open in a browser or use curl:

```bash
curl http://localhost:8000/health
```

Expected: `{"status":"ok"}`.

API docs:

- Swagger UI: **http://localhost:8000/docs**
- ReDoc: **http://localhost:8000/redoc**

---

## Step 8: (Optional) Test postcards

1. **Login** (your auth endpoint) and get a Bearer token.
2. **List postcards** (empty at first):
   ```bash
   curl -s "http://localhost:8000/api/v1/postcards?page=1&limit=10" -H "Authorization: Bearer YOUR_TOKEN"
   ```
   Response shape: `{ "items": [], "page": 1, "limit": 10, "total": 0, "total_pages": 0 }`.
3. **Create a postcard** via `/api/v1/postcards` (multipart: `front_file`, `back_file`, `data` as in your API docs).

---

## Summary checklist

| Step | Command / action |
|------|-------------------|
| 1 | `cd` to project, create and activate venv |
| 2 | `pip install -r requirements.txt` |
| 3 | Copy `.env.example` to `.env`, set DB (and Redis/Cognito if needed) |
| 4 | Create PostgreSQL database if new |
| 5 | `alembic upgrade head` |
| 6 | `python main.py` or `uvicorn main:app --reload --port 8000` |
| 7 | Open `/health` and `/docs` to confirm |
| 8 | (Optional) Test postcards with token |

---

## Troubleshooting

- **“No module named app”** – Run commands from the project root (`e:\mair\love-backend-python`) and ensure the venv is activated.
- **Database connection failed** – Check `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASS` in `.env` and that PostgreSQL is running.
- **Redis connection failed** – Start Redis and check `REDIS_HOST` / `REDIS_PORT`.
- **Secrets Manager errors** – Set DB and Cognito variables in `.env` so the app doesn’t try to load secrets from AWS.
