"""Textual interface for the terminal odds ticker."""

from __future__ import annotations

import os
from typing import Any

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Input, Static, TabbedContent, TabPane

from odds_ticker.analytics import KELLY_FRACTIONS, calculate_fractional_kelly, cycle_kelly_fraction
from odds_ticker.config import load_config, save_api_key
from odds_ticker.feed import FAIR_KEYS, MARKETS, MockOddsFeed
from odds_ticker.fetcher import LiveOddsFeed
from odds_ticker.widgets import ApiKeyModal, LeagueFilterModal, MatchDetailView


class OddsTickerApp(App[None]):
    """Browse football odds and value edges."""

    TITLE = "Odds Ticker"
    SUB_TITLE = "Live football markets"
    CSS_PATH = "styles.tcss"
    BINDINGS = [("q", "quit", "Quit"), ("r", "refresh", "Refresh"), ("s", "cycle_sort", "Sort"), ("l", "select_leagues", "Leagues"), ("k", "cycle_kelly", "Kelly")]
    MARKET_IDS = {"tab-1x2": "1X2", "tab-ou": "Over / Under", "tab-btts": "BTTS", "tab-ah": "Asian Handicap"}
    KELLY_FRACTIONS = KELLY_FRACTIONS

    def __init__(self) -> None:
        super().__init__()
        api_key = os.getenv("ODDS_API_KEY") or str(load_config().get("api_key", "")).strip()
        self._api_key = api_key
        self.feed = LiveOddsFeed(api_key) if api_key else MockOddsFeed()
        self.feed_indicator = "[LIVE API]" if api_key else "[MOCK FEED]"
        self._refresh_timer_started = False
        self._rows: dict[str, dict[str, Any]] = {}
        self._sort_mode = 0
        self._active_leagues: set[str] | None = None
        self._kelly_index = 0

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="layout"):
            with Vertical(id="markets"):
                yield Static("MATCH MARKETS", id="market-title")
                with TabbedContent(initial="tab-1x2", id="market-tabs"):
                    for tab_id, market in self.MARKET_IDS.items():
                        with TabPane(market, id=tab_id):
                            yield DataTable(id=f"table-{tab_id}", cursor_type="row", zebra_stripes=True)
            with Vertical(id="details"):
                yield Static("MATCH INSPECTOR", id="detail-title")
                yield MatchDetailView(id="match-detail", history_provider=self.feed.history)
        yield Static("", id="exposure-warning")
        yield Footer()

    def on_mount(self) -> None:
        self.sub_title = f"{self.feed_indicator} · Live football markets"
        for table in self.query(DataTable):
            table.add_columns("League", "Fixture", "Selection 1", "Selection 2", "Selection 3", "Edge")
        if not self._api_key:
            self.push_screen(ApiKeyModal(), self._on_api_key_choice)
            return
        self._start_feed()

    def _on_api_key_choice(self, api_key: str | None) -> None:
        """Apply the selected live or mock feed after onboarding."""
        if api_key:
            save_api_key(api_key)
            self._api_key = api_key
            self.feed = LiveOddsFeed(api_key)
            self.feed_indicator = "[LIVE API]"
        else:
            self._api_key = ""
            self.feed = MockOddsFeed()
            self.feed_indicator = "[MOCK FEED]"
        self.sub_title = f"{self.feed_indicator} · Live football markets"
        self.query_one(MatchDetailView)._history_provider = self.feed.history
        self._start_feed()

    def _start_feed(self) -> None:
        """Populate the dashboard and schedule regular refreshes once."""
        self.refresh_snapshot()
        if not self._refresh_timer_started:
            self.set_interval(3, self.refresh_snapshot)
            self._refresh_timer_started = True

    def action_refresh(self) -> None:
        """Fetch and display a fresh market snapshot."""
        self.refresh_snapshot()

    def action_cycle_sort(self) -> None:
        """Cycle value edge, first outcome price and league sorting."""
        self._sort_mode = (self._sort_mode + 1) % 3
        self._render_tables()

    def action_cycle_kelly(self) -> None:
        """Cycle quarter, half and full Kelly stake guidance."""
        next_fraction = cycle_kelly_fraction(self.KELLY_FRACTIONS[self._kelly_index])
        self._kelly_index = self.KELLY_FRACTIONS.index(next_fraction)
        self.query_one(MatchDetailView).set_kelly_fraction(self.KELLY_FRACTIONS[self._kelly_index])
        self._render_exposure()

    def action_select_leagues(self) -> None:
        """Open the league filter chooser."""
        leagues = sorted({str(row["league"]) for row in self._rows.values()})
        selected = set(leagues) if self._active_leagues is None else self._active_leagues
        self.push_screen(LeagueFilterModal(leagues, selected), self._set_leagues)

    def _set_leagues(self, selected: set[str] | None) -> None:
        if selected is not None:
            leagues = {str(row["league"]) for row in self._rows.values()}
            self._active_leagues = None if selected == leagues else selected
            self._render_tables()

    def refresh_snapshot(self) -> None:
        """Update cached fixtures, all market tables and exposure guidance."""
        snapshot = self.feed.fetch_snapshot()
        self._rows = {str(row["match_id"]): row for row in snapshot.iter_rows(named=True)}
        if self._active_leagues is not None:
            self._active_leagues.intersection_update(str(row["league"]) for row in self._rows.values())
        self._render_tables()

    def _render_tables(self) -> None:
        rows = list(self._rows.values())
        if self._active_leagues is not None:
            rows = [row for row in rows if row["league"] in self._active_leagues]
        sort_keys = (lambda row: -float(row["value_edge"]), lambda row: float(row["home_win"]), lambda row: str(row["league"]))
        rows.sort(key=sort_keys[self._sort_mode])
        for tab_id, market in self.MARKET_IDS.items():
            table = self.query_one(f"#table-{tab_id}", DataTable)
            table.clear()
            keys, labels = MARKETS[market]
            table.clear(columns=True)
            table.add_columns("League", "Fixture", *labels, "Edge")
            for row in rows:
                prices = [float(row[key]) for key in keys]
                edge = float(row[f"edge_{market}"])
                colour = "#00ff87" if edge > 5 else "#ffb86c" if edge >= 0 else "#8b5a62"
                table.add_row(str(row["league"]), Text(f"{row['home_team']} v {row['away_team']}"), *(f"{price:.2f}" for price in prices), Text(f"{edge:+.1f}%", style=f"bold {colour}"), key=str(row["match_id"]))
        active = self.query_one("#market-tabs", TabbedContent).active
        market = self.MARKET_IDS.get(str(active), "1X2")
        self.query_one("#market-title", Static).update(f"{market.upper()} · {'Value edge ↓' if self._sort_mode == 0 else 'Odds ↑' if self._sort_mode == 1 else 'League A–Z'} · {len(rows)} fixtures · l LEAGUES · k {self.KELLY_FRACTIONS[self._kelly_index]:.0%} KELLY")
        if rows:
            self.query_one(f"#table-{active}", DataTable).move_cursor(row=0)
            self.query_one(MatchDetailView).set_match(self._market_row(rows[0], market))
        self._render_exposure()

    def _market_row(self, row: dict[str, Any], market: str) -> dict[str, Any]:
        keys, labels = MARKETS[market]
        result = dict(row)
        edge = float(row[f"edge_{market}"])
        probabilities = [float(row[FAIR_KEYS.get(key, f"fair_{key}")]) for key in keys]
        best = max(range(len(keys)), key=lambda index: (probabilities[index] - 1 / float(row[keys[index]])) * 100)
        result.update({"value_market": market, "value_pick": labels[best], "value_odds": float(row[keys[best]]), "value_probability": probabilities[best], "value_edge": edge})
        return result

    def _render_exposure(self) -> None:
        if not self.is_mounted:
            return
        try:
            bankroll = float(self.query_one("#bankroll", Input).value)
        except (ValueError, TypeError):
            return
        exposure = sum(calculate_fractional_kelly(float(row["value_odds"]), float(row["value_probability"]), self.KELLY_FRACTIONS[self._kelly_index], bankroll) for row in self._rows.values() if float(row["value_edge"]) > 0)
        badge = self.query_one("#exposure-warning", Static)
        badge.update(f"⚠ Recommended exposure {exposure / bankroll:.1%} exceeds 15% of bankroll" if bankroll > 0 and exposure / bankroll > .15 else "")

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        """Show the highlighted fixture for the newly selected market."""
        market = self.MARKET_IDS.get(str(event.pane.id), "1X2")
        rows = list(self._rows.values())
        if self._active_leagues is not None:
            rows = [row for row in rows if row["league"] in self._active_leagues]
        if rows:
            self.query_one(MatchDetailView).set_match(self._market_row(rows[0], market))
        self._render_tables()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Update the inspector as the fixture selection moves."""
        self._show_row(event)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Update the inspector when a fixture is selected."""
        self._show_row(event)

    def _show_row(self, event: DataTable.RowHighlighted | DataTable.RowSelected) -> None:
        row = self._rows.get(str(event.row_key.value))
        market = self.MARKET_IDS.get(str(self.query_one("#market-tabs", TabbedContent).active), "1X2")
        if row is not None:
            self.query_one(MatchDetailView).set_match(self._market_row(row, market))


def main() -> None:
    """Run the Odds Ticker application."""
    OddsTickerApp().run()


if __name__ == "__main__":
    main()
