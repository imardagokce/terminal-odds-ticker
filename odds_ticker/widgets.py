"""Custom Textual widgets for fixture inspection and league selection."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, Checkbox, Input, Sparkline, Static

from odds_ticker.analytics import calculate_fractional_kelly, calculate_implied_probability, calculate_overround


class LeagueFilterModal(ModalScreen[set[str] | None]):
    """Choose which leagues appear in the market tables."""

    def __init__(self, leagues: list[str], selected: set[str]) -> None:
        super().__init__()
        self.leagues = leagues
        self.selected = set(selected)

    def compose(self) -> ComposeResult:
        with Vertical(id="league-modal"):
            yield Static("SELECT LEAGUES", classes="modal-title")
            for league in self.leagues:
                yield Checkbox(league, value=league in self.selected, id=f"league-{self.leagues.index(league)}")
            with Horizontal():
                yield Button("All", id="select-all")
                yield Button("None", id="select-none")
                yield Button("Apply", variant="primary", id="apply")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "select-all":
            for checkbox in self.query(Checkbox):
                checkbox.value = True
        elif event.button.id == "select-none":
            for checkbox in self.query(Checkbox):
                checkbox.value = False
        elif event.button.id == "apply":
            self.dismiss({checkbox.label.plain for checkbox in self.query(Checkbox) if checkbox.value})
        elif event.button.id == "cancel":
            self.dismiss(None)


class MatchDetailView(Widget):
    """Show selected fixture odds, movement and fractional Kelly guidance."""

    def __init__(self, *, id: str | None = None, history_provider: Callable[[str, str], list[float]] | None = None) -> None:
        super().__init__(id=id)
        self._match: dict[str, Any] | None = None
        self._fraction = 0.25
        self._history_provider = history_provider

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Select a fixture to inspect its market.", id="detail-content")
            yield Input(value="1000.00", placeholder="Bankroll", id="bankroll", type="number")
            yield Sparkline([], id="movement-sparkline")
            yield Static("Odds movement", id="movement-log")

    def set_kelly_fraction(self, fraction: float) -> None:
        """Set the displayed Kelly fraction and refresh stake guidance."""
        self._fraction = fraction
        self._render_match()

    def set_match(self, match: dict[str, Any]) -> None:
        """Display a fixture and its current market history."""
        self._match = match
        self._render_match()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Recalculate stake guidance when the bankroll changes."""
        if event.input.id == "bankroll":
            self._render_match()

    def _render_match(self) -> None:
        if self._match is None or not self.is_mounted:
            return
        match = self._match
        market = str(match.get("value_market", "1X2"))
        try:
            bankroll = float(self.query_one("#bankroll", Input).value)
            stake = calculate_fractional_kelly(float(match["value_odds"]), float(match["value_probability"]), self._fraction, bankroll)
            stake_text = f"£{stake:,.2f} ({self._fraction:.0%} Kelly)"
        except (ValueError, TypeError, KeyError):
            stake_text = "Enter a valid bankroll"
        prices = (float(match["home_win"]), float(match["draw"]), float(match["away_win"]))
        edge = float(match["value_edge"])
        content = (f"[bold]{match['home_team']} v {match['away_team']}[/bold]\n{match['league']} · {market}\n\n"
                   f"1X2  {prices[0]:.2f}  /  {prices[1]:.2f}  /  {prices[2]:.2f}\n"
                   f"Over / Under 2.5  {match['over_2_5']:.2f}  /  {match['under_2_5']:.2f}\n"
                   f"BTTS Yes / No  {match['btts_yes']:.2f}  /  {match['btts_no']:.2f}\n"
                   f"Asian Handicap  {match['ah_home']:.2f}  /  {match['ah_away']:.2f}\n\n"
                   f"1X2 bookmaker vig  {calculate_overround(*prices):+.2f}%\n"
                   f"Value edge  {edge:+.2f}% · {match['value_pick']}\nSuggested stake  {stake_text}\n\n"
                   f"Updated {match['timestamp'].strftime('%H:%M:%S UTC')}")
        self.query_one("#detail-content", Static).update(content)
        market_keys = {
            "1X2": {"Home": "home_win", "Draw": "draw", "Away": "away_win"}.get(str(match["value_pick"]), "home_win"),
            "Over / Under": "over_2_5" if match["value_pick"] == "Over 2.5" else "under_2_5",
            "BTTS": "btts_yes" if match["value_pick"] == "Yes" else "btts_no",
            "Asian Handicap": "ah_home" if str(match["value_pick"]).startswith("Home") else "ah_away",
        }
        outcome = market_keys.get(market, "home_win")
        history = self._history_provider(str(match["match_id"]), outcome) if self._history_provider else match.get(f"history_{outcome}", [])
        self.query_one("#movement-sparkline", Sparkline).data = history or [float(match.get("value_odds", prices[0]))]
        self.query_one("#movement-log", Static).update(f"Odds trend · {match['value_pick']}")
