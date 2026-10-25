"""Google OAuth 2.0 device-flow integration for PlayYT."""

from __future__ import annotations

import json
import os
import time

import requests

from ..config.paths import credentials_dir
from ..utils.errors import AuthenticationError
from ..utils.logging import get_logger

logger = get_logger("oauth")

# Scopes needed for YouTube Data API read access.
SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

HTTP_OK = 200
DEVICE_FLOW_TIMEOUT = 900

TOKEN_URI = "https://oauth2.googleapis.com/token"
DEVICE_URI = "https://oauth2.googleapis.com/device/code"


class GoogleOAuth:
    """Handles Google OAuth 2.0 device flow for headless servers."""

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> None:
        self.client_id = client_id or os.environ.get("PLAYYT_CLIENT_ID", "")
        self.client_secret = client_secret or os.environ.get("PLAYYT_CLIENT_SECRET", "")
        self._credentials_configured = bool(self.client_id and self.client_secret)
        self.credentials_dir = credentials_dir()
        self.credentials_dir.mkdir(parents=True, exist_ok=True)
        self.token_path = self.credentials_dir / "tokens.json"

    def _require_credentials(self) -> None:
        if not self._credentials_configured:
            raise AuthenticationError(
                "OAuth client credentials not configured. "
                "Set PLAYYT_CLIENT_ID and PLAYYT_CLIENT_SECRET."
            )

    # ------------------------------------------------------------------ #
    # Token storage
    # ------------------------------------------------------------------ #
    def _load_tokens(self) -> dict | None:
        if not self.token_path.exists():
            return None
        try:
            with self.token_path.open("r", encoding="utf-8") as fh:
                return json.load(fh)  # type: ignore[no-any-return]
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to read stored tokens: %s", exc)
            return None

    def _save_tokens(self, tokens: dict) -> None:
        # Never log tokens.
        with self.token_path.open("w", encoding="utf-8") as fh:
            json.dump(tokens, fh)
        try:
            os.chmod(self.token_path, 0o600)
        except OSError:
            pass

    def clear_tokens(self) -> None:
        if self.token_path.exists():
            self.token_path.unlink()

    def has_valid_tokens(self) -> bool:
        tokens = self._load_tokens()
        if not tokens:
            return False
        # Consider valid if we have a refresh token (can refresh access token).
        return bool(tokens.get("refresh_token"))

    def get_access_token(self) -> str | None:
        """Return a valid access token, refreshing if necessary."""
        tokens = self._load_tokens()
        if not tokens:
            return None
        access_token = tokens.get("access_token")
        expiry = tokens.get("expiry", 0)
        if access_token and time.time() < expiry:
            return access_token  # type: ignore[no-any-return]
        return self._refresh_access_token(tokens)

    def _refresh_access_token(self, tokens: dict) -> str | None:
        self._require_credentials()
        refresh_token = tokens.get("refresh_token")
        if not refresh_token:
            return None
        try:
            resp = requests.post(
                TOKEN_URI,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
                timeout=30,
            )
        except requests.RequestException as exc:
            logger.warning("Token refresh failed: %s", exc)
            return None
        if resp.status_code != HTTP_OK:
            logger.warning("Token refresh returned %s", resp.status_code)
            return None
        data = resp.json()
        new_tokens = {
            "access_token": data["access_token"],
            "refresh_token": tokens.get("refresh_token"),
            "expiry": time.time() + data.get("expires_in", 3600),
            "token_type": data.get("token_type", "Bearer"),
        }
        self._save_tokens(new_tokens)
        return new_tokens["access_token"]  # type: ignore[no-any-return]

    # ------------------------------------------------------------------ #
    # Device flow
    # ------------------------------------------------------------------ #
    def start_device_flow(self) -> dict:
        """Begin the OAuth device flow. Returns user-facing info."""
        self._require_credentials()
        try:
            resp = requests.post(
                DEVICE_URI,
                data={
                    "client_id": self.client_id,
                    "scope": " ".join(SCOPES),
                },
                timeout=30,
            )
        except requests.RequestException as exc:
            raise AuthenticationError(f"Unable to reach Google OAuth: {exc}") from exc
        if resp.status_code != HTTP_OK:
            raise AuthenticationError(f"Device flow request failed ({resp.status_code})")
        data = resp.json()
        if "error" in data:
            raise AuthenticationError(data.get("error_description", "OAuth error"))
        return {
            "device_code": data["device_code"],
            "user_code": data["user_code"],
            "verification_url": data["verification_url"],
            "expires_in": data.get("expires_in", 900),
            "interval": data.get("interval", 5),
        }

    def poll_for_token(self, device_code: str, interval: int) -> dict:
        """Poll Google until the user authorizes or the flow expires."""
        self._require_credentials()
        deadline = time.time() + DEVICE_FLOW_TIMEOUT
        while time.time() < deadline:
            try:
                resp = requests.post(
                    TOKEN_URI,
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "device_code": device_code,
                        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    },
                    timeout=30,
                )
            except requests.RequestException as exc:
                logger.warning("Token poll error: %s", exc)
                time.sleep(interval)
                continue

            if resp.status_code == HTTP_OK:
                data = resp.json()
                tokens = {
                    "access_token": data["access_token"],
                    "refresh_token": data.get("refresh_token"),
                    "expiry": time.time() + data.get("expires_in", 3600),
                    "token_type": data.get("token_type", "Bearer"),
                }
                self._save_tokens(tokens)
                logger.info("OAuth authorization complete")
                return tokens

            error = resp.json().get("error", "")
            if error == "authorization_pending":
                time.sleep(interval)
                continue
            if error in ("slow_down",):
                interval += 5
                time.sleep(interval)
                continue
            if error in ("access_denied", "expired_token"):
                raise AuthenticationError("Authorization was denied or expired.")
            logger.warning("Unexpected poll response: %s", error)
            time.sleep(interval)

        raise AuthenticationError("Authorization timed out.")
