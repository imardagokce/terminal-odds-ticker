"""Custom Textual widgets for inspecting an individual fixture."""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widget import Widget
from textual.widgets import Input, Static

from odds_ticker.analytics import (
    calculate_fractional_kelly,
    calculate_implied_probability,
    calculate_overround,
)


class MatchDetailView(Widget):
    """Show selected fixture probabilities, bookmaker margin and stake guidance."""

    DEFAULT_CSS = """
    MatchDetailView { height: 1fr; }
    #detail-content { height: auto; padding-bottom: 1; }
    #bankroll { margin-top: 1; }
    #movement-log { height: auto; padding-top: 1; }
    """

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._match: dict[str, Any] | None = None
        self._history: list[float] = []

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Select a fixture to inspect its market.", id="detail-content")
            yield Input(value="1000.00", placeholder="Bankroll", id="bankroll", type="number")
            yield Static("Odds movement will appear here.", id="movement-log")

    def set_match(self, match: dict[str, Any]) -> None:
        """Display a fixture and append its selected odds to the movement log."""
        if self._match is None or match["match_id"] != self._match["match_id"]:
            self._history = []
        self._match = match
        selected_odds = {
            "Home": float(match["home_win"]),
            "Draw": float(match["draw"]),
            "Away": float(match["away_win"]),
        }[str(match["value_pick"])]
        self._history.append(selected_odds)
        self._history = self._history[-6:]
        self._render_match()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Recalculate the stake whenever the bankroll input changes."""
        if event.input.id == "bankroll":
            self._render_match()

    def _render_match(self) -> None:
        if self._match is None or not self.is_mounted:
            return
        match = self._match
        prices = (float(match["home_win"]), float(match["draw"]), float(match["away_win"]))
        try:
            bankroll = float(self.query_one("#bankroll", Input).value)
            stake = calculate_fractional_kelly(
                odds={"Home": prices[0], "Draw": prices[1], "Away": prices[2]}[str(match["value_pick"])] ,
                estimated_prob=float(match["value_probability"]),
                bankroll=bankroll,
            )
            stake_text = f"£{stake:,.2f} (quarter Kelly)"
        except (ValueError, TypeError):
            stake_text = "Enter a valid bankroll"
        implied = tuple(calculate_implied_probability(price) * 100 for price in prices)
        margin = calculate_overround(*prices)
        content = (
            f"[bold]{match['home_team']} v {match['away_team']}[/bold]\n"
            f"{match['league']}\n\n"
            f"Home   {prices[0]:.2f}  ({implied[0]:.1f}% implied)\n"
            f"Draw   {prices[1]:.2f}  ({implied[1]:.1f}% implied)\n"
            f"Away   {prices[2]:.2f}  ({implied[2]:.1f}% implied)\n\n"
            f"Bookmaker vig  {margin:+.2f}%\n"
            f"Value edge     {float(match['value_edge']):+.2f}%\n"
            f"Value pick     {match['value_pick']}\n"
            f"Suggested stake {stake_text}\n\n"
            f"Updated {match['timestamp'].strftime('%H:%M:%S UTC')}"
        )
        self.query_one("#detail-content", Static).update(content)
        movements = " ➔ ".join(f"{price:.2f}" for price in self._history)
        if len(self._history) > 1:
            arrow = "▲" if self._history[-1] > self._history[-2] else "▼" if self._history[-1] < self._history[-2] else "–"
        else:
            arrow = "–"
        self.query_one("#movement-log", Static).update(f"Odds movement · {match['value_pick']}: {movements} {arrow}")
