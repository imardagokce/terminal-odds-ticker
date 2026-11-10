<div align="center">

# ⚡ Terminal Odds Ticker

**A keyboard-driven football odds dashboard for the terminal.**

![Release](https://img.shields.io/badge/release-v2.3.0-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Textual](https://img.shields.io/badge/interface-Textual-6741D9?style=for-the-badge)
![Polars](https://img.shields.io/badge/data-Polars-CD792C?style=for-the-badge)
![License](https://img.shields.io/badge/licence-MIT-green?style=for-the-badge)

[Features](#features) · [Installation](#installation) · [Keybindings](#keybindings) · [Packaging](#packaging) · [Security](SECURITY.md)

</div>

## Overview

Terminal Odds Ticker compares football markets in a responsive Textual interface. Review fixtures and value edges, inspect odds movement, and view fractional Kelly stake guidance against an editable bankroll. Live network requests run asynchronously so refreshes leave keyboard navigation and the Command Palette responsive.

Odds and calculations are informational estimates, not betting advice. The application does not place bets or process payments.

## Features

- **Interactive TUI:** Colour-coded market tables, tabbed markets and a Match Inspector.
- **Live API and Mock Feed:** Use The Odds API with an API key; choose the local mock feed during onboarding or when live data is unavailable.
- **Today's Fixtures (`t`):** Filter the displayed fixtures to local today's date.
- **Bankroll editor (`b`):** Set the bankroll used for stake guidance and exposure warnings.
- **Sort Selection (`s`):** Choose value edge, implied win probability, kickoff time or decimal odds.
- **Match Inspector:** Review four markets, recent price movement, bookmaker overround, fractional Kelly stake, and win probability/loss risk visualisers.
- **League filter (`l`) and Kelly modes (`k`):** Focus the dashboard and cycle quarter, half and full Kelly guidance.

The live feed requests supported European and UK leagues and normalises head-to-head, totals, BTTS and spread prices. Missing live fixtures or API errors fall back to the Mock Feed.

## Installation

Requires Python 3.12 or later.

```bash
git clone https://github.com/imardagokce/terminal-odds-ticker.git
cd terminal-odds-ticker
python -m venv .venv
```

Activate the virtual environment, then install and launch:

```bash
pip install -r requirements.txt
python -m odds_ticker.app
```

To use live odds, set `ODDS_API_KEY` in the environment before launching. Without a key, the application offers the Mock Feed. On Windows, you can also launch the packaged `odds-ticker.exe` from a terminal; it uses the same environment key or saved per-user configuration.

## Keybindings

| Key | Action |
|:---:|:---|
| `q` | Quit |
| `r` | Refresh fixtures |
| `s` | Open sort selection |
| `l` | Open league filter |
| `t` | Toggle today's fixtures / all fixtures |
| `b` | Edit bankroll |
| `k` | Cycle Kelly fraction |
| `Ctrl+P` (`^p`) | Open the Command Palette |

## Packaging

Install dependencies and PyInstaller, then build the single-file executable with one command:

```bash
pip install -r requirements.txt pyinstaller
pyinstaller --clean --noconfirm --onefile odds-ticker.spec
```

The executable is written to `dist/odds-ticker.exe` on Windows (or `dist/odds-ticker` on other platforms). Run it from a terminal to retain interactive TUI input.

## Security

Treat the Odds API key as a secret. Prefer `ODDS_API_KEY`; if saved through onboarding, it is stored in the current user's application configuration. Logs intentionally omit response bodies and credential-bearing request details. See [SECURITY.md](SECURITY.md) for credential handling and private vulnerability reporting.

## Contributing

Contributions are welcome. Keep changes focused, describe user-visible behaviour, and avoid committing API keys or other credentials. Review [SECURITY.md](SECURITY.md) before reporting a vulnerability; use the private reporting route described there instead of a public issue.

## Licence

Distributed under the [MIT Licence](LICENSE).
