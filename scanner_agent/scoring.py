from __future__ import annotations

from .models import MarketSnapshot, ScanResult, Signal, utc_now_iso


MIN_REQUIRED_FIELDS = (
    "price_change_15m",
    "price_change_1h",
    "price_change_4h",
    "price_change_24h",
    "volume_change_1h",
    "funding_rate",
    "open_interest_change_1h",
    "support",
    "resistance",
)


def score_snapshot(snapshot: MarketSnapshot) -> ScanResult:
    warnings = list(snapshot.data_warnings)
    missing = [name for name in MIN_REQUIRED_FIELDS if getattr(snapshot, name) is None]
    if len(missing) >= 4:
        warnings.append(f"unclear data: missing {', '.join(missing)}")
        return _result(snapshot, "NO_TRADE", 0, "Data is too incomplete for a responsible signal.", warnings)

    long_score, short_score, reasons = _directional_scores(snapshot)
    score = max(long_score, short_score)
    signal: Signal
    if score < 55:
        signal = "NO_TRADE"
    elif long_score >= short_score + 10:
        signal = "LONG"
    elif short_score >= long_score + 10:
        signal = "SHORT"
    else:
        signal = "NO_TRADE"
        reasons.append("Long and short evidence is mixed, so the scanner stays flat.")

    if signal == "NO_TRADE":
        score = min(score, 74)

    reason = " ".join(reasons) if reasons else "No strong directional edge was detected."
    return _result(snapshot, signal, int(min(score, 100)), reason, warnings)


def _directional_scores(snapshot: MarketSnapshot) -> tuple[float, float, list[str]]:
    long_score = 0.0
    short_score = 0.0
    reasons: list[str] = []

    momentum = [
        snapshot.price_change_15m,
        snapshot.price_change_1h,
        snapshot.price_change_4h,
        snapshot.price_change_24h,
    ]
    positive_count = sum(1 for value in momentum if value is not None and value > 0)
    negative_count = sum(1 for value in momentum if value is not None and value < 0)
    if positive_count >= 3:
        long_score += 25
        reasons.append("Momentum is bullish across most tracked windows.")
    if negative_count >= 3:
        short_score += 25
        reasons.append("Momentum is bearish across most tracked windows.")

    if snapshot.price_change_15m is not None and snapshot.price_change_1h is not None:
        if snapshot.price_change_15m > 1.0 and snapshot.price_change_1h > 2.0:
            long_score += 12
            reasons.append("Short-term price expansion suggests fresh buying pressure.")
        if snapshot.price_change_15m < -1.0 and snapshot.price_change_1h < -2.0:
            short_score += 12
            reasons.append("Short-term selling pressure is accelerating.")

    if snapshot.volume_change_1h is not None:
        if snapshot.volume_change_1h > 25:
            long_score += 12
            short_score += 12
            reasons.append("Volume expanded sharply, confirming that the move has participation.")
        elif snapshot.volume_change_1h < -25:
            long_score -= 8
            short_score -= 8
            reasons.append("Volume is fading, which weakens conviction.")

    if snapshot.open_interest_change_1h is not None:
        if snapshot.open_interest_change_1h > 3:
            if _net_price_change(snapshot) >= 0:
                long_score += 15
                reasons.append("Open interest rose with price, consistent with new long positioning.")
            else:
                short_score += 15
                reasons.append("Open interest rose while price fell, consistent with new short positioning.")
        elif snapshot.open_interest_change_1h < -3:
            long_score -= 5
            short_score -= 5
            reasons.append("Open interest contracted, so the move may be driven by position closing.")

    if snapshot.funding_rate is not None:
        if snapshot.funding_rate > 0.05:
            long_score -= 8
            short_score += 8
            reasons.append("Funding is elevated positive, warning that longs may be crowded.")
        elif snapshot.funding_rate < -0.05:
            short_score -= 8
            long_score += 8
            reasons.append("Funding is deeply negative, warning that shorts may be crowded.")

    if snapshot.breakout:
        long_score += 22
        reasons.append("Price broke above recent resistance.")
    if snapshot.breakdown:
        short_score += 22
        reasons.append("Price broke below recent support.")

    if snapshot.news_catalyst:
        long_score += 4
        short_score += 4
        reasons.append(f"Recent news catalyst found: {snapshot.news_catalyst}.")
    else:
        reasons.append("No fresh news catalyst was available from configured news sources.")

    if snapshot.price_change_24h is not None:
        if snapshot.price_change_24h > 0:
            reasons.append("The token likely pumped because price, volume, and derivatives positioning aligned upward.")
        elif snapshot.price_change_24h < 0:
            reasons.append("The token likely dropped because sellers controlled recent momentum and derivatives flows.")

    return max(long_score, 0), max(short_score, 0), reasons


def _net_price_change(snapshot: MarketSnapshot) -> float:
    values = [
        value
        for value in (snapshot.price_change_15m, snapshot.price_change_1h, snapshot.price_change_4h)
        if value is not None
    ]
    return sum(values) / len(values) if values else 0


def _result(
    snapshot: MarketSnapshot,
    signal: Signal,
    score: int,
    reason: str,
    warnings: list[str],
) -> ScanResult:
    return ScanResult(
        scanned_at=utc_now_iso(),
        exchange=snapshot.exchange,
        symbol=snapshot.symbol,
        base_asset=snapshot.base_asset,
        quote_asset=snapshot.quote_asset,
        signal=signal,
        score=score,
        live_candidate=score >= 85 and signal != "NO_TRADE",
        paper_trade=score >= 75 and signal != "NO_TRADE",
        last_price=snapshot.last_price,
        quote_volume_24h=snapshot.quote_volume_24h,
        price_change_15m=snapshot.price_change_15m,
        price_change_1h=snapshot.price_change_1h,
        price_change_4h=snapshot.price_change_4h,
        price_change_24h=snapshot.price_change_24h,
        volume_change_1h=snapshot.volume_change_1h,
        funding_rate=snapshot.funding_rate,
        open_interest=snapshot.open_interest,
        open_interest_change_1h=snapshot.open_interest_change_1h,
        support=snapshot.support,
        resistance=snapshot.resistance,
        breakout=snapshot.breakout,
        breakdown=snapshot.breakdown,
        news_catalyst=snapshot.news_catalyst,
        reason=reason,
        data_warnings=warnings,
    )
