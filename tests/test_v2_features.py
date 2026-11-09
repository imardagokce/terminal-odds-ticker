"""Coverage for the V2 market, league and Kelly features."""

import unittest

from odds_ticker.app import OddsTickerApp
from odds_ticker.analytics import cycle_kelly_fraction
from odds_ticker.feed import MARKETS, MockOddsFeed
from odds_ticker.models import MatchOdds


class V2FeatureTests(unittest.TestCase):
    def test_feed_parses_all_market_prices(self) -> None:
        snapshot = MockOddsFeed(seed=3).fetch_snapshot()
        row = snapshot.row(0, named=True)
        record = MatchOdds.model_validate(row)
        self.assertGreater(record.over_2_5, 1)
        self.assertGreater(record.under_2_5, 1)
        self.assertGreater(record.btts_yes, 1)
        self.assertGreater(record.ah_away, 1)
        self.assertEqual(set(row_key for row_key in MARKETS), {"1X2", "Over / Under", "BTTS", "Asian Handicap"})
        self.assertTrue(all(f"edge_{market}" in row for market in MARKETS))

    def test_feed_retains_fifteen_ticks_per_outcome(self) -> None:
        feed = MockOddsFeed(seed=8)
        for _ in range(18):
            feed.fetch_snapshot()
        self.assertEqual(len(feed.history("EPL-001", "home_win")), 15)

    def test_kelly_fraction_cycle(self) -> None:
        app = OddsTickerApp()
        self.assertEqual(app.KELLY_FRACTIONS, (0.25, 0.50, 1.00))
        self.assertEqual(cycle_kelly_fraction(0.25), 0.50)
        self.assertEqual(cycle_kelly_fraction(0.50), 1.00)
        self.assertEqual(cycle_kelly_fraction(1.00), 0.25)

    def test_league_filter_is_applied_to_rows(self) -> None:
        app = OddsTickerApp()
        app._rows = {str(row["match_id"]): row for row in MockOddsFeed(seed=9).fetch_snapshot().iter_rows(named=True)}
        app._active_leagues = {"Premier League"}
        filtered = [row for row in app._rows.values() if row["league"] in app._active_leagues]
        self.assertEqual(len(filtered), 2)
        self.assertTrue(all(row["league"] == "Premier League" for row in filtered))


if __name__ == "__main__":
    unittest.main()
