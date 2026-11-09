"""Tests for odds probability and staking calculations."""

import unittest

from odds_ticker.analytics import (
    calculate_fractional_kelly,
    calculate_implied_probability,
    calculate_overround,
)


class AnalyticsTests(unittest.TestCase):
    def test_implied_probability(self) -> None:
        self.assertAlmostEqual(calculate_implied_probability(2.0), 0.5)

    def test_overround_is_percentage_margin(self) -> None:
        # The three implied probabilities total 105%; the vig is 5%.
        self.assertAlmostEqual(calculate_overround(2.0, 4.0, 3.3333333333333335), 5.0)

    def test_fractional_kelly_stake(self) -> None:
        # At 2.0 odds and 60% probability, full Kelly is 20%; quarter Kelly is 5%.
        self.assertAlmostEqual(calculate_fractional_kelly(2.0, 0.6, bankroll=1000.0), 50.0)

    def test_fractional_kelly_never_suggests_a_lay_stake(self) -> None:
        self.assertEqual(calculate_fractional_kelly(2.0, 0.4, bankroll=1000.0), 0.0)


if __name__ == "__main__":
    unittest.main()
