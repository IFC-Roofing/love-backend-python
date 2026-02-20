# Chat API – Frontend Integration Guide

This document describes how to integrate the chat feature in your frontend. All chat endpoints require the user to be authenticated using the same token returned by **POST /api/v1/auth/login**.

---

## 1. Authentication

- **Get token:** Call `POST /api/v1/auth/login` with `{ "email": "...", "password": "..." }`.
- **Response** includes `access_token` (JWT). Use this for all chat requests.
- **REST:** Send header: `Authorization: Bearer <access_token>`.
- **WebSocket:** Append token to URL: `wss://<host>/api/v1/chat/ws?token=<access_token>`.

If the token is missing or invalid, REST endpoints return `401`; the WebSocket closes with code `4001`.

---

## 2. Base URL

- REST: `https://<your-api-host>/api/v1/chat`
- WebSocket: `wss://<your-api-host>/api/v1/chat/ws` (or `ws://` for local dev)

---

## 3. Chat API paths reference

Use these **full paths** relative to your API host (e.g. `https://<host>/api/v1/chat/rooms`). Do not call shorter paths like `/rooms`—they will return 404. Example: create or get a room is **POST** `/api/v1/chat/rooms`, not **POST** `/rooms`.

| Method     | Full path                                   | Purpose                                                                                  |
| ---------- | ------------------------------------------- | ---------------------------------------------------------------------------------------- |
| GET        | `/api/v1/chat/rooms`                         | List rooms for current user (query: page, limit, chat_type)                              |
| POST       | `/api/v1/chat/rooms`                         | Create or get direct room (body: other_user_id or contact_id)                            |
| GET        | `/api/v1/chat/rooms/{room_id}`               | Get one room (must be participant)                                                       |
| GET        | `/api/v1/chat/rooms/{room_id}/messages`      | List messages, mark room read (query: page, limit, before_id)                            |
| POST       | `/api/v1/chat/rooms/{room_id}/messages`      | Send message (body: content, optional quote_id)                                           |
| WebSocket  | `/api/v1/chat/ws`                            | Real-time: connect with ?token=; subscribe/typing; receive message_created, user_typing  |

---

## 4. REST Endpoints (detail)

### 4.1 List rooms

**GET** `/rooms`

Returns the list of rooms the current user participates in, ordered by `last_message_at` (newest first).

| Query param   | Type   | Default | Description                    |
|---------------|--------|---------|--------------------------------|
| `page`        | number | 1       | Page number (1-based).        |
| `limit`       | number | 20      | Items per page (1–100).       |
| `chat_type`   | string | —       | Optional filter (e.g. `direct`). |

**Response (200):**

```json
{
  "items": [
    {
      "id": "uuid",
      "chat_type": "direct",
      "contact_id": null,
      "topic": null,
      "last_message_at": "2025-02-13T12:00:00",
      "created_at": "2025-02-13T10:00:00",
      "unread_count": 2,
      "last_message_preview": {
        "id": "uuid",
        "content": "Last message text...",
        "user_id": "uuid",
        "created_at": "2025-02-13T12:00:00"
      },
      "other_participants": [
        { "user_id": "uuid", "email": "other@example.com" }
      ]
    }
  ],
  "page": 1,
  "limit": 20,
  "total": 5,
  "total_pages": 1
}
```

---

### 4.2 Create or get a direct room

**POST** `/rooms`

Creates a new direct room or returns an existing one with the given user or contact.

**Request body (one of):**

```json
{ "other_user_id": "uuid-of-another-user" }
```

or

```json
{ "contact_id": "uuid-of-contact" }
```

- **other_user_id:** 1:1 room with another user. Cannot be the current user.
- **contact_id:** Room linked to a contact (e.g. for “chat with this contact” UI).

**Response (201):**

```json
{
  "id": "room-uuid",
  "chat_type": "direct",
  "contact_id": null,
  "topic": null,
  "last_message_at": null,
  "created_at": "2025-02-13T10:00:00",
  "unread_count": 0,
  "other_participants": [
    { "user_id": "uuid", "email": "other@example.com" }
  ]
}
```

**Errors:**

- `400` – e.g. `other_user_id` is the current user (`INVALID_OTHER_USER`).
- `404` – User or contact not found.

---

### 4.3 Get a single room

**GET** `/rooms/{room_id}`

Returns room details. Allowed only if the current user is a participant.

**Response (200):**

Same shape as a single room in the list (see 3.1), including `unread_count` and `other_participants`.

**Errors:** `404` if room not found or user is not a participant.

---

### 4.4 List messages in a room

**GET** `/rooms/{room_id}/messages`

Returns paginated messages for the room. **Side effect:** marks the room as read for the current user (unread count set to 0).

| Query param | Type   | Default | Description                                  |
|-------------|--------|---------|----------------------------------------------|
| `page`      | number | 1       | Page number (1-based).                       |
| `limit`     | number | 20      | Items per page.                              |
| `before_id` | string | —       | Optional: return messages before this message ID (cursor-style). |

**Response (200):**

