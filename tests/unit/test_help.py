"""Tests for the help screen."""

from __future__ import annotations

import asyncio

from playyt.app import PlayYTApp
from playyt.ui.screens.help import HelpScreen


def test_help_escape_closes_screen() -> None:
    async def scenario() -> None:
        app = PlayYTApp()
        async with app.run_test() as pilot:
            await pilot.pause(0.2)
            await pilot.press("?")
            await pilot.pause()
            assert isinstance(app.screen, HelpScreen)
            await pilot.press("escape")
            await pilot.pause()
            assert not isinstance(app.screen, HelpScreen)

    asyncio.run(scenario())
