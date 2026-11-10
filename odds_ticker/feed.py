"""Deterministic fixture data with simulated live odds movement."""

from __future__ import annotations

import random
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
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
        fixtures = [
            ("TUR", "Galatasaray", "Fenerbahçe", "Trendyol Süper Lig", (2.05, 3.45, 3.35)),
            ("TUR", "Beşiktaş", "Trabzonspor", "Trendyol Süper Lig", (2.10, 3.35, 3.25)),
            ("EPL", "Arsenal", "Liverpool", "Premier League", (2.35, 3.40, 2.95)),
            ("EPL", "Manchester City", "Aston Villa", "Premier League", (1.62, 4.20, 5.10)),
            ("EPL", "Chelsea", "Tottenham", "Premier League", (2.05, 3.65, 3.25)),
            ("UCL", "Real Madrid", "Bayern Munich", "Champions League", (2.15, 3.55, 3.20)),
            ("UCL", "Inter", "Paris Saint-Germain", "Champions League", (2.75, 3.25, 2.55)),
            ("GER", "Bayern Munich", "Dortmund", "Bundesliga", (1.72, 4.10, 4.35)),
            ("GER", "Bayer Leverkusen", "RB Leipzig", "Bundesliga", (1.95, 3.60, 3.60)),
            ("ESP", "Real Madrid", "Barcelona", "La Liga", (2.15, 3.50, 3.25)),
            ("ESP", "Atletico Madrid", "Sevilla", "La Liga", (1.80, 3.55, 4.70)),
            ("ITA", "Juventus", "AC Milan", "Serie A", (2.30, 3.10, 3.35)),
            ("FRA", "PSG", "Marseille", "Ligue 1", (1.55, 4.30, 5.80)),
            ("NED", "Ajax", "PSV", "Eredivisie", (2.55, 3.80, 2.35)),
            ("POR", "Benfica", "Porto", "Primeira Liga", (2.00, 3.35, 3.70)),
        ]
        now = datetime.now(timezone.utc)
        self._fixtures: list[dict[str, Any]] = []
        for index, (prefix, home, away, league, result_odds) in enumerate(fixtures):
            odds: dict[str, float] = {
                "home_win": result_odds[0], "draw": result_odds[1], "away_win": result_odds[2],
                "over_2_5": 1.65 + (index % 5) * .08, "under_2_5": 2.30 - (index % 4) * .07,
                "btts_yes": 1.62 + (index % 4) * .09, "btts_no": 2.25 - (index % 5) * .08,
                "ah_home": 1.72 + (index % 5) * .07, "ah_away": 2.16 - (index % 4) * .06,
            }
            fixture: dict[str, Any] = {
                "match_id": (f"EPL-{('Arsenal', 'Manchester City', 'Chelsea').index(home) + 1:03d}"
                             if home in {"Arsenal", "Manchester City", "Chelsea"} else f"{prefix}-{index + 1:03d}"),
                "home_team": home, "away_team": away,
                "league": league, "commence_time": now + timedelta(days=index + 1, hours=index % 8), **odds,
            }
            for keys, _ in MARKETS.values():
                implied = [1 / odds[key] for key in keys]
                total = sum(implied)
                for key, probability in zip(keys, implied):
                    fixture[FAIR_KEYS.get(key, f"fair_{key}")] = probability / total
            self._fixtures.append(fixture)
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
