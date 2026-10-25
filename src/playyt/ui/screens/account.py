"""Account screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Static

from ...services.authentication import auth


class AccountScreen(Screen):
    """YouTube account status and authentication."""

    def compose(self) -> ComposeResult:
        yield Static("Account", id="account-title")
        yield Static("")
        if auth.is_authenticated():
            yield Static("Status: Connected", classes="section")
            yield Static("Press below to log out.")
            yield Button("Log out", id="btn-logout")
        else:
            yield Static("Status: Not connected", classes="section")
            yield Static("")
            yield Static("Press Enter to authenticate.", id="auth-hint")
            yield Static("")
            yield Button("Authenticate", id="btn-auth")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-auth":
            self.app.notify("Opening device flow... check logs.")
        elif event.button.id == "btn-logout":
            auth.logout()
            self.app.notify("Logged out.")
            self.app.push_screen(AccountScreen())
