from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from statistics import mean

from .http import HttpError, get_json
from .models import Candle, MarketSnapshot


@dataclass(frozen=True)
class FuturesMarket:
    exchange: str
    symbol: str
    base_asset: str
    quote_asset: str
    quote_volume_24h: float
    last_price: float


class ExchangeClient(ABC):
    name: str

    def __init__(self, timeout: float = 12.0) -> None:
        self.timeout = timeout

    @abstractmethod
    def high_volume_markets(self, min_quote_volume: float, limit: int) -> list[FuturesMarket]:
        raise NotImplementedError

    @abstractmethod
    def build_snapshot(self, market: FuturesMarket) -> MarketSnapshot:
        raise NotImplementedError


def pct_change(current: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return ((current - previous) / previous) * 100


def change_from_candles(candles: list[Candle], periods_back: int) -> float | None:
    if len(candles) <= periods_back:
        return None
    previous = candles[-periods_back - 1].close
    current = candles[-1].close
    return pct_change(current, previous)


def volume_change(candles: list[Candle], periods: int = 4) -> float | None:
    if len(candles) < periods * 2:
        return None
    recent = mean(c.volume for c in candles[-periods:])
    prior = mean(c.volume for c in candles[-periods * 2 : -periods])
    return pct_change(recent, prior)


def support_resistance(candles: list[Candle], lookback: int = 48) -> tuple[float | None, float | None]:
    if len(candles) < 10:
        return None, None
    sample = candles[-lookback:]
    return min(c.low for c in sample), max(c.high for c in sample)


def detect_breakout(last_price: float, support: float | None, resistance: float | None) -> tuple[bool, bool]:
    if support is None or resistance is None:
        return False, False
    buffer = 0.001
    return last_price > resistance * (1 + buffer), last_price < support * (1 - buffer)


class BinanceFuturesClient(ExchangeClient):
    name = "binance"
    base_url = "https://fapi.binance.com"

    def high_volume_markets(self, min_quote_volume: float, limit: int) -> list[FuturesMarket]:
        exchange_info = get_json(f"{self.base_url}/fapi/v1/exchangeInfo", timeout=self.timeout)
        tradable = {
            item["symbol"]: item
            for item in exchange_info.get("symbols", [])
            if item.get("contractType") == "PERPETUAL"
            and item.get("status") == "TRADING"
            and item.get("quoteAsset") == "USDT"
        }
        tickers = get_json(f"{self.base_url}/fapi/v1/ticker/24hr", timeout=self.timeout)
        markets: list[FuturesMarket] = []
        for ticker in tickers:
            symbol = ticker.get("symbol", "")
            info = tradable.get(symbol)
            if not info:
                continue
            quote_volume = float(ticker.get("quoteVolume", 0) or 0)
            if quote_volume < min_quote_volume:
                continue
            markets.append(
                FuturesMarket(
                    exchange=self.name,
                    symbol=symbol,
                    base_asset=info["baseAsset"],
                    quote_asset=info["quoteAsset"],
                    quote_volume_24h=quote_volume,
                    last_price=float(ticker["lastPrice"]),
                )
            )
        return sorted(markets, key=lambda m: m.quote_volume_24h, reverse=True)[:limit]

    def build_snapshot(self, market: FuturesMarket) -> MarketSnapshot:
        warnings: list[str] = []
        candles_15m = self._klines(market.symbol, "15m", 120, warnings)
        candles_1h = self._klines(market.symbol, "1h", 96, warnings)
        funding_rate = self._funding_rate(market.symbol, warnings)
        open_interest = self._open_interest(market.symbol, warnings)
        oi_change = self._open_interest_change(market.symbol, warnings)
        support, resistance = support_resistance(candles_1h)
        breakout, breakdown = detect_breakout(market.last_price, support, resistance)
        return MarketSnapshot(
            exchange=market.exchange,
            symbol=market.symbol,
            base_asset=market.base_asset,
            quote_asset=market.quote_asset,
            last_price=market.last_price,
            quote_volume_24h=market.quote_volume_24h,
            price_change_15m=change_from_candles(candles_15m, 1),
            price_change_1h=change_from_candles(candles_15m, 4),
            price_change_4h=change_from_candles(candles_15m, 16),
            price_change_24h=change_from_candles(candles_1h, 24),
            volume_change_1h=volume_change(candles_15m, 4),
            funding_rate=funding_rate,
            open_interest=open_interest,
            open_interest_change_1h=oi_change,
            support=support,
            resistance=resistance,
            breakout=breakout,
            breakdown=breakdown,
            data_warnings=warnings,
        )

    def _klines(self, symbol: str, interval: str, limit: int, warnings: list[str]) -> list[Candle]:
        try:
            rows = get_json(
                f"{self.base_url}/fapi/v1/klines",
                {"symbol": symbol, "interval": interval, "limit": limit},
                timeout=self.timeout,
            )
        except HttpError as exc:
            warnings.append(str(exc))
            return []
        return [
            Candle(
                open_time_ms=int(row[0]),
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
            )
            for row in rows
        ]

    def _funding_rate(self, symbol: str, warnings: list[str]) -> float | None:
        try:
            rows = get_json(
                f"{self.base_url}/fapi/v1/fundingRate",
                {"symbol": symbol, "limit": 1},
                timeout=self.timeout,
            )
            return float(rows[-1]["fundingRate"]) * 100 if rows else None
        except (HttpError, KeyError, ValueError, TypeError) as exc:
            warnings.append(f"funding unavailable: {exc}")
            return None

    def _open_interest(self, symbol: str, warnings: list[str]) -> float | None:
        try:
            row = get_json(
                f"{self.base_url}/fapi/v1/openInterest",
                {"symbol": symbol},
                timeout=self.timeout,
            )
            return float(row["openInterest"])
        except (HttpError, KeyError, ValueError, TypeError) as exc:
            warnings.append(f"open interest unavailable: {exc}")
            return None

    def _open_interest_change(self, symbol: str, warnings: list[str]) -> float | None:
        try:
            rows = get_json(
                f"{self.base_url}/futures/data/openInterestHist",
                {"symbol": symbol, "period": "15m", "limit": 5},
                timeout=self.timeout,
            )
            if len(rows) < 5:
                return None
            return pct_change(float(rows[-1]["sumOpenInterest"]), float(rows[0]["sumOpenInterest"]))
        except (HttpError, KeyError, ValueError, TypeError) as exc:
            warnings.append(f"open interest change unavailable: {exc}")
            return None


class BybitFuturesClient(ExchangeClient):
    name = "bybit"
    base_url = "https://api.bybit.com"

    def high_volume_markets(self, min_quote_volume: float, limit: int) -> list[FuturesMarket]:
        instruments = get_json(
            f"{self.base_url}/v5/market/instruments-info",
            {"category": "linear", "limit": 1000},
            timeout=self.timeout,
        )
        tradable = {
            item["symbol"]: item
            for item in instruments.get("result", {}).get("list", [])
            if item.get("status") == "Trading"
            and item.get("contractType") == "LinearPerpetual"
            and item.get("quoteCoin") == "USDT"
        }
        tickers = get_json(
            f"{self.base_url}/v5/market/tickers",
            {"category": "linear"},
            timeout=self.timeout,
        )
        markets: list[FuturesMarket] = []
        for ticker in tickers.get("result", {}).get("list", []):
            symbol = ticker.get("symbol", "")
            info = tradable.get(symbol)
            if not info:
                continue
            quote_volume = float(ticker.get("turnover24h", 0) or 0)
            if quote_volume < min_quote_volume:
                continue
            markets.append(
                FuturesMarket(
                    exchange=self.name,
                    symbol=symbol,
                    base_asset=info["baseCoin"],
                    quote_asset=info["quoteCoin"],
                    quote_volume_24h=quote_volume,
                    last_price=float(ticker["lastPrice"]),
                )
            )
        return sorted(markets, key=lambda m: m.quote_volume_24h, reverse=True)[:limit]

    def build_snapshot(self, market: FuturesMarket) -> MarketSnapshot:
        warnings: list[str] = []
        candles_15m = self._klines(market.symbol, "15", 120, warnings)
        candles_1h = self._klines(market.symbol, "60", 96, warnings)
        funding_rate = self._funding_rate(market.symbol, warnings)
        open_interest = self._open_interest(market.symbol, warnings)
        oi_change = self._open_interest_change(market.symbol, warnings)
        support, resistance = support_resistance(candles_1h)
        breakout, breakdown = detect_breakout(market.last_price, support, resistance)
        return MarketSnapshot(
            exchange=market.exchange,
            symbol=market.symbol,
            base_asset=market.base_asset,
            quote_asset=market.quote_asset,
            last_price=market.last_price,
            quote_volume_24h=market.quote_volume_24h,
            price_change_15m=change_from_candles(candles_15m, 1),
            price_change_1h=change_from_candles(candles_15m, 4),
            price_change_4h=change_from_candles(candles_15m, 16),
            price_change_24h=change_from_candles(candles_1h, 24),
            volume_change_1h=volume_change(candles_15m, 4),
            funding_rate=funding_rate,
            open_interest=open_interest,
            open_interest_change_1h=oi_change,
            support=support,
            resistance=resistance,
            breakout=breakout,
            breakdown=breakdown,
            data_warnings=warnings,
        )

    def _klines(self, symbol: str, interval: str, limit: int, warnings: list[str]) -> list[Candle]:
        try:
            rows = get_json(
                f"{self.base_url}/v5/market/kline",
                {"category": "linear", "symbol": symbol, "interval": interval, "limit": limit},
                timeout=self.timeout,
            ).get("result", {}).get("list", [])
        except HttpError as exc:
            warnings.append(str(exc))
            return []
        candles = [
            Candle(
                open_time_ms=int(row[0]),
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
                volume=float(row[5]),
            )
            for row in rows
        ]
        return sorted(candles, key=lambda candle: candle.open_time_ms)

    def _funding_rate(self, symbol: str, warnings: list[str]) -> float | None:
        try:
            rows = get_json(
                f"{self.base_url}/v5/market/funding/history",
                {"category": "linear", "symbol": symbol, "limit": 1},
                timeout=self.timeout,
            ).get("result", {}).get("list", [])
            return float(rows[0]["fundingRate"]) * 100 if rows else None
        except (HttpError, KeyError, ValueError, TypeError) as exc:
            warnings.append(f"funding unavailable: {exc}")
            return None

    def _open_interest(self, symbol: str, warnings: list[str]) -> float | None:
        try:
            rows = get_json(
                f"{self.base_url}/v5/market/open-interest",
                {"category": "linear", "symbol": symbol, "intervalTime": "15min", "limit": 1},
                timeout=self.timeout,
            ).get("result", {}).get("list", [])
            return float(rows[0]["openInterest"]) if rows else None
        except (HttpError, KeyError, ValueError, TypeError) as exc:
            warnings.append(f"open interest unavailable: {exc}")
            return None

    def _open_interest_change(self, symbol: str, warnings: list[str]) -> float | None:
        try:
            rows = get_json(
                f"{self.base_url}/v5/market/open-interest",
                {"category": "linear", "symbol": symbol, "intervalTime": "15min", "limit": 5},
                timeout=self.timeout,
            ).get("result", {}).get("list", [])
            if len(rows) < 5:
                return None
            ordered = sorted(rows, key=lambda row: int(row["timestamp"]))
            return pct_change(float(ordered[-1]["openInterest"]), float(ordered[0]["openInterest"]))
        except (HttpError, KeyError, ValueError, TypeError) as exc:
            warnings.append(f"open interest change unavailable: {exc}")
            return None
