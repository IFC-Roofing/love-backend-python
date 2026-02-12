---
inclusion: fileMatch
fileMatchPattern: "app/aws/**,app/service/auth_service.py,app/router/api/v1/auth.py,app/session/**,app/core/dependencies.py,app/core/config.py,app/model/user.py"
---

# AWS Cognito + FastAPI Authentication Guide

This project uses AWS Cognito for authentication with a server-side session layer.
Read this guide fully before making any auth-related changes.

## Architecture Overview

```
Client → Router → AuthService → CognitoWrapper (boto3) → AWS Cognito
                                      ↓
                               Session Store (in-memory)
                                      ↓
                          validate_session dependency (protected routes)
```

## Key Design Decisions

1. **Option A (Trust Session)**: Token is verified ONCE at login via Cognito. After that, session store is the source of truth. No JWT/JWK verification on every request.
2. **Cognito handles ALL authentication** (signup, login, email verification, password reset). We do NOT create/verify JWTs locally.
3. **Local user table stores cognito_username** (UUID) for all Cognito operations. Cognito is created FIRST, then DB record.
4. **AWS layer is isolated** in `app/aws/`. It only contains AWS-specific code.
5. **Secrets Manager is the ONLY source** for all credentials (DB + Cognito). No credentials in .env.

## File Structure & Responsibilities

### AWS Layer (`app/aws/`)
- `client.py` - Centralized boto3 client factory. Use `get_aws_client(service_name)` for ANY AWS service.
- `secrets.py` - Secrets Manager wrapper. `get_secret(name, region)` returns parsed JSON dict.
- `cognito.py` - `CognitoIdentityProviderWrapper` class. All Cognito boto3 operations.
- `__init__.py` - Exports: `get_aws_client`, `CognitoIdentityProviderWrapper`, `get_secret`

### Config (`app/core/config.py`)
- Pydantic Settings loads AWS region config from `.env`
- ALL secrets loaded from Secrets Manager at startup:
  - `love-backend/db` → DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS
  - `love-backend/cognito` → COGNITO_USER_POOL_ID, COGNITO_CLIENT_ID, COGNITO_CLIENT_SECRET
- No database or Cognito credentials in .env — only AWS region and optional flags

### User Model (`app/model/user.py`)
- `id` - UUID primary key (DB-generated)
- `email` - Unique, indexed
- `cognito_username` - UUID from Cognito (unique, not null) - CRITICAL for all Cognito operations
- `is_active` - Boolean flag
- `created_at`, `updated_at` - Timestamps

### Session Layer (`app/session/`)
- In-memory dict: `{token: user_data}`
- `create_session(token, user_data)` - Store after login
- `get_session(token)` - Lookup only, NO verification
- `remove_session(token)` - Remove on logout
- `extract_token(auth_header)` - Parse "Bearer <token>"
- **Production**: Replace with Redis

### Auth Service (`app/service/auth_service.py`)
- Instantiates `CognitoIdentityProviderWrapper` in `__init__` using `get_aws_client('cognito-idp')` and settings
- `register_user()` - Cognito sign_up FIRST, then local DB create with cognito_username
- `login()` - Cognito admin_initiate_auth + create session with IdToken
- `logout()` - Cognito global_sign_out + remove session
- `verify_email()` - Confirm signup with code (uses cognito_username from DB)
- `resend_verification_code()` - Resend email verification code (uses cognito_username from DB)
- `forgot_password()` - Initiate password reset flow (uses cognito_username from DB)
- `reset_password()` - Complete password reset with code (uses cognito_username from DB)
- `change_password()` - Change password for logged-in user (uses access_token from session)

### Dependencies (`app/core/dependencies.py`)
- `validate_session` - FastAPI dependency for protected routes. Extracts token, checks session store, returns user_data dict.
- `get_current_token` - Gets token from request.state.session

### Middleware (`app/core/middleware.py`)
- `SessionMiddleware` - Initializes `request.state.session = {}` for every request

## Cognito User Pool Configuration

- **Pool uses email as ALIAS** (not username). Username is a UUID.
- **Sign-up**: Generate UUID as Username, pass email as UserAttribute
- **Login**: Use `ADMIN_USER_PASSWORD_AUTH` flow (not USER_PASSWORD_AUTH) because pool uses email alias + client secret
- **Client has a SECRET** - All API calls MUST include SECRET_HASH calculated via HMAC-SHA256
- **MFA**: OFF
- **Auto-verified attributes**: email
- **Password policy**: min 8 chars, uppercase, lowercase, numbers, symbols

## SECRET_HASH Calculation

Required for ALL Cognito API calls when client has a secret:

```python
def _secret_hash(self, username: str) -> str:
    message = bytes(username + self.client_id, 'utf-8')
    key = bytes(self.client_secret, 'utf-8')
    return base64.b64encode(
        hmac.new(key, message, digestmod=hashlib.sha256).digest()
    ).decode()
```

**CRITICAL**: Always use `cognito_username` (UUID) from the DB for SECRET_HASH calculation, NOT email.

## Auth Flows

### Signup Flow
1. Router receives email + password
2. AuthService checks local DB for existing email
3. **Cognito `sign_up()` FIRST** with UUID username + email attribute + SECRET_HASH
4. If Cognito succeeds, create local user record with `cognito_username` from Cognito response
5. User receives verification code via email
6. Return success message

### Email Verification Flow
1. User receives code via email after signup
2. Client calls `POST /verify-email` with `{email, code}`
3. AuthService looks up user by email, gets `cognito_username`
4. Cognito `confirm_sign_up()` with cognito_username + code + SECRET_HASH
5. User can now login

