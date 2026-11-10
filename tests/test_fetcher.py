"""Tests for normalising The Odds API responses."""

import unittest
from unittest.mock import patch

import httpx
import polars as pl

from odds_ticker.fetcher import LiveOddsFeed, SPORTS
from odds_ticker.feed import MockOddsFeed
from odds_ticker.models import MatchOdds


PAYLOAD = [{
    "id": "fixture-1",
    "home_team": "Galatasaray",
    "away_team": "Fenerbahce",
    "bookmakers": [{"key": "test", "markets": [
        {"key": "h2h", "outcomes": [
            {"name": "Galatasaray", "price": 2.1}, {"name": "Draw", "price": 3.2}, {"name": "Fenerbahce", "price": 3.4},
        ]},
        {"key": "totals", "outcomes": [
            {"name": "Over", "point": 2.5, "price": 1.8}, {"name": "Under", "point": 2.5, "price": 2.0},
        ]},
        {"key": "btts", "outcomes": [{"name": "Yes", "price": 1.7}, {"name": "No", "price": 2.1}]},
        {"key": "spreads", "outcomes": [
            {"name": "Galatasaray", "point": -0.5, "price": 1.9}, {"name": "Fenerbahce", "point": 0.5, "price": 1.95},
        ]},
    ]}],
}]


class LiveOddsFeedTests(unittest.TestCase):
    def test_parse_event_normalises_all_markets(self) -> None:
        feed = LiveOddsFeed("test-key", client=httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=PAYLOAD))))
        row = feed._parse_event(PAYLOAD[0], "Trendyol Süper Lig")
        record = MatchOdds.model_validate(row)
        self.assertEqual(record.match_id, "fixture-1")
        self.assertEqual(record.league, "Trendyol Süper Lig")
        self.assertEqual(record.home_win, 2.1)
        self.assertEqual(record.over_2_5, 1.8)
        self.assertEqual(record.btts_yes, 1.7)
        self.assertEqual(record.ah_away, 1.95)
        self.assertTrue(all(f"edge_{name}" in row for name in ("1X2", "Over / Under", "BTTS", "Asian Handicap")))
        self.assertEqual(feed.history("fixture-1", "home_win"), [2.1])

    def test_fetch_snapshot_uses_http_and_caches_response(self) -> None:
        calls = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request)
            return httpx.Response(200, json=PAYLOAD)

        client = httpx.Client(transport=httpx.MockTransport(handler))
        feed = LiveOddsFeed("test-key", client=client, ttl=60)
        first = feed.fetch_snapshot()
        second = feed.fetch_snapshot()
        self.assertIsInstance(first, pl.DataFrame)
        self.assertEqual(first.height, len(SPORTS))
        self.assertEqual(second.height, first.height)
        self.assertEqual(len(calls), len(SPORTS))
        self.assertEqual(calls[0].url.params["markets"], "h2h,totals,btts,spreads")
        client.close()

    def test_app_falls_back_to_mock_feed_when_api_errors(self) -> None:
        from odds_ticker.app import OddsTickerApp

        client = httpx.Client(transport=httpx.MockTransport(
            lambda request: httpx.Response(403, text="invalid API key")
        ))
        with patch.dict("os.environ", {"ODDS_API_KEY": "test-key"}):
            app = OddsTickerApp()
        app.feed.close()
        app.feed = LiveOddsFeed("test-key", client=client)

        async def exercise_app() -> None:
            async with app.run_test() as pilot:
                await pilot.pause()
                self.assertIsInstance(app.feed, MockOddsFeed)
                self.assertGreater(len(app._rows), 0)
                self.assertEqual(app.feed_indicator, "[MOCK FEED]")

        import asyncio
        asyncio.run(exercise_app())
        client.close()


if __name__ == "__main__":
    unittest.main()
