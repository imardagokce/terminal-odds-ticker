"""Custom Textual widgets for fixture inspection and league selection."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import Button, Checkbox, Input, Sparkline, Static

from odds_ticker.analytics import calculate_fractional_kelly, calculate_implied_probability, calculate_overround
from odds_ticker.fetcher import SPORTS


DEFAULT_LEAGUES = tuple(SPORTS.values())


class ApiKeyModal(ModalScreen[str | None]):
    """Collect an optional Odds API key during first run."""

    def compose(self) -> ComposeResult:
        with Vertical(id="api-key-modal"):
            yield Static("Enter your The Odds API Key (Leave blank for Mock Mode):", classes="modal-title")
            yield Input(placeholder="The Odds API key", password=True, id="api-key-input")
            with Horizontal():
                yield Button("Save & Continue", variant="primary", id="save-api-key")
                yield Button("Use Mock Mode", id="use-mock")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-api-key":
            self.dismiss(self.query_one("#api-key-input", Input).value.strip())
        elif event.button.id == "use-mock":
            self.dismiss("")


class LeagueFilterModal(ModalScreen[set[str] | None]):
    """Choose which leagues appear in the market tables."""

    BINDINGS = [("escape", "cancel", "Cancel"), ("l", "cancel", "Close")]

    def __init__(self, leagues: list[str], selected: set[str]) -> None:
        super().__init__()
        self.leagues = sorted(set(leagues) or DEFAULT_LEAGUES)
        self.selected = set(selected) if selected else set(self.leagues)

    def compose(self) -> ComposeResult:
        with Vertical(id="league-modal"):
            yield Static("SELECT LEAGUES", classes="modal-title")
            with VerticalScroll(id="league-options"):
                for index, league in enumerate(self.leagues):
                    yield Checkbox(league, value=league in self.selected, id=f"league-{index}")
            with Horizontal(id="league-footer"):
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
            self.action_cancel()

    def action_cancel(self) -> None:
        """Close the dialog without applying changes."""
        self.dismiss(None)


class SortSelectionModal(ModalScreen[str | None]):
    """Choose the active fixture sorting mode."""

    BINDINGS = [("escape", "cancel", "Cancel"), ("s", "cancel", "Cancel")]
    SORT_OPTIONS = (
        ("value_edge", "Value Edge ↓  ·  Highest value edge percentage"),
        ("win_probability", "Win Probability ↓  ·  Highest implied win probability"),
        ("kickoff_time", "⏰ Kickoff Time ↑  ·  Chronological order"),
        ("odds", "Decimal Odds ↑  ·  Ascending odds"),
    )

    def __init__(self, current_sort: str) -> None:
        super().__init__()
        self.current_sort = current_sort

    def compose(self) -> ComposeResult:
        with Vertical(id="sort-modal"):
            yield Static("SELECT SORT MODE", classes="modal-title")
            for sort_key, label in self.SORT_OPTIONS:
                yield Button(
                    label,
                    variant="primary" if sort_key == self.current_sort else "default",
                    id=f"sort-{sort_key}",
                )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        sort_key = str(event.button.id or "").removeprefix("sort-")
        if sort_key in {key for key, _ in self.SORT_OPTIONS}:
            self.dismiss(sort_key)

    def action_cancel(self) -> None:
        """Close the chooser without changing the active sort."""
        self.dismiss(None)


class BankrollModal(ModalScreen[float | None]):
    """Edit the bankroll used for stake guidance."""

    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, bankroll: float) -> None:
        super().__init__()
        self.bankroll = bankroll

    def compose(self) -> ComposeResult:
        with Vertical(id="bankroll-modal"):
            yield Static("SET BANKROLL", classes="modal-title")
            yield Input(value=f"{self.bankroll:.2f}", placeholder="Bankroll amount", type="number", id="bankroll-modal-input")
            with Horizontal():
                yield Button("Save", variant="primary", id="save-bankroll")
                yield Button("Cancel", id="cancel-bankroll")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-bankroll":
            try:
                value = float(self.query_one("#bankroll-modal-input", Input).value)
            except ValueError:
                self.query_one("#bankroll-modal-input", Input).focus()
                return
            if value >= 0:
                self.dismiss(value)
        elif event.button.id == "cancel-bankroll":
            self.dismiss(None)

    def action_cancel(self) -> None:
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
            yield Static("", id="bet-recommendation")
            yield Static("", id="risk-profile")
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

    def clear_match(self) -> None:
        """Clear stale fixture details when the active filters match nothing."""
        self._match = None
        if self.is_mounted:
            self.query_one("#detail-content", Static).update("No fixtures match the active filters.")
            recommendation = self.query_one("#bet-recommendation", Static)
            recommendation.update("NO VALUE DETECTED (PASS)")
            recommendation.set_class(True, "pass")
            self.query_one("#risk-profile", Static).update("")

    def set_bankroll(self, bankroll: float) -> None:
        """Set bankroll and refresh the recommendation."""
        self._bankroll = bankroll
        self._render_match()

    def _render_match(self) -> None:
        if self._match is None or not self.is_mounted:
            return
        match = self._match
        market = str(match.get("value_market", "1X2"))
        try:
            bankroll = float(getattr(self, "_bankroll", 1000.0))
            stake = calculate_fractional_kelly(float(match["value_odds"]), float(match["value_probability"]), self._fraction, bankroll)
            stake_text = f"₺{stake:,.2f} ({stake / bankroll:.1%} Bankroll)" if bankroll > 0 else "₺0.00 (0.0% Bankroll)"
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
                   f"Value edge  {edge:+.2f}% · {match['value_pick']}\n\n"
                   f"Updated {match['timestamp'].strftime('%H:%M:%S UTC')}")
        self.query_one("#detail-content", Static).update(content)
        recommendation = self.query_one("#bet-recommendation", Static)
        risk_profile = self.query_one("#risk-profile", Static)
        win_probability = calculate_implied_probability(float(match["value_odds"]))
        loss_risk = 1.0 - win_probability
        risk_text = Text()
        risk_text.append(f"WIN PROBABILITY: {win_probability:.1%}\n", style="bold green")
        risk_text.append(f"LOSS RISK: {loss_risk:.1%}", style="bold red")
        if edge > 0:
            recommendation.update(f"RECOMMENDED BET: {match['value_pick']} @ {float(match['value_odds']):.2f}\nSTAKE AMOUNT: {stake_text}")
            recommendation.set_class(True, "recommended")
            risk_level = "LOW RISK" if win_probability > 0.70 else "MEDIUM RISK" if win_probability >= 0.50 else "HIGH RISK / HIGH VALUE"
            risk_text.append(f"\n{risk_level}", style="bold yellow")
        else:
            recommendation.update("NO VALUE DETECTED (PASS)")
            recommendation.set_class(True, "pass")
        risk_profile.update(risk_text)
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