```json
{
  "items": [
    {
      "id": "uuid",
      "room_id": "uuid",
      "user_id": "uuid",
      "content": "Message text",
      "quote_id": null,
      "created_at": "2025-02-13T12:00:00"
    }
  ],
  "page": 1,
  "limit": 20,
  "total": 42,
  "total_pages": 3
}
```

**Errors:** `404` if room not found or user is not a participant.

---

### 4.5 Send a message

**POST** `/rooms/{room_id}/messages`

Creates a message in the room. Only allowed if the current user is a participant.  
**Side effects:** updates the room’s `last_message_at`, increments `unread_count` for other participants, and broadcasts a `message_created` event to all WebSocket subscribers of this room.

**Request body:**

```json
{
  "content": "Your message text",
  "quote_id": null
}
```

- `content` (string, required): message body.
- `quote_id` (uuid, optional): ID of the message being quoted.

**Response (201):**

Same shape as a single message in the list (see 3.4), e.g.:

```json
{
  "id": "uuid",
  "room_id": "uuid",
  "user_id": "uuid",
  "content": "Your message text",
  "quote_id": null,
  "created_at": "2025-02-13T12:05:00"
}
```

**Errors:** `404` if room not found or user is not a participant.

---

## 5. WebSocket (real-time)

**URL:** `GET /api/v1/chat/ws?token=<access_token>`

- Use the same `access_token` as for REST.
- If the token is invalid or missing, the connection is closed with code **4001**.

### 5.1 Client → Server (send JSON text frames)

All messages are JSON objects with an `action` and a `room_id` (UUID string). The user must be a participant of the room; otherwise the message is ignored.

| Action        | Description                          | Payload example                                      |
|---------------|--------------------------------------|------------------------------------------------------|
| `subscribe`   | Subscribe to a room’s events.        | `{ "action": "subscribe", "room_id": "<uuid>" }`     |
| `unsubscribe` | Stop receiving events for that room. | `{ "action": "unsubscribe", "room_id": "<uuid>" }`    |
| `typing`      | Broadcast typing indicator to others.| `{ "action": "typing", "room_id": "<uuid>", "typing": true }` |

- **subscribe:** Send when the user opens a conversation; required to receive `message_created` and `user_typing` for that room.
- **typing:** Send while the user is typing; use `typing: false` when they stop. The server broadcasts to other participants in the room (not to the sender).

### 5.2 Server → Client (events)

Each event is a JSON text frame with:

- `event` – event name.
- `room_id` – room UUID (string).
- `payload` – event data.

**message_created** (new message in a room you’re subscribed to):

```json
{
  "event": "message_created",
  "room_id": "uuid",
  "payload": {
    "id": "uuid",
    "room_id": "uuid",
    "user_id": "uuid",
    "content": "Hello!",
    "quote_id": null,
    "created_at": "2025-02-13T12:05:00"
  }
}
```

**user_typing** (another participant started or stopped typing):

```json
{
  "event": "user_typing",
  "room_id": "uuid",
  "payload": {
    "user_id": "uuid",
    "typing": true
  }
}
```

---

## 6. Recommended frontend flow

1. **Conversation list**
   - `GET /rooms?page=1&limit=20` to load rooms.
   - Use `unread_count` and `last_message_preview` for badges and previews.
   - Use `other_participants` for display names/avatars.

2. **Start or open a conversation**
   - To start with another user: `POST /rooms` with `{ "other_user_id": "<uuid>" }`.
   - To open an existing room: `GET /rooms/{room_id}`.
   - Load messages: `GET /rooms/{room_id}/messages?page=1&limit=50` (this marks the room as read).

3. **Real-time connection**
   - Open WebSocket: `wss://<host>/api/v1/chat/ws?token=<access_token>`.
   - When user opens a room, send: `{ "action": "subscribe", "room_id": "<room_id>" }`.
   - When leaving the room (or closing chat), send: `{ "action": "unsubscribe", "room_id": "<room_id>" }`.

4. **Sending messages**
   - `POST /rooms/{room_id}/messages` with `{ "content": "...", "quote_id": null }`.
   - Optimistically add the message to the UI; optionally update when you receive `message_created` over WebSocket for consistency.

5. **Typing indicator**
   - On keydown/focus: send `{ "action": "typing", "room_id": "<room_id>", "typing": true }`.
   - After a short idle or on blur: send `{ "action": "typing", "room_id": "<room_id>", "typing": false }`.
   - When you receive `user_typing`, show “X is typing…” for that `user_id`.

6. **Reconnection**
   - If the WebSocket closes (e.g. network drop), reconnect with the same token and re-send `subscribe` for the currently open room(s).

---

## 7. Error responses (REST)

- **401 Unauthorized** – Missing or invalid `Authorization` header / token.
- **404 Not Found** – Room, user, or contact not found, or current user is not a participant.
- **400 Bad Request** – Invalid body (e.g. `other_user_id` is self, validation errors). Response body may include a `detail` object with `code` and `message`.

Use the same token for both REST and WebSocket; it is issued by your backend on login and is not generated by the frontend.
