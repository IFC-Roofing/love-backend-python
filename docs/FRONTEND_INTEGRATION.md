# Frontend integration

How to connect your frontend (React, Next.js, etc.) to the Love Backend API.

---

## Base URL

- Local: `http://localhost:8000`
- Docker: `http://localhost:8000` (or the host/port you expose)
- Production: `https://your-api-domain.com`

All API routes are under **`/api/v1`**.

---

## Authentication

1. **Login** to get a token:
   - `POST /api/v1/auth/login`
   - Body (JSON): `{ "email": "user@example.com", "password": "..." }`
   - Response: `{ "message": "Login successful", "access_token": "<JWT>", "token_type": "bearer", "user": { "id", "email", "is_active", "profile_image_url" } }`

2. **Use the token** on protected requests:
   - Header: `Authorization: Bearer <access_token>`

3. **Signup** (if needed): `POST /api/v1/auth/signup` with `{ "email", "password" }`.

4. **Logout**: `POST /api/v1/auth/logout` with the same `Authorization: Bearer <token>` header.

---

## Contacts

- **List my contacts**  
  `GET /api/v1/contacts`  
  Headers: `Authorization: Bearer <token>`  
  Response: `[{ "id": "uuid", "user_id": "uuid", "email": "..." }, ...]`

- **Get one contact**  
  `GET /api/v1/contacts/{contact_id}`  
  Headers: `Authorization: Bearer <token>`

Use contact `id` when sending a postcard to that contact (optional `receiver_contact_id` in postcard data).

---

## Postcards

### Create postcard (upload front + back, optional data)

- **Request:** `POST /api/v1/postcards`
- **Headers:** `Authorization: Bearer <token>`
- **Body:** `multipart/form-data`
  - `front_file` (required): image or video file
  - `back_file` (required): image or video file
  - `data` (optional): JSON string. All fields inside are optional. Omit entirely, send `{}`, or send any subset of:
    - `personal_message` (string)
    - `qr_code_data` (string)
    - `design_metadata` (object, e.g. `{ "font_size": 18 }`)
    - `receiver_contact_id` (UUID string from GET /contacts)

- **Success response (201):**
```json
{
  "message": "Postcard sent successfully",
  "postcard": {
    "id": "uuid",
    "user_id": "uuid",
    "receiver_contact_id": "uuid or null",
    "front_image_path": "https://... or path",
    "back_image_path": "https://... or path",
    "personal_message": "...",
    "qr_code_data": "...",
    "design_metadata": { ... },
    "image_metadata": { "front": {...}, "back": {...} },
    "created_at": "2026-02-13T..."
  }
}
```

- **Displaying images:** When using S3, `front_image_path` and `back_image_path` are full URLs; use them directly in `<img src="...">` or `<video src="...">`. Without S3, prefix with your API base URL + `/uploads/` (e.g. `http://localhost:8000/uploads/` + path).

### List my postcards

- **Request:** `GET /api/v1/postcards?page=1&limit=10`
- **Headers:** `Authorization: Bearer <token>`
- **Response:** `{ "items": [...], "page": 1, "limit": 10, "total": 42, "total_pages": 5 }`

### Get one postcard

- **Request:** `GET /api/v1/postcards/{postcard_id}`
- **Headers:** `Authorization: Bearer <token>`
- **Response:** Same shape as one item in the list / the `postcard` object in create response.

---

## Profile image

- **Upload profile image:** `PATCH /api/v1/users/me/profile-image`  
  Headers: `Authorization: Bearer <token>`  
  Body: `multipart/form-data` with one file field (e.g. `file`: image).  
  Only works when S3 is configured. Response includes updated user with `profile_image_url` (S3 URL).

- **Get my profile:** `GET /api/v1/users/me`  
  Headers: `Authorization: Bearer <token>`  
  Response includes `profile_image_url`.

---

## Example: create postcard from the browser (fetch)

```javascript
const token = "…"; // from login
const formData = new FormData();
formData.append("front_file", frontFile);   // File from <input type="file">
formData.append("back_file", backFile);     // File from <input type="file">
// Optional: only if you have message or receiver
formData.append("data", JSON.stringify({
  personal_message: "Happy birthday!",
  receiver_contact_id: "5c473ef1-2351-419d-9a33-25aaa5f03c86"
}));

const res = await fetch("http://localhost:8000/api/v1/postcards", {
  method: "POST",
  headers: { "Authorization": `Bearer ${token}` },
  body: formData
});
const json = await res.json();
// json.message === "Postcard sent successfully"
// json.postcard has id, front_image_path, back_image_path, etc.
```

---

## Example: create postcard with no data (only files)

Omit the `data` field, or send empty JSON:

```javascript
formData.append("front_file", frontFile);
formData.append("back_file", backFile);
formData.append("data", "{}");
```

All fields inside `data` are optional; you can send `{}`, omit `data`, or include only the fields you need.
