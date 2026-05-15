from __future__ import annotations

from dataclasses import dataclass

from .models import ScanResult


@dataclass(frozen=True)
class PositionPlan:
    symbol: str
    signal: str
    entry_price: float
    stop_price: float | None
    quantity: float
    notional_usd: float
    risk_amount_usd: float
    risk_pct: float
    leverage: float
    dry_run: bool
    reason: str


def size_position(
    result: ScanResult,
    account_equity_usd: float,
    risk_pct: float,
    max_notional_usd: float | None = None,
    leverage: float = 1.0,
    dry_run: bool = True,
) -> PositionPlan:
    if result.signal == "NO_TRADE":
        return _empty(result, risk_pct, leverage, dry_run, "No position because signal is NO_TRADE.")
    if account_equity_usd <= 0:
        return _empty(result, risk_pct, leverage, dry_run, "No position because account equity must be positive.")
    if not 0 < risk_pct <= 5:
        return _empty(result, risk_pct, leverage, dry_run, "No position because risk_pct must be between 0 and 5.")
    if leverage != 1.0:
        return _empty(result, risk_pct, leverage, dry_run, "No position because first live phase allows no leverage.")

    stop_price = _stop_price(result)
    if stop_price is None:
        return _empty(result, risk_pct, leverage, dry_run, "No position because a valid support/resistance stop is missing.")

    stop_distance = abs(result.last_price - stop_price)
    if stop_distance <= 0:
        return _empty(result, risk_pct, leverage, dry_run, "No position because stop distance is zero.")

    risk_amount = account_equity_usd * (risk_pct / 100)
    quantity = risk_amount / stop_distance
    notional = quantity * result.last_price
    if max_notional_usd is not None and notional > max_notional_usd:
        notional = max_notional_usd
        quantity = max_notional_usd / result.last_price
        risk_amount = quantity * stop_distance

    return PositionPlan(
        symbol=result.symbol,
        signal=result.signal,
        entry_price=result.last_price,
        stop_price=stop_price,
        quantity=quantity,
        notional_usd=notional,
        risk_amount_usd=risk_amount,
        risk_pct=risk_pct,
        leverage=leverage,
        dry_run=dry_run,
        reason="Dry-run position size calculated from account risk and technical stop.",
    )


def _stop_price(result: ScanResult) -> float | None:
    if result.signal == "LONG" and result.support is not None and result.support < result.last_price:
        return result.support
    if result.signal == "SHORT" and result.resistance is not None and result.resistance > result.last_price:
        return result.resistance
    return None


def _empty(result: ScanResult, risk_pct: float, leverage: float, dry_run: bool, reason: str) -> PositionPlan:
    return PositionPlan(
        symbol=result.symbol,
        signal=result.signal,
        entry_price=result.last_price,
        stop_price=None,
        quantity=0.0,
        notional_usd=0.0,
        risk_amount_usd=0.0,
        risk_pct=risk_pct,
        leverage=leverage,
        dry_run=dry_run,
        reason=reason,
    )
