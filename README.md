# Crypto Futures Scanner Agent

A scanner-first crypto futures agent for Binance USDT-M and Bybit linear futures.
It does not place live orders. It scans, scores, saves results, optionally sends
Telegram alerts, and records paper trades when the score is high enough.

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

- `MIN_QUOTE_VOLUME_USD`: filters out low-liquidity markets.
- `MAX_SYMBOLS_PER_EXCHANGE`: caps scan size.
- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`: enable alerts.
- `CRYPTOPANIC_API_KEY` or `NEWSAPI_KEY`: enable news catalyst checks.

## Safety Rules

This project intentionally has no live order placement code.

- Score `>= 75`: paper trade.
- Score `>= 85`: live candidate flag only.
- Low-liquidity coins are filtered out.
- Unclear data produces `NO_TRADE`.
- First live phase rule is documented as no leverage, but live execution is not implemented.

## Example

```powershell
python -m scanner_agent --once --min-volume 50000000 --limit 40
```

## Scheduling

Use Task Scheduler, cron, or a process manager to run the command repeatedly.
Keep the first phase scanner-only until the output has been reviewed over enough
market regimes.
