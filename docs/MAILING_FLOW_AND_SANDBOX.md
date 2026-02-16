# How mailing works in this app (analysis)

## End-to-end flow

```
1. User creates a postcard (POST /api/v1/postcards)
   → Front/back files uploaded to S3 (or local).
   → Postcard row saved with front_image_path, back_image_path (URLs), personal_message, qr_code_data.
   → No DMM call.

2. User sends the postcard (POST /api/v1/mailings)
   → Body: postcard_id, contact_ids (or recipient_name + recipient_address), optional send_sender_copy.
   → Backend loads postcard (must belong to current user).
   → Builds HTML from postcard:
      - front_artwork: valid HTML5 doc with <img src="front_image_path"> (or <video> if .mp4/.webm/.mov).
      - back_artwork: valid HTML5 doc with back image + personal_message + qr_code_data.
   → For each recipient:
      - Build to_address from contact (or parsed recipient_address).
      - POST to DMM: { name, size: "4x6", mail_type: "first_class", front_artwork, back_artwork, from_address, to_address }.
      - On success: create Mailing row (postcard_id, user_id, contact_id, status, external_id = DMM id).
   → If send_sender_copy and DMM_SENDER_COPY_ADDRESS set: one more POST to DMM, same artwork, to_address = sender; create Mailing for "Sender copy".
   → Response includes results (per recipient), front_artwork, back_artwork (so you can verify what was sent).

3. List / get mailings (GET /api/v1/mailings, GET /api/v1/mailings/{id})
   → Returns mailings for current user with status, external_id, and front_artwork / back_artwork (rebuilt from postcard).

4. Sync status (POST /api/v1/mailings/sync-status)
   → For each mailing with external_id and status not sent/canceled: GET DMM /postcards/{external_id}, update mailing.status.
```

## Key components

| Component | Role |
|-----------|------|
| **Config** | `DIRECT_MAIL_MANAGER_API_URL`, `DIRECT_MAIL_MANAGER_API_KEY`, optional `DMM_FROM_ADDRESS`, `DMM_SENDER_COPY_ADDRESS`. `use_dmm` = true when URL and key are set. |
| **Postcard** | Stores front/back image URLs (S3 or path), personal_message, qr_code_data. No DMM call on create. |
| **Contact** | Must have address (address_line1, city, state or postal_code, country) to send via contact_ids. |
| **DMM client** | POST /postcards with name, size, mail_type, front_artwork, back_artwork, from_address, to_address. GET /postcards/{id} for status. |
| **HTML builder** | Builds valid HTML5 from postcard URLs; wraps in `<!DOCTYPE html><html>...<body>...</body></html>`. |
| **Mailing** | One row per successful DMM send; stores external_id (DMM postcard id) and status. |

## Is it working?

- **Yes**, when:
  - Env has `DIRECT_MAIL_MANAGER_API_URL` and `DIRECT_MAIL_MANAGER_API_KEY` (and `DMM_FROM_ADDRESS` with at least street + city).
  - Postcard uses **image** URLs for front/back (not video) so DMM can render for print.
  - Contact has full mailing address.
  - You get `success: true`, `mailing_id`, and `external_id` (e.g. `psc_...`) in the create response.

- **Failure cases:** DMM not configured (503), postcard not found (404), contact missing address (error in results), DMM returns 4xx/5xx (error in results; we log and include DMM message).

---

# Steps to see mailings in the DMM sandbox dashboard

You are using **sandbox**: `DIRECT_MAIL_MANAGER_API_URL=https://sandbox.directmailmanager.com/api`.

## 1. Log in to the sandbox

- Open: **https://sandbox.directmailmanager.com**  
  (or the sandbox login URL from your DMM account; it may be under “Sandbox” or “Test” in the main site.)
- Log in with the **same DMM account** that owns the API key in `DIRECT_MAIL_MANAGER_API_KEY`.  
  If the key is for a different account or environment, you will not see these postcards.

## 2. Find “Postcards” (or “Mail” / “Campaigns”)

- In the sandbox app, go to the section that lists **postcards** or **mailings** (often **Postcards**, **Orders**, or **Campaigns** in the menu).
- Make sure you are in **Sandbox** mode if the UI has a Production / Sandbox switch.

## 3. Locate your mailing

Use one or more of:

- **By name**  
  We send `name: "Postcard - {recipient_name}"` (e.g. **"Postcard - Jennifer Jaeger"**). Use search or filter by name.

- **By date**  
  Filter by the **date** you called `POST /api/v1/mailings` (created_at / send_date).

- **By ID**  
  From your app response, take **external_id** (e.g. `psc_69934795b5870`). In DMM, search or open postcard detail by this ID if the UI supports it.

## 4. Confirm what you see

- Each row/card should match one **Mailing** in your app (same **external_id**).
- Status in DMM (e.g. scheduled, sent) can be synced back with **POST /api/v1/mailings/sync-status**.
- You can open a postcard to see front/back artwork (DMM’s rendered version) and recipient address.

## 5. If you don’t see anything

- **Wrong account** – API key must belong to the account you’re logged into.
- **Wrong environment** – You must be in **Sandbox** when using `https://sandbox.directmailmanager.com/api`.
- **Wrong section** – Try **Postcards**, **Orders**, or **Campaigns** (names vary by DMM UI).
- **Verify via API** – Call `GET https://sandbox.directmailmanager.com/api/postcards/{external_id}` with header `Authorization: Bearer {your_api_key}`. If you get 200 and a postcard object, it exists in sandbox; then the issue is only where it appears in the dashboard.

---

## Quick checklist

1. Create postcard (image front/back) → **POST /api/v1/postcards**.
2. Ensure contact has full address (or use recipient_name + recipient_address).
3. Send mailing → **POST /api/v1/mailings** with postcard_id and contact_ids (or recipient).
4. Note **external_id** (e.g. `psc_...`) from the response.
5. Log in to **https://sandbox.directmailmanager.com** with the same account as the API key.
6. Open **Postcards** (or equivalent), filter by date/name, or search by **external_id**.
7. Optionally sync status in your app → **POST /api/v1/mailings/sync-status**.
