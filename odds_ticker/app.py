"""Textual interface for the terminal odds ticker."""

from __future__ import annotations

from typing import Any

from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Static

from odds_ticker.feed import MockOddsFeed
from odds_ticker.widgets import MatchDetailView


class OddsTickerApp(App[None]):
    """Browse simulated football odds and value edges."""

    TITLE = "Odds Ticker"
    SUB_TITLE = "Live football markets · mock feed"
    CSS_PATH = "styles.tcss"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("s", "cycle_sort", "Sort"),
        ("f", "cycle_filter", "League"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.feed = MockOddsFeed()
        self._rows: dict[str, dict[str, Any]] = {}
        self._sort_mode = 0
        self._league_filter: str | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="layout"):
            with Vertical(id="markets"):
                yield Static("MATCH MARKETS · s SORT · f LEAGUE", id="market-title")
                yield DataTable(id="table", cursor_type="row", zebra_stripes=True)
            with Vertical(id="details"):
                yield Static("MATCH INSPECTOR", id="detail-title")
                yield MatchDetailView(id="match-detail")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("League", "Fixture", "Home", "Draw", "Away", "Edge")
        table.cursor_type = "row"
        self.refresh_snapshot()
        self.set_interval(3, self.refresh_snapshot)

    def on_resize(self, event: events.Resize) -> None:
        """Stack the panels when the terminal is too narrow for columns."""
        layout = self.query_one("#layout", Horizontal)
        layout.set_class(event.size.width < 100, "compact")

    def action_refresh(self) -> None:
        """Fetch a fresh market snapshot."""
        self.refresh_snapshot()

    def action_cycle_sort(self) -> None:
        """Cycle through edge, home price and league sort orders."""
        self._sort_mode = (self._sort_mode + 1) % 3
        self._render_table()

    def action_cycle_filter(self) -> None:
        """Cycle through all leagues and each league filter."""
        leagues = sorted({str(row["league"]) for row in self._rows.values()})
        options: list[str | None] = [None, *leagues]
        current_index = options.index(self._league_filter) if self._league_filter in options else 0
        self._league_filter = options[(current_index + 1) % len(options)]
        self._render_table()

    def refresh_snapshot(self) -> None:
        """Update the cached snapshot and repaint the filtered table."""
        snapshot = self.feed.fetch_snapshot()
        self._rows = {str(row["match_id"]): row for row in snapshot.iter_rows(named=True)}
        self._render_table()

    def _render_table(self) -> None:
        table = self.query_one(DataTable)
        rows = list(self._rows.values())
        if self._league_filter is not None:
            rows = [row for row in rows if row["league"] == self._league_filter]
        sort_keys = (
            lambda row: -float(row["value_edge"]),
            lambda row: float(row["home_win"]),
            lambda row: str(row["league"]),
        )
        rows.sort(key=sort_keys[self._sort_mode])
        table.clear()
        for row in rows:
            edge = float(row["value_edge"])
            fixture = Text(f"{row['home_team']} v {row['away_team']}")
            edge_colour = "#00ff87" if edge > 5 else "#ffb86c" if edge >= 0 else "#8b5a62"
            edge_cell = Text(f"{edge:+.1f}%", style=f"bold {edge_colour}")
            prices = (
                f"{row['home_trend']} {row['home_win']:.2f}",
                f"{row['draw_trend']} {row['draw']:.2f}",
                f"{row['away_trend']} {row['away_win']:.2f}",
            )
            table.add_row(str(row["league"]), fixture, *prices, edge_cell, key=str(row["match_id"]))
        sort_names = ("Value edge ↓", "Home odds ↑", "League A–Z")
        filter_name = self._league_filter or "All leagues"
        self.query_one("#market-title", Static).update(
            f"MATCH MARKETS · {sort_names[self._sort_mode]} · {filter_name} · s SORT · f LEAGUE"
        )
        if rows:
            table.move_cursor(row=0)
            self.query_one(MatchDetailView).set_match(rows[0])

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Update the inspector as the table cursor moves."""
        self._show_highlighted_row(event)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Update the inspector when a fixture is activated."""
        self._show_highlighted_row(event)

    def _show_highlighted_row(self, event: DataTable.RowHighlighted | DataTable.RowSelected) -> None:
        row = self._rows.get(str(event.row_key.value))
        if row is not None:
            self.query_one(MatchDetailView).set_match(row)


def main() -> None:
    """Run the Odds Ticker application."""
    OddsTickerApp().run()


if __name__ == "__main__":
    main()
