"""Authentication service for PlayYT."""

from __future__ import annotations

from ..integrations.google_oauth import GoogleOAuth
from ..models.account import Account
from ..utils.errors import AuthenticationError
from ..utils.logging import get_logger

logger = get_logger("auth")


class AuthenticationService:
    """Manages Google OAuth authentication state."""

    def __init__(self, oauth: GoogleOAuth | None = None) -> None:
        self.oauth = oauth or GoogleOAuth()
        self.account = Account()

    def is_authenticated(self) -> bool:
        return self.oauth.has_valid_tokens()

    def authenticate(self) -> None:
        """Run the OAuth device flow interactively."""
        if self.is_authenticated():
            self.account.authenticated = True
            return
        try:
            info = self.oauth.start_device_flow()
        except AuthenticationError as exc:
            logger.warning("OAuth start failed: %s", exc)
            raise
        self.oauth.poll_for_token(info["device_code"], info["interval"])
        self.account.authenticated = True
        logger.info("Account authenticated")

    def logout(self) -> None:
        self.oauth.clear_tokens()
        self.account = Account()
        logger.info("Account logged out")

    def access_token(self) -> str | None:
        return self.oauth.get_access_token()


auth = AuthenticationService()
