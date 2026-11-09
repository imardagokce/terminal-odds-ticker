"""Tests for the mock odds feed and its validated records."""

import unittest
from datetime import datetime

import polars as pl

from odds_ticker.feed import MockOddsFeed
from odds_ticker.models import MatchOdds


class MockOddsFeedTests(unittest.TestCase):
    def test_snapshot_contains_valid_fixture_data(self) -> None:
        snapshot = MockOddsFeed(seed=7).fetch_snapshot()
        self.assertIsInstance(snapshot, pl.DataFrame)
        self.assertEqual(snapshot.height, 4)
        self.assertTrue({"home_trend", "draw_trend", "away_trend", "value_edge"}.issubset(snapshot.columns))
        record = MatchOdds.model_validate(snapshot.row(0, named=True))
        self.assertIsInstance(record.timestamp, datetime)
        self.assertGreater(record.home_win, 1)

    def test_snapshot_prices_move_on_subsequent_ticks(self) -> None:
        feed = MockOddsFeed(seed=19)
        first = feed.fetch_snapshot()
        second = feed.fetch_snapshot()
        self.assertNotEqual(first["home_win"].to_list(), second["home_win"].to_list())


if __name__ == "__main__":
    unittest.main()
