"""HTTP client for upcoming football odds from The Odds API."""

from __future__ import annotations

import os
import logging
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any

import httpx
import polars as pl

from odds_ticker.feed import FAIR_KEYS, MARKETS
from odds_ticker.models import MatchOdds

BASE_URL = "https://api.the-odds-api.com/v4/sports"
SPORTS: dict[str, str] = {
    "soccer_epl": "Premier League",
    "soccer_germany_bundesliga": "Bundesliga",
    "soccer_spain_la_liga": "La Liga",
    "soccer_italy_serie_a": "Serie A",
    "soccer_france_ligue_one": "Ligue 1",
    "soccer_netherlands_eredivisie": "Eredivisie",
    "soccer_turkey_super_league": "Trendyol Süper Lig",
    "soccer_uefa_champs_league": "Champions League",
    "soccer_uefa_europa_league": "Europa League",
}
MARKET_KEYS = ("h2h", "totals", "spreads")
LOGGER = logging.getLogger(__name__)


class LiveOddsFeed:
    """Fetch and normalise upcoming odds for the supported football leagues."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        ttl: float = 45.0,
        client: httpx.Client | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.api_key = api_key or os.getenv("ODDS_API_KEY", "")
        if not self.api_key:
            raise ValueError("An Odds API key is required for LiveOddsFeed")
        self.ttl = max(0.0, min(float(ttl), 60.0))
        self._client = client or httpx.Client(timeout=timeout)
        self._owns_client = client is None
        self._cached_at = 0.0
        self._cached_snapshot = pl.DataFrame()
        self._last_fetch_failed = False
        self._last_error: str | None = None
        self._history: dict[str, dict[str, deque[float]]] = defaultdict(lambda: defaultdict(lambda: deque(maxlen=15)))

    def close(self) -> None:
        """Close the HTTP connection pool owned by this feed."""
        if self._owns_client:
            self._client.close()

    def fetch_snapshot(self) -> pl.DataFrame:
        """Return the latest cached or newly fetched odds snapshot."""
        now_monotonic = time.monotonic()
        if self._cached_at and now_monotonic - self._cached_at < self.ttl:
            return self._cached_snapshot.clone()

        rows: list[dict[str, Any]] = []
        successful_requests = 0
        self._last_fetch_failed = False
        self._last_error = None
        for sport_key, league in SPORTS.items():
            try:
                response = self._client.get(
                    f"{BASE_URL}/{sport_key}/odds",
                    params={
                        "apiKey": self.api_key,
                        "regions": "eu,uk",
                        "markets": ",".join(MARKET_KEYS),
                        "oddsFormat": "decimal",
                        "dateFormat": "iso",
                    },
                )
                if response.status_code != 200:
                    detail = response.text[:300].replace("\n", " ")
                    if response.status_code == 404:
                        LOGGER.warning("Sport key '%s' unknown or inactive, skipping", sport_key)
                        continue
                    if response.status_code in (401, 429):
                        self._last_fetch_failed = True
                        self._last_error = f"HTTP {response.status_code}: {detail or response.reason_phrase}"
                        LOGGER.error("Odds API global request failure for %s: HTTP %s: %s", sport_key, response.status_code, detail or response.reason_phrase)
                        break
                    LOGGER.warning(
                        "Odds API request for %s returned HTTP %s: %s",
                        league,
                        response.status_code,
                        detail or response.reason_phrase,
                    )
                    response.raise_for_status()
                successful_requests += 1
                payload = response.json()
                if isinstance(payload, list):
                    rows.extend(self._parse_event(event, league) for event in payload)
            except httpx.HTTPStatusError as error:
                detail = error.response.text[:300].replace("\n", " ")
                LOGGER.error(
                    "Odds API request for %s failed with HTTP %s: %s",
                    league,
                    error.response.status_code,
                    detail or error,
                )
                # Keep useful results from other leagues if an endpoint is unavailable.
                continue
            except httpx.RequestError as error:
                LOGGER.error("Odds API request for %s failed: %s", league, error)
                continue
            except (ValueError, TypeError, KeyError) as error:
                # Keep useful results from other leagues if an endpoint is unavailable.
                LOGGER.warning("Could not fetch odds for %s: %s", league, error)
                continue

        if not self._last_fetch_failed and successful_requests == 0:
            self._last_fetch_failed = True
            self._last_error = "All sport key requests failed"

        if not rows:
            LOGGER.warning(
                "The Odds API returned no fixtures. Check API quota and key, and confirm "
                "fixtures are available in the eu,uk regions."
            )

        self._cached_snapshot = pl.DataFrame(rows) if rows else pl.DataFrame()
        self._cached_at = now_monotonic
        return self._cached_snapshot.clone()

    def _parse_event(self, event: dict[str, Any], league: str) -> dict[str, Any]:
        """Convert one Odds API event into the dashboard's normalised row."""
        prices: dict[str, float] = {}
        for bookmaker in event.get("bookmakers", []):
            markets = {market.get("key"): market for market in bookmaker.get("markets", [])}
            self._put_outcomes(prices, markets.get("h2h"), "h2h", event)
            self._put_outcomes(prices, markets.get("totals"), "totals", event)
            self._put_outcomes(prices, markets.get("btts"), "btts", event)
            self._put_outcomes(prices, markets.get("spreads"), "spreads", event)

        # Missing markets are represented as unavailable prices for compatibility;
        # the model and UI require valid decimal odds, so use neutral defaults.
        defaults = {
            "home_win": 1.90, "draw": 1.90, "away_win": 1.90,
            "over_2_5": 1.90, "under_2_5": 1.90,
            "btts_yes": 1.90, "btts_no": 1.90,
            "ah_home": 1.90, "ah_away": 1.90,
        }
        defaults.update(prices)
        fair = self._fair_probabilities(defaults)
        edges: dict[str, float] = {}
        for market, (keys, _) in MARKETS.items():
            probabilities = [fair[FAIR_KEYS.get(key, f"fair_{key}")] for key in keys]
            implied = [1 / defaults[key] for key in keys]
            total = sum(implied)
            edges[market] = round(max((p - price / total) * 100 for p, price in zip(probabilities, implied)), 2)

        best_market = max(edges, key=edges.get)
        keys, labels = MARKETS[best_market]
        best_index = max(range(len(keys)), key=lambda i: (fair[FAIR_KEYS.get(keys[i], f"fair_{keys[i]}")] - 1 / defaults[keys[i]]) * 100)
        row: dict[str, Any] = {
            "match_id": str(event.get("id") or f"{event.get('home_team')}-{event.get('away_team')}"),
            "home_team": str(event["home_team"]),
            "away_team": str(event["away_team"]),
            "league": league,
            **defaults,
            **fair,
            **{f"edge_{market}": edge for market, edge in edges.items()},
            "value_edge": edges[best_market],
            "value_market": best_market,
            "value_pick": labels[best_index],
            "value_odds": defaults[keys[best_index]],
            "value_probability": fair[FAIR_KEYS.get(keys[best_index], f"fair_{keys[best_index]}")],
            "timestamp": datetime.now(timezone.utc),
        }
        for key in defaults:
            self._history[row["match_id"]][key].append(defaults[key])
            row[f"history_{key}"] = list(self._history[row["match_id"]][key])
        for key in ("home_win", "draw", "away_win"):
            row[{"home_win": "home_trend", "draw": "draw_trend", "away_win": "away_trend"}[key]] = "–"
        MatchOdds.model_validate(row)
        return row

    @staticmethod
    def _put_outcomes(prices: dict[str, float], market: dict[str, Any] | None, kind: str, event: dict[str, Any]) -> None:
        """Read the first bookmaker's selections into standard outcome fields."""
        if not market:
            return
        for outcome in market.get("outcomes", []):
            name = str(outcome.get("name", "")).casefold()
            price = outcome.get("price")
            if price is None or float(price) <= 1:
                continue
            if kind == "h2h":
                key = "home_win" if name == str(event.get("home_team", "")).casefold() else "away_win" if name == str(event.get("away_team", "")).casefold() else "draw" if name == "draw" else None
            elif kind == "totals" and float(outcome.get("point", 2.5)) == 2.5:
                key = "over_2_5" if name == "over" else "under_2_5" if name == "under" else None
            elif kind == "btts":
                key = "btts_yes" if name in ("yes", "btts_yes") else "btts_no" if name in ("no", "btts_no") else None
            elif kind == "spreads":
                point = float(outcome.get("point", 0))
                if name == str(event.get("home_team", "")).casefold() and point < 0:
                    key = "ah_home"
                elif name == str(event.get("away_team", "")).casefold() and point > 0:
                    key = "ah_away"
                else:
                    key = None
            else:
                key = None
            if key and key not in prices:
                prices[key] = float(price)

    @staticmethod
    def _fair_probabilities(prices: dict[str, float]) -> dict[str, float]:
        """Estimate normalised fair probabilities from available market prices."""
        result: dict[str, float] = {}
        groups = {
            ("home_win", "draw", "away_win"), ("over_2_5", "under_2_5"),
            ("btts_yes", "btts_no"), ("ah_home", "ah_away"),
        }
        for group in groups:
            implied = [1 / prices[key] for key in group]
            total = sum(implied)
            for key, value in zip(group, implied):
                result[FAIR_KEYS.get(key, f"fair_{key}")] = value / total
        return result

    def history(self, match_id: str, outcome: str) -> list[float]:
        """Return up to fifteen recent prices for a fixture outcome."""
        return list(self._history[match_id][outcome])
