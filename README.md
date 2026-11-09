<div align="center">

# ⚡ terminal-odds-ticker

**A live-style football odds dashboard for your terminal.**

Track simulated market movement, spot potential value and explore fractional Kelly staking from a keyboard-first Textual interface.

[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Textual TUI](https://img.shields.io/badge/TUI-Textual-6741D9)](https://textual.textualize.io/)
[![Polars Core](https://img.shields.io/badge/Data-Polars-CD792C)](https://pola.rs/)
[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

[Overview](#overview) · [Features](#features) · [Quick Start](#quick-start) · [Keybindings](#keybindings) · [License](#license)

</div>

## Overview

`terminal-odds-ticker` is a compact terminal application for exploring football 1X2 odds. Its mock feed produces live-style snapshots as Polars DataFrames, with small random price movements and calculated value edges. Use the split-screen market table and match inspector to follow the fixtures that interest you.

## Features

- **Real-time Polars data streaming** from a simulated football odds feed, refreshed every three seconds.
- **Fractional Kelly criterion calculator** with an editable bankroll and a suggested quarter-Kelly stake.
- **Vig and margin detection** with implied probability breakdowns for each outcome.
- **Odds movement history** for the selected value pick.
- **Hotkey sorting and league filtering** to focus the market table.
- **High-contrast dark interface** with colour-coded value edges.

## Quick Start

Requires Python 3.12 or newer.

```bash
git clone https://github.com/imardagokce/terminal-odds-ticker.git
cd terminal-odds-ticker
python -m pip install -e .
odds-ticker
```

The feed is simulated; it does not connect to bookmakers or provide real-time betting prices.

## Keybindings

| Key | Action |
|:---:|:---|
| `q` | Quit the application |
| `r` | Refresh the market snapshot |
| `s` | Cycle sorting by value edge, home odds and league |
| `f` | Cycle through league filters |

## License

This project is distributed under the [MIT License](LICENSE).
