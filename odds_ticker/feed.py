"""Deterministic fixture data with simulated live odds movement."""

from __future__ import annotations

import random
from datetime import datetime, timezone

import polars as pl

from odds_ticker.models import MatchOdds


class MockOddsFeed:
    """Generate sample fixtures and realistic, small odds movements."""

    def __init__(self, seed: int | None = None) -> None:
        self._random = random.Random(seed)
        self._fixtures: list[dict[str, str | float]] = [
            {"match_id": "EPL-001", "home_team": "Arsenal", "away_team": "Liverpool", "league": "Premier League", "home_win": 2.35, "draw": 3.40, "away_win": 2.95, "fair_home": 0.43, "fair_draw": 0.27, "fair_away": 0.30},
            {"match_id": "EPL-002", "home_team": "Manchester City", "away_team": "Aston Villa", "league": "Premier League", "home_win": 1.62, "draw": 4.20, "away_win": 5.10, "fair_home": 0.62, "fair_draw": 0.22, "fair_away": 0.16},
            {"match_id": "UCL-001", "home_team": "Real Madrid", "away_team": "Bayern Munich", "league": "Champions League", "home_win": 2.15, "draw": 3.55, "away_win": 3.20, "fair_home": 0.46, "fair_draw": 0.25, "fair_away": 0.29},
            {"match_id": "UCL-002", "home_team": "Inter", "away_team": "Paris Saint-Germain", "league": "Champions League", "home_win": 2.75, "draw": 3.25, "away_win": 2.55, "fair_home": 0.35, "fair_draw": 0.28, "fair_away": 0.37},
        ]
        self._previous: dict[str, tuple[float, float, float]] = {}

    def fetch_snapshot(self) -> pl.DataFrame:
        """Return an updated snapshot, including edge and movement indicators."""
        now = datetime.now(timezone.utc)
        rows: list[dict[str, object]] = []
        for fixture in self._fixtures:
            old = (float(fixture["home_win"]), float(fixture["draw"]), float(fixture["away_win"]))
            for key in ("home_win", "draw", "away_win"):
                movement = self._random.uniform(-0.035, 0.035)
                fixture[key] = round(max(1.01, float(fixture[key]) + movement), 2)
            current = (float(fixture["home_win"]), float(fixture["draw"]), float(fixture["away_win"]))
            implied = tuple(1 / price for price in current)
            overround = sum(implied)
            fair = (float(fixture["fair_home"]), float(fixture["fair_draw"]), float(fixture["fair_away"]))
            edges = tuple((fair[i] - implied[i] / overround) * 100 for i in range(3))
            best_index = max(range(3), key=edges.__getitem__)
            edge = edges[best_index]
            previous = self._previous.get(str(fixture["match_id"]), old)
            trends = tuple("▲" if current[i] > previous[i] else "▼" if current[i] < previous[i] else "–" for i in range(3))
            self._previous[str(fixture["match_id"])] = current
            row = {key: fixture[key] for key in ("match_id", "home_team", "away_team", "league", "home_win", "draw", "away_win")}
            row.update({"value_edge": round(edge, 2), "value_pick": ("Home", "Draw", "Away")[best_index], "value_probability": fair[best_index], "timestamp": now, "home_trend": trends[0], "draw_trend": trends[1], "away_trend": trends[2]})
            # Validate the core record at the feed boundary.
            MatchOdds.model_validate({**row, "timestamp": now})
            rows.append(row)
        return pl.DataFrame(rows)
