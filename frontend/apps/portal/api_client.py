import logging
from typing import Any, Dict, Optional, Tuple
from django.conf import settings
import requests

logger = logging.getLogger(__name__)


class APIClient:
    """HTTP Client communicating with the Donatily Django REST backend."""

    def __init__(self, request=None):
        self.request = request
        self.base_url = settings.BACKEND_API_URL.rstrip("/")
        self.timeout = settings.API_TIMEOUT_SECONDS

    def _get_headers(self, custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
        }
        if self.request and hasattr(self.request, "session"):
            token = self.request.session.get("access_token")
            if token:
                headers["Authorization"] = f"Bearer {token}"
        if custom_headers:
            headers.update(custom_headers)
        return headers

    def _refresh_token(self) -> bool:
        if not self.request or not hasattr(self.request, "session"):
            return False
        refresh = self.request.session.get("refresh_token")
        if not refresh:
            return False

        try:
            url = f"{self.base_url}/api/auth/refresh/"
            resp = requests.post(url, json={"refresh": refresh}, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                self.request.session["access_token"] = data.get("access")
                if "refresh" in data:
                    self.request.session["refresh_token"] = data.get("refresh")
                self.request.session.modified = True
                return True
        except Exception as exc:
            logger.error("Token refresh failed: %s", exc)

        return False

    def request_api(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        retry_on_401: bool = True,
    ) -> Tuple[int, Any]:
        """Execute HTTP request against backend REST API."""
        url = f"{self.base_url}{path}" if path.startswith("/") else f"{self.base_url}/{path}"
        req_headers = self._get_headers(headers)

        try:
            resp = requests.request(
                method=method.upper(),
                url=url,
                data=data,
                json=json,
                params=params,
                files=files,
                headers=req_headers,
                timeout=self.timeout,
            )

            # Auto-retry once on 401 expired token
            if resp.status_code == 401 and retry_on_401 and self._refresh_token():
                req_headers = self._get_headers(headers)
                resp = requests.request(
                    method=method.upper(),
                    url=url,
                    data=data,
                    json=json,
                    params=params,
                    files=files,
                    headers=req_headers,
                    timeout=self.timeout,
                )

            # Parse response
            try:
                res_data = resp.json() if resp.content else {}
            except Exception:
                res_data = {"raw": resp.text}

            return resp.status_code, res_data

        except requests.RequestException as exc:
            logger.error("API error for %s %s: %s", method, url, exc)
            return 503, {"detail": f"Service API temporairement indisponible: {str(exc)}"}

    def get(self, path: str, params=None, headers=None):
        return self.request_api("GET", path, params=params, headers=headers)

    def post(self, path: str, data=None, json=None, files=None, headers=None):
        return self.request_api("POST", path, data=data, json=json, files=files, headers=headers)

    def patch(self, path: str, data=None, json=None, files=None, headers=None):
        return self.request_api("PATCH", path, data=data, json=json, files=files, headers=headers)

    def put(self, path: str, data=None, json=None, files=None, headers=None):
        return self.request_api("PUT", path, data=data, json=json, files=files, headers=headers)

    def delete(self, path: str, params=None, headers=None):
        return self.request_api("DELETE", path, params=params, headers=headers)


def format_api_errors(data: Any) -> str:
    """Format DRF error responses into readable messages."""
    if isinstance(data, dict):
        if "detail" in data:
            return str(data["detail"])
        errors = []
        for k, v in data.items():
            if isinstance(v, list):
                errors.append(f"{k}: {', '.join(str(i) for i in v)}")
            else:
                errors.append(f"{k}: {v}")
        return " | ".join(errors)
    return str(data)
