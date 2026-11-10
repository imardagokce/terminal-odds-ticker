<div align="center">

# ⚡ terminal-odds-ticker

**A keyboard-driven football odds and value analysis dashboard for your terminal.**

Compare simulated market prices, follow odds movement and explore Kelly staking in a fast Textual interface.

![Version 2.0.0](https://img.shields.io/badge/Version-2.0.0-blue?style=for-the-badge)
![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Textual](https://img.shields.io/badge/TUI-Textual-6741D9?style=for-the-badge)
![Polars](https://img.shields.io/badge/Data-Polars-CD792C?style=for-the-badge)
![MIT License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![Security Policy](https://img.shields.io/badge/Security-Policy-2ea44f?style=for-the-badge&logo=github)

[Overview](#overview) · [What's New](#version-200-whats-new) · [Features](#features) · [Quick Start](#quick-start) · [Live API](#live-api) · [Keybindings](#keybindings) · [Security](SECURITY.md) · [License](#license)

</div>

## Overview

`terminal-odds-ticker` is a terminal-based quantitative football betting tool. Its simulated feed refreshes odds snapshots as Polars data, calculates market value edges and presents fixtures in an interactive Textual dashboard. Inspect a match, compare its markets and view suggested fractional Kelly stakes against an editable bankroll.

> The included feed is simulated. Prices and value estimates are illustrative and are not betting advice.

## Version 2.0.0: What's New

- **Tabbed market views:** Switch between 1X2, Over / Under 2.5, Both Teams to Score (BTTS) and Asian Handicap (-0.5 / +0.5).
- **League Selection modal (`l`):** Choose individual leagues, select all leagues or clear the selection.
- **Live odds trends:** A native Textual `Sparkline` plots the selected outcome's recent odds history, retained for up to 15 feed ticks per fixture.
- **Dynamic Kelly modes (`k`):** Cycle through Quarter Kelly (25%), Half Kelly (50%) and Full Kelly (100%).
- **Exposure warning:** A warning appears when the combined recommended stakes for positive-edge fixtures exceed 15% of the entered bankroll.

## Features

- **Fast Polars engine** for working with refreshed multi-market snapshots.
- **Bookmaker vig detection** using implied probabilities and overround calculations.
- **Positive expected-value edge calculator** across all four supported market types.
- **Fractional Kelly stake guidance** with an editable bankroll and selectable Kelly fraction.
- **TCSS dark styling** with colour-coded edges, market tables and keyboard navigation.
- **Deterministic mock feed option** for repeatable development and tests through a configurable random seed.

## Quick Start

Requires Python 3.12 or newer.

```bash
git clone https://github.com/imardagokce/terminal-odds-ticker.git
cd terminal-odds-ticker
pip install -e .
odds-ticker
```

To run the test suite:

```bash
python -m unittest discover tests
```

## Live API

Set `ODDS_API_KEY` to enable live odds. Requests use decimal odds and cover the `eu,uk` regions, including European and UK bookmaker markets for supported leagues. The feed requests head-to-head, totals, BTTS and spreads markets.

If no fixtures appear, check that the key is valid, the account has remaining quota, and fixtures are currently available in the selected regions. See the [Security Policy](SECURITY.md) for credential handling and vulnerability reporting.

## Keybindings

| Key | Action |
|:---:|:---|
| `l` | Open the league selection modal |
| `k` | Cycle Quarter, Half and Full Kelly |
| `s` | Cycle sort order |
| `r` | Refresh the feed |
| `q` | Quit the application |

## License

This project is distributed under the [MIT License](LICENSE).
