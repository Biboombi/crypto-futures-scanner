from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Literal


Signal = Literal["LONG", "SHORT", "NO_TRADE"]


@dataclass(frozen=True)
class Candle:
    open_time_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class MarketSnapshot:
    exchange: str
    symbol: str
    base_asset: str
    quote_asset: str
    last_price: float
    quote_volume_24h: float
    price_change_15m: float | None
    price_change_1h: float | None
    price_change_4h: float | None
    price_change_24h: float | None
    volume_change_1h: float | None
    funding_rate: float | None
    open_interest: float | None
    open_interest_change_1h: float | None
    support: float | None
    resistance: float | None
    breakout: bool
    breakdown: bool
    news_catalyst: str | None = None
    data_warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ScanResult:
    scanned_at: str
    exchange: str
    symbol: str
    base_asset: str
    quote_asset: str
    signal: Signal
    score: int
    live_candidate: bool
    paper_trade: bool
    last_price: float
    quote_volume_24h: float
    price_change_15m: float | None
    price_change_1h: float | None
    price_change_4h: float | None
    price_change_24h: float | None
    volume_change_1h: float | None
    funding_rate: float | None
    open_interest: float | None
    open_interest_change_1h: float | None
    support: float | None
    resistance: float | None
    breakout: bool
    breakdown: bool
    news_catalyst: str | None
    reason: str
    data_warnings: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
