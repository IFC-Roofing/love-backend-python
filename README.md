# Love Backend

Backend API for Love management system built with FastAPI.



## Project Structure

```
app/
├── core/           # Config, database, security, middleware
├── crud/           # Data access layer
├── model/          # SQLAlchemy models
├── router/         # API endpoints (versioned at /api/v1/)
├── schema/         # Pydantic schemas
├── service/        # Business logic
├── session/        # Session management
└── utils/          # Helpers (hashing, jwt)
```

## Quick Start

1. Clone and create virtual environment:
```bash
git clone <repo-url>
cd love-backend
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file (copy from `.env.example`):
```bash
copy .env.example .env  # Windows
# cp .env.example .env  # Linux/Mac
```

Then configure your environment variables:
```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ifc_roofing
DB_USER=postgres
DB_PASS=your-password

# Security
SECRET_KEY=your-secret-key-change-in-production

# Optional
# ALGORITHM=HS256
# ACCESS_TOKEN_EXPIRE_MINUTES=30
# DEBUG=false
# PROJECT_NAME=Love Backend
# CORS_ORIGINS=["http://localhost:3000"]
```

4. Run migrations (production) or set DEBUG=true for auto-create:
```bash
alembic upgrade head
```

5. Start the server:
```bash
python main.py
```

6. Open http://localhost:8000/docs for Swagger UI

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login and get JWT token
- `POST /api/v1/auth/logout` - Logout and invalidate session
- `GET /api/v1/users/me` - Get current user profile

### Health
- `GET /health` - API health check

## Development

### Adding New Features

1. **Models**: Define database tables in `app/model/`
2. **CRUD**: Add database operations in `app/crud/`
3. **Services**: Implement business logic in `app/service/`
4. **Schemas**: Define request/response models in `app/schema/`
5. **Routes**: Add API endpoints in `app/router/api/v1/`

### Database Migrations

Create a new migration:
```bash
alembic revision --autogenerate -m "description"
```

Apply migrations:
```bash
alembic upgrade head
```

## BMad-Method Setup (optional)

```bash
npx bmad-method install
```
Then select your project directory (e.g., `dev/love-backend`).

## Production Deployment

- Set `DEBUG=false` in `.env`
- Use proper PostgreSQL database
- Configure CORS origins for your frontend domain
- Use environment-specific secret keys
- Consider Redis for session storage at scale
- Set up proper logging and monitoring