### Resend Verification Code Flow
1. Client calls `POST /resend-code` with `{email}`
2. AuthService looks up user by email, gets `cognito_username`
3. Cognito `resend_confirmation_code()` with cognito_username + SECRET_HASH
4. User receives new code via email

### Login Flow
1. Router receives email + password
2. AuthService calls Cognito `admin_initiate_auth()` with email + password + SECRET_HASH (uses email for login)
3. Cognito returns: IdToken, AccessToken, RefreshToken
4. Get local user from DB by email
5. Store IdToken as session key with user_data: `{user_id (DB UUID), email, is_active, access_token}`
6. Return IdToken to client as access_token

### Protected Route Flow
1. Client sends `Authorization: Bearer <IdToken>`
2. `validate_session` dependency extracts token
3. Looks up token in session store (NO crypto verification)
4. Returns user_data dict to route handler
5. Route uses `user_data["user_id"]` (DB UUID) for queries

### Logout Flow
1. `validate_session` confirms session exists
2. AuthService calls Cognito `global_sign_out()` with stored access_token
3. Remove token from session store
4. Return success

### Forgot Password Flow
1. Client calls `POST /forgot-password` with `{email}`
2. AuthService looks up user by email, gets `cognito_username`
3. Cognito `forgot_password()` with cognito_username + SECRET_HASH
4. User receives reset code via email
5. Client calls `POST /reset-password` with `{email, code, new_password}`
6. AuthService looks up user by email, gets `cognito_username`
7. Cognito `confirm_forgot_password()` with cognito_username + code + new_password + SECRET_HASH
8. Password reset complete

### Change Password Flow (Logged-in User)
1. Client calls `POST /change-password` with `{current_password, new_password}` (requires valid session)
2. AuthService gets `access_token` from session
3. Cognito `change_password()` with access_token + current_password + new_password
4. Password changed

## Session Data Structure

```python
# Stored in session: {id_token: user_data}
{
    "user_id": "db-uuid-string",      # Local DB user ID (NOT Cognito sub)
    "email": "user@example.com",
    "is_active": True,
    "access_token": "cognito-access-token"  # Stored for sign_out and change_password
}
```

## API Endpoints

### Public Endpoints
- `POST /signup` - Register new user (email, password)
- `POST /verify-email` - Confirm email with code (email, code)
- `POST /resend-code` - Resend verification code (email)
- `POST /login` - Authenticate user (email, password)
- `POST /forgot-password` - Initiate password reset (email)
- `POST /reset-password` - Complete password reset (email, code, new_password)

### Protected Endpoints (require valid session)
- `POST /logout` - Sign out user
- `POST /change-password` - Change password (current_password, new_password)
- `GET /me` - Get current user profile
- `GET /session` - Get session info

## Error Response Format

All auth errors use `AppException` subclasses:

```json
{
    "detail": {
        "code": "ERROR_CODE",
        "message": "Human-readable message",
        "hint": "Optional suggestion"
    }
}
```

Error codes: `EMAIL_EXISTS`, `INVALID_CREDENTIALS`, `NOT_AUTHENTICATED`, `SESSION_EXPIRED`, `NOT_FOUND`, `FORBIDDEN`

## How to Protect a Route

```python
from app.core.dependencies import validate_session

@router.get("/protected")
async def protected_route(
    current_user: Dict[str, Any] = Depends(validate_session)
):
    user_id = current_user["user_id"]  # DB UUID
    email = current_user["email"]
    access_token = current_user["access_token"]  # For Cognito operations
    return {"message": f"Hello {email}"}
```

## How to Add a New Cognito Operation

1. Add method to `CognitoIdentityProviderWrapper` in `app/aws/cognito.py`
2. Use `cognito_username` (UUID) as the username parameter, NOT email
3. Include SECRET_HASH if client has secret:
   ```python
   if self.client_secret:
       kwargs['SecretHash'] = self._secret_hash(username)  # username is cognito_username UUID
   ```
4. Add service method in `AuthService` that:
   - Looks up user by email in DB
   - Gets `cognito_username` from user record
   - Calls Cognito wrapper with `cognito_username`
5. Add route in `app/router/api/v1/auth.py`
6. Never call Cognito directly from routers

## How to Add a New AWS Service

```python
# In any service:
from app.aws import get_aws_client

s3_client = get_aws_client('s3')
ses_client = get_aws_client('ses')
```

Create a wrapper class in `app/aws/` following the same pattern as `cognito.py`.

## Common Pitfalls

1. **Never use `USER_PASSWORD_AUTH`** for login - use `ADMIN_USER_PASSWORD_AUTH` (email alias + client secret)
2. **Never use email as Username** in Cognito operations - use `cognito_username` (UUID) from DB
3. **Always include SECRET_HASH** in Cognito API calls
4. **SECRET_HASH must use cognito_username** (UUID), not email, except for login which uses email
5. **Cognito MUST succeed before DB insert** - if Cognito fails, don't create DB record
6. **Always store cognito_username** in DB during signup - it's required for all future Cognito operations
7. **Session is in-memory** - server restart clears all sessions
8. **Don't verify tokens on every request** - session store is trusted (Option A)
9. **All credentials come from Secrets Manager only** — DB and Cognito, not from .env
10. **For verify/resend/forgot/reset operations**: Look up user by email in DB, get `cognito_username`, pass to Cognito

## Database Schema

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR UNIQUE NOT NULL,
    cognito_username VARCHAR UNIQUE NOT NULL,  -- UUID from Cognito
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE UNIQUE INDEX idx_users_cognito_username ON users(cognito_username);
```
