from __future__ import annotations

import csv
import json
from dataclasses import fields
from pathlib import Path

from .models import ScanResult


def ensure_output_dirs(output_dir: Path) -> tuple[Path, Path]:
    scans_dir = output_dir / "scans"
    scans_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir, scans_dir


def save_scan(results: list[ScanResult], output_dir: Path, stamp: str) -> tuple[Path, Path, Path]:
    _, scans_dir = ensure_output_dirs(output_dir)
    json_path = scans_dir / f"scan_{stamp}.json"
    csv_path = scans_dir / f"scan_{stamp}.csv"
    latest_path = scans_dir / "latest.json"

    payload = [result.to_dict() for result in results]
    json_text = json.dumps(payload, indent=2, sort_keys=True)
    json_path.write_text(json_text, encoding="utf-8")
    latest_path.write_text(json_text, encoding="utf-8")

    fieldnames = [field.name for field in fields(ScanResult)]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            row = result.to_dict()
            row["data_warnings"] = " | ".join(result.data_warnings)
            writer.writerow(row)

    return json_path, csv_path, latest_path


def append_paper_trades(results: list[ScanResult], output_dir: Path) -> Path:
    ensure_output_dirs(output_dir)
    path = output_dir / "paper_trades.csv"
    trade_results = [result for result in results if result.paper_trade]
    fieldnames = [
        "scanned_at",
        "exchange",
        "symbol",
        "signal",
        "score",
        "live_candidate",
        "entry_price",
        "support",
        "resistance",
        "reason",
    ]
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        for result in trade_results:
            writer.writerow(
                {
                    "scanned_at": result.scanned_at,
                    "exchange": result.exchange,
                    "symbol": result.symbol,
                    "signal": result.signal,
                    "score": result.score,
                    "live_candidate": result.live_candidate,
                    "entry_price": result.last_price,
                    "support": result.support,
                    "resistance": result.resistance,
                    "reason": result.reason,
                }
            )
    return path
