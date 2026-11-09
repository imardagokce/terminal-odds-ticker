"""Validated data models used by the odds ticker."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MatchOdds(BaseModel):
    """Odds and calculated value for a single football fixture."""

    model_config = ConfigDict(frozen=True)

    match_id: str = Field(min_length=1)
    home_team: str = Field(min_length=1)
    away_team: str = Field(min_length=1)
    league: str = Field(min_length=1)
    home_win: float = Field(gt=1.0)
    draw: float = Field(gt=1.0)
    away_win: float = Field(gt=1.0)
    value_edge: float
    timestamp: datetime
