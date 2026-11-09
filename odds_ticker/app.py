"""Textual interface for the terminal odds ticker."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Header, Static
from rich.text import Text

from odds_ticker.feed import MockOddsFeed


class OddsTickerApp(App[None]):
    """Browse simulated football odds and value edges."""

    TITLE = "Odds Ticker"
    SUB_TITLE = "Live football markets · mock feed"
    CSS = """
    Screen { background: #10151b; color: #e6edf3; }
    #layout { height: 1fr; padding: 1 2; }
    #markets { width: 3fr; border: round #344454; padding: 0 1; }
    #details { width: 2fr; border: round #344454; padding: 1 2; margin-left: 1; }
    #market-title, #detail-title { text-style: bold; color: #7dd3fc; padding-bottom: 1; }
    #detail-body { height: 1fr; }
    DataTable { height: 1fr; }
    """
    BINDINGS = [("q", "quit", "Quit"), ("r", "refresh", "Refresh")]

    def __init__(self) -> None:
        super().__init__()
        self.feed = MockOddsFeed()
        self._rows: dict[str, dict[str, object]] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="layout"):
            with Vertical(id="markets"):
                yield Static("MATCH MARKETS", id="market-title")
                yield DataTable(id="table", cursor_type="row", zebra_stripes=True)
            with Vertical(id="details"):
                yield Static("SELECTED FIXTURE", id="detail-title")
                yield Static("Select a fixture to inspect its odds and Kelly estimate.", id="detail-body")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("League", "Fixture", "Home", "Draw", "Away", "Edge")
        table.cursor_type = "row"
        self.refresh_snapshot()
        self.set_interval(3, self.refresh_snapshot)

    def action_refresh(self) -> None:
        self.refresh_snapshot()

    def refresh_snapshot(self) -> None:
        snapshot = self.feed.fetch_snapshot()
        table = self.query_one(DataTable)
        table.clear()
        self._rows.clear()
        for row in snapshot.iter_rows(named=True):
            match_id = str(row["match_id"])
            self._rows[match_id] = row
            edge = float(row["value_edge"])
            fixture = f"{row['home_team']} v {row['away_team']}"
            prices = f"{row['home_trend']} {row['home_win']:.2f}", f"{row['draw_trend']} {row['draw']:.2f}", f"{row['away_trend']} {row['away_win']:.2f}"
            fixture_cell = Text(fixture, style="bold green" if edge >= 5 else "")
            edge_cell = Text(f"{edge:+.1f}%", style="bold green" if edge >= 5 else "")
            table.add_row(str(row["league"]), fixture_cell, *prices, edge_cell, key=match_id)
        if table.row_count:
            table.move_cursor(row=0)
            self.update_details()

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self.update_details()

    def update_details(self) -> None:
        table = self.query_one(DataTable)
        if not table.row_count:
            return
        match_id = list(self._rows)[table.cursor_row]
        row = self._rows.get(match_id)
        if row is None:
            return
        odds_by_pick = {"Home": float(row["home_win"]), "Draw": float(row["draw"]), "Away": float(row["away_win"])}
        best_odds = odds_by_pick[str(row["value_pick"])]
        probability = float(row["value_probability"])
        kelly = max(0.0, (best_odds * probability - 1) / (best_odds - 1))
        text = (
            f"[bold]{row['home_team']} v {row['away_team']}[/bold]\n"
            f"{row['league']}\n\n"
            f"Home win   {row['home_win']:.2f}\nDraw       {row['draw']:.2f}\nAway win   {row['away_win']:.2f}\n\n"
            f"Value edge  [green]{float(row['value_edge']):+.2f}%[/green]\n"
            f"Value pick   {row['value_pick']}\n"
            f"Kelly guide {kelly:.2%} of bankroll\n\n"
            f"Updated {row['timestamp'].strftime('%H:%M:%S UTC')}"
        )
        self.query_one("#detail-body", Static).update(text)


def main() -> None:
    """Run the Odds Ticker application."""
    OddsTickerApp().run()


if __name__ == "__main__":
    main()
