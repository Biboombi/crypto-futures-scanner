# Crypto Futures Scanner Agent

A scanner-first Python project for Binance USDT-M and Bybit linear futures.
It runs in dry-run mode by default. It does not place live orders. It scans,
scores, saves results, optionally sends Telegram alerts, and records paper
trades when the score is high enough.

## Project Structure

```text
.
|-- scanner_agent/
|   |-- cli.py          # command-line entrypoint
|   |-- config.py       # .env loading and safe defaults
|   |-- exchanges.py    # Binance and Bybit futures clients
|   |-- models.py       # typed scan/result models
|   |-- news.py         # optional catalyst lookup
|   |-- persistence.py  # CSV/JSON and paper trade outputs
|   |-- risk.py         # dry-run position sizing
|   |-- runner.py       # scanner orchestration
|   |-- scoring.py      # signal scoring rules
|   `-- telegram.py     # alert-only Telegram client
|-- tests/
|   |-- test_position_sizing.py
|   `-- test_scoring.py
|-- .env.example
|-- pyproject.toml
`-- README.md
```

## What it does

- Scans Binance and Bybit futures pairs.
- Keeps only high-liquidity USDT perpetual markets.
- Collects 15m, 1h, 4h, and 24h price change.
- Collects volume change, funding rate, and open interest change.
- Detects support, resistance, breakout, and breakdown from recent candles.
- Optionally checks recent news catalysts when a news API key is configured.
- Outputs `LONG`, `SHORT`, or `NO_TRADE` with a score out of 100.
- Saves every scan to CSV and JSON.
- Creates paper-trade entries for score `>= 75`.
- Marks live candidates for score `>= 85`, but never places live orders.
- Sends Telegram alerts only.

## Quick Start

```powershell
python -m scanner_agent --once
```

Outputs are written to `data/`:

- `data/scans/latest.json`
- `data/scans/scan_YYYYMMDD_HHMMSS.json`
- `data/scans/scan_YYYYMMDD_HHMMSS.csv`
- `data/paper_trades.csv`

## Configuration

Copy the example file and edit values as needed:

```powershell
Copy-Item .env.example .env
```

The app also works without `.env`; defaults are conservative.

Important settings:

- `DRY_RUN`: defaults to `true`; live order placement is not implemented.
- `MIN_QUOTE_VOLUME_USD`: filters out low-liquidity markets.
- `MAX_SYMBOLS_PER_EXCHANGE`: caps scan size.
- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`: enable alerts.
- `CRYPTOPANIC_API_KEY` or `NEWSAPI_KEY`: enable news catalyst checks.

Never commit real API keys or Telegram tokens. Put secrets only in your local
`.env` file, which is ignored by git.

## Safety Rules

This project intentionally has no live order placement code.

- Dry-run mode is enabled by default.
- Score `>= 75`: paper trade.
- Score `>= 85`: live candidate flag only.
- Low-liquidity coins are filtered out.
- Unclear data produces `NO_TRADE`.
- First live phase rule is documented as no leverage, but live execution is not implemented.

## Example

```powershell
python -m scanner_agent --once --min-volume 50000000 --limit 40
```

## Tests

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

The tests cover signal scoring and dry-run position sizing, including max
notional caps and the no-leverage first-phase rule.

## Scheduling

Use Task Scheduler, cron, or a process manager to run the command repeatedly.
Keep the first phase scanner-only until the output has been reviewed over enough
market regimes.
