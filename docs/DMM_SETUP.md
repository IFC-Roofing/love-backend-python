# DMM (Direct Mail Manager) integration

After a postcard is created, **send** is triggered via `POST /api/v1/mailings`. That call uses DMM to actually send the postcard (physical mail).

## Env variables (set in .env or .env.docker)

| Variable | Required | Description |
|----------|----------|-------------|
| `DIRECT_MAIL_MANAGER_API_URL` | Yes (for DMM) | DMM API base URL, e.g. `https://api.directmailmanager.com/api` (no trailing slash) |
| `DIRECT_MAIL_MANAGER_API_KEY` | Yes (for DMM) | Your DMM API key (Bearer) |
| `DMM_FROM_ADDRESS` | Recommended | JSON: return address. Example: `{"first_name":"John","last_name":"Smith","street":"5115 Colleyville Blvd","city":"Colleyville","state":"TX","postal_code":"76034","country":"US","company":"IFC Roofing"}`. Optional keys: `first_name`, `last_name`, `company`. |
| `DMM_SENDER_COPY_ADDRESS` | Optional | JSON: where to send sender copy (same shape as above) |

## Flow

1. Create postcard: `POST /api/v1/postcards` (front/back images; stored in S3 or local).
2. Trigger send: `POST /api/v1/mailings` with:
   - `postcard_id`: id from step 1
   - `contact_ids`: list of contact UUIDs (contacts must have `address_line1`, `city`, `state` or `postal_code`, `country`), **or**
   - `recipient_name` + `recipient_address`: one-off recipient
   - `send_sender_copy`: optional boolean
3. Backend builds HTML from postcard’s stored image URLs and POSTs to DMM; creates one Mailing per recipient.
4. List/check: `GET /api/v1/mailings`, `GET /api/v1/mailings/{id}`, `POST /api/v1/mailings/sync-status`.

## Contacts and seed

Existing seeded contacts (e.g. for user `df8e2c7d-0225-4ac0-b9c9-65cf422860f3`) are unchanged. To send to a contact via DMM, that contact must have mailing address fields set (`name`, `address_line1`, `city`, `state`, `postal_code`, `country`). You can add/update those via your app or DB; the seed only inserts `id`, `user_id`, `email`.

## Image URLs

Front/back URLs are taken from the postcard as stored in the DB (e.g. S3 URLs when using S3). DMM must be able to fetch those URLs to render the postcard. Use S3 with public read (or DMM-accessible URLs) for mailings to work.
