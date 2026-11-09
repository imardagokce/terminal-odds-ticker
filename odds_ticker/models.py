"""Validated data models used by the odds ticker."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MatchOdds(BaseModel):
    """Odds and value estimates for a football fixture's supported markets."""

    model_config = ConfigDict(frozen=True)

    match_id: str = Field(min_length=1)
    home_team: str = Field(min_length=1)
    away_team: str = Field(min_length=1)
    league: str = Field(min_length=1)
    home_win: float = Field(gt=1.0)
    draw: float = Field(gt=1.0)
    away_win: float = Field(gt=1.0)
    over_2_5: float = Field(default=1.90, gt=1.0)
    under_2_5: float = Field(default=1.90, gt=1.0)
    btts_yes: float = Field(default=1.90, gt=1.0)
    btts_no: float = Field(default=1.90, gt=1.0)
    ah_home: float = Field(default=1.90, gt=1.0)
    ah_away: float = Field(default=1.90, gt=1.0)
    value_edge: float
    timestamp: datetime
