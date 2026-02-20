"""
Direct Mail Manager API client.
Calls DMM with image URLs as stored in DB (e.g. S3 URLs).
"""
import logging
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings
from app.dmm.address import parse_address_json

logger = logging.getLogger(__name__)


class DMMClientError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, body: Optional[Any] = None):
        self.status_code = status_code
        self.body = body
        super().__init__(message)


class DMMClient:
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = (base_url or settings.DIRECT_MAIL_MANAGER_API_URL or "").rstrip("/")
        self.api_key = api_key or settings.DIRECT_MAIL_MANAGER_API_KEY

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def create_postcard(
        self,
        front_html: str,
        back_html: str,
        to_address: Dict[str, Any],
        from_address: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a postcard in DMM. Payload matches RoR app: name, size, mail_type, front_artwork, back_artwork, from_address, to_address.
        """
        if not self.base_url or not self.api_key:
            raise DMMClientError("DMM API URL and API key must be set")

        from_addr = from_address or parse_address_json(settings.DMM_FROM_ADDRESS) or {}
        to_payload = {
            "first_name": to_address.get("first_name") or "",
            "last_name": to_address.get("last_name") or "",
            "address_line1": to_address.get("address_line1") or "",
            "address_line2": to_address.get("address_line2") or "",
            "address_city": to_address.get("address_city") or "",
            "address_state": to_address.get("address_state") or "",
            "address_zip": to_address.get("address_zip") or "",
        }
        body: Dict[str, Any] = {
            "name": name or "Postcard",
            "size": "4x6",
            "mail_type": "first_class",
            "front_artwork": front_html,
            "back_artwork": back_html,
            "to_address": to_payload,
        }
        if from_addr:
            body["from_address"] = {
                "first_name": from_addr.get("first_name") or "",
                "last_name": from_addr.get("last_name") or "",
                "address_line1": from_addr.get("address_line1") or "",
                "address_city": from_addr.get("address_city") or "",
                "address_state": from_addr.get("address_state") or "",
                "address_zip": from_addr.get("address_zip") or "",
                "company": from_addr.get("company") or "",
            }

        try:
            with httpx.Client(timeout=30.0) as client:
                r = client.post(self._url("postcards"), headers=self._headers(), json=body)
        except httpx.RequestError as e:
            logger.exception("DMM create postcard request error")
            raise DMMClientError(str(e))

        if r.status_code >= 400:
            logger.warning("DMM create postcard error %s: %s", r.status_code, r.text[:500] if r.text else "")
            msg = f"DMM create postcard failed: {r.status_code}"
            if r.text:
                try:
                    err_json = r.json()
                    detail = err_json.get("message") or err_json.get("error") or str(err_json)[:300]
                    msg = f"{msg} — {detail}"
                except Exception:
                    msg = f"{msg} — {r.text[:300]}"
            raise DMMClientError(msg, status_code=r.status_code, body=r.text)

        data = r.json() if r.content else {}
        if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
            data = data["data"]
        external_id = data.get("id") if isinstance(data, dict) else data.get("postcard_id")
        return {"id": external_id, "status": data.get("status", "pending") if isinstance(data, dict) else "pending"}

    def get_postcard(self, external_id: str) -> Dict[str, Any]:
        if not self.base_url or not self.api_key:
            raise DMMClientError("DMM API URL and API key must be set")
        try:
            with httpx.Client(timeout=15.0) as client:
                r = client.get(self._url(f"postcards/{external_id}"), headers=self._headers())
        except httpx.RequestError as e:
            logger.exception("DMM get postcard request error")
            raise DMMClientError(str(e))
        if r.status_code >= 400:
            raise DMMClientError(f"DMM get postcard failed: {r.status_code}", status_code=r.status_code, body=r.text)
        data = r.json() if r.content else {}
        if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict):
            data = data["data"]
        status = data.get("status", "unknown") if isinstance(data, dict) else "unknown"
        return {"id": external_id, "status": status, **(data if isinstance(data, dict) else {})}


dmm_client = DMMClient()
