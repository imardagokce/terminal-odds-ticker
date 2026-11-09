"""Odds and staking calculations for the market inspector."""


def calculate_implied_probability(decimal_odds: float) -> float:
    """Return the implied probability for decimal odds."""
    if decimal_odds <= 1:
        raise ValueError("Decimal odds must be greater than 1")
    return 1.0 / decimal_odds


def calculate_overround(home: float, draw: float, away: float) -> float:
    """Return the bookmaker overround as a percentage."""
    probabilities = tuple(calculate_implied_probability(price) for price in (home, draw, away))
    return (sum(probabilities) - 1.0) * 100.0


def calculate_fractional_kelly(
    odds: float,
    estimated_prob: float,
    fraction: float = 0.25,
    bankroll: float = 1000.0,
) -> float:
    """Return the fractional Kelly stake in bankroll currency units."""
    if odds <= 1:
        raise ValueError("Decimal odds must be greater than 1")
    if not 0 <= estimated_prob <= 1:
        raise ValueError("Estimated probability must be between 0 and 1")
    if not 0 <= fraction <= 1:
        raise ValueError("Kelly fraction must be between 0 and 1")
    if bankroll < 0:
        raise ValueError("Bankroll cannot be negative")
    net_odds = odds - 1.0
    full_kelly = (net_odds * estimated_prob - (1.0 - estimated_prob)) / net_odds
    return max(0.0, full_kelly) * fraction * bankroll
