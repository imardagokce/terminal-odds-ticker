"""Deterministic fixture data with simulated live odds movement."""

from __future__ import annotations

import random
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any

import polars as pl

from odds_ticker.models import MatchOdds

MARKETS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "1X2": (("home_win", "draw", "away_win"), ("Home", "Draw", "Away")),
    "Over / Under": (("over_2_5", "under_2_5"), ("Over 2.5", "Under 2.5")),
    "BTTS": (("btts_yes", "btts_no"), ("Yes", "No")),
    "Asian Handicap": (("ah_home", "ah_away"), ("Home -0.5", "Away +0.5")),
}
FAIR_KEYS = {"home_win": "fair_home", "draw": "fair_draw", "away_win": "fair_away"}


class MockOddsFeed:
    """Generate sample fixtures and realistic, small odds movements."""

    def __init__(self, seed: int | None = None) -> None:
        self._random = random.Random(seed)
        self._fixtures: list[dict[str, Any]] = [
            {"match_id": "EPL-001", "home_team": "Arsenal", "away_team": "Liverpool", "league": "Premier League", "home_win": 2.35, "draw": 3.40, "away_win": 2.95, "over_2_5": 1.78, "under_2_5": 2.08, "btts_yes": 1.68, "btts_no": 2.18, "ah_home": 1.92, "ah_away": 1.94, "fair_home": .43, "fair_draw": .27, "fair_away": .30, "fair_over_2_5": .60, "fair_under_2_5": .40, "fair_btts_yes": .61, "fair_btts_no": .39, "fair_ah_home": .53, "fair_ah_away": .47},
            {"match_id": "EPL-002", "home_team": "Manchester City", "away_team": "Aston Villa", "league": "Premier League", "home_win": 1.62, "draw": 4.20, "away_win": 5.10, "over_2_5": 1.62, "under_2_5": 2.35, "btts_yes": 1.72, "btts_no": 2.10, "ah_home": 1.73, "ah_away": 2.12, "fair_home": .62, "fair_draw": .22, "fair_away": .16, "fair_over_2_5": .64, "fair_under_2_5": .36, "fair_btts_yes": .59, "fair_btts_no": .41, "fair_ah_home": .61, "fair_ah_away": .39},
            {"match_id": "UCL-001", "home_team": "Real Madrid", "away_team": "Bayern Munich", "league": "Champions League", "home_win": 2.15, "draw": 3.55, "away_win": 3.20, "over_2_5": 1.82, "under_2_5": 2.02, "btts_yes": 1.70, "btts_no": 2.14, "ah_home": 1.86, "ah_away": 2.00, "fair_home": .46, "fair_draw": .25, "fair_away": .29, "fair_over_2_5": .58, "fair_under_2_5": .42, "fair_btts_yes": .60, "fair_btts_no": .40, "fair_ah_home": .54, "fair_ah_away": .46},
            {"match_id": "UCL-002", "home_team": "Inter", "away_team": "Paris Saint-Germain", "league": "Champions League", "home_win": 2.75, "draw": 3.25, "away_win": 2.55, "over_2_5": 1.95, "under_2_5": 1.88, "btts_yes": 1.75, "btts_no": 2.05, "ah_home": 2.04, "ah_away": 1.82, "fair_home": .35, "fair_draw": .28, "fair_away": .37, "fair_over_2_5": .51, "fair_under_2_5": .49, "fair_btts_yes": .57, "fair_btts_no": .43, "fair_ah_home": .45, "fair_ah_away": .55},
        ]
        self._history: dict[str, dict[str, deque[float]]] = defaultdict(lambda: defaultdict(lambda: deque(maxlen=15)))
        self._previous: dict[str, dict[str, float]] = defaultdict(dict)

    def fetch_snapshot(self) -> pl.DataFrame:
        """Return updated odds, best value estimates and a rolling price history."""
        now = datetime.now(timezone.utc)
        rows: list[dict[str, object]] = []
        for fixture in self._fixtures:
            for odds_key, _ in MARKETS.values():
                for key in odds_key:
                    fixture[key] = round(max(1.01, float(fixture[key]) + self._random.uniform(-.035, .035)), 2)
            edges: dict[str, float] = {}
            picks: dict[str, tuple[str, str, float]] = {}
            for market, (keys, labels) in MARKETS.items():
                prices = [float(fixture[key]) for key in keys]
                for key, price in zip(keys, prices):
                    self._history[str(fixture["match_id"])][key].append(price)
                implied = [1 / price for price in prices]
                margin = sum(implied)
                probabilities = [float(fixture[FAIR_KEYS.get(key, f"fair_{key}")]) for key in keys]
                market_edges = [(probabilities[i] - implied[i] / margin) * 100 for i in range(len(keys))]
                best = max(range(len(keys)), key=market_edges.__getitem__)
                edges[market] = round(market_edges[best], 2)
                picks[market] = (keys[best], labels[best], probabilities[best])
            best_market = max(edges, key=edges.__getitem__)
            best_key, best_label, best_probability = picks[best_market]
            row: dict[str, object] = dict(fixture)
            row.update({f"edge_{market}": edge for market, edge in edges.items()})
            row.update({"value_edge": edges[best_market], "value_market": best_market, "value_pick": best_label, "value_odds": float(fixture[best_key]), "value_probability": best_probability, "timestamp": now})
            row.update({f"history_{key}": list(self._history[str(fixture["match_id"])][key]) for key in self._history[str(fixture["match_id"])]})
            for key in ("home_win", "draw", "away_win"):
                previous = self._previous[str(fixture["match_id"])].get(key, float(fixture[key]))
                row[f"{key.removesuffix('_win')}_trend" if key != "home_win" else "home_trend"] = "▲" if float(fixture[key]) > previous else "▼" if float(fixture[key]) < previous else "–"
                self._previous[str(fixture["match_id"])][key] = float(fixture[key])
            MatchOdds.model_validate({**row, "timestamp": now})
            rows.append(row)
        return pl.DataFrame(rows)

    def history(self, match_id: str, outcome: str) -> list[float]:
        """Return up to fifteen recent prices for a fixture outcome."""
        return list(self._history[match_id][outcome])
