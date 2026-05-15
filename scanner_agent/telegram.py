from __future__ import annotations

from .http import HttpError, post_json
from .models import ScanResult


class TelegramClient:
    def __init__(self, bot_token: str | None, chat_id: str | None, timeout: float = 12.0) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.timeout = timeout

    @property
    def enabled(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def send_alerts(self, results: list[ScanResult]) -> list[str]:
        if not self.enabled:
            return []
        sent: list[str] = []
        for result in results:
            if not result.paper_trade:
                continue
            message = format_alert(result)
            try:
                post_json(
                    f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                    {
                        "chat_id": self.chat_id,
                        "text": message,
                        "disable_web_page_preview": True,
                    },
                    timeout=self.timeout,
                )
                sent.append(result.symbol)
            except HttpError:
                continue
        return sent


def format_alert(result: ScanResult) -> str:
    live_text = "LIVE CANDIDATE ONLY - no order sent" if result.live_candidate else "PAPER TRADE"
    lines = [
        f"{live_text}",
        f"{result.exchange.upper()} {result.symbol}: {result.signal} {result.score}/100",
        f"Price: {result.last_price}",
        f"24h volume: ${result.quote_volume_24h:,.0f}",
        f"15m/1h/4h/24h: {_fmt(result.price_change_15m)} / {_fmt(result.price_change_1h)} / "
        f"{_fmt(result.price_change_4h)} / {_fmt(result.price_change_24h)}",
        f"Volume change 1h: {_fmt(result.volume_change_1h)}",
        f"Funding: {_fmt(result.funding_rate)}",
        f"OI change 1h: {_fmt(result.open_interest_change_1h)}",
        f"Support/Resistance: {result.support} / {result.resistance}",
        result.reason,
    ]
    return "\n".join(lines)


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}%"
