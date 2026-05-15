import unittest

from scanner_agent.models import ScanResult
from scanner_agent.risk import size_position


def result(signal: str = "LONG") -> ScanResult:
    return ScanResult(
        scanned_at="2026-05-15T00:00:00+00:00",
        exchange="binance",
        symbol="BTCUSDT",
        base_asset="BTC",
        quote_asset="USDT",
        signal=signal,
        score=80,
        live_candidate=False,
        paper_trade=True,
        last_price=100.0,
        quote_volume_24h=1_000_000_000,
        price_change_15m=1.0,
        price_change_1h=2.0,
        price_change_4h=3.0,
        price_change_24h=4.0,
        volume_change_1h=30.0,
        funding_rate=0.01,
        open_interest=100_000,
        open_interest_change_1h=4.0,
        support=95.0,
        resistance=105.0,
        breakout=True,
        breakdown=False,
        news_catalyst=None,
        reason="test",
        data_warnings=[],
    )


class PositionSizingTests(unittest.TestCase):
    def test_sizes_long_from_risk_and_support_stop(self) -> None:
        plan = size_position(result("LONG"), account_equity_usd=10_000, risk_pct=1.0)

        self.assertTrue(plan.dry_run)
        self.assertEqual(plan.stop_price, 95.0)
        self.assertEqual(plan.risk_amount_usd, 100.0)
        self.assertEqual(plan.quantity, 20.0)
        self.assertEqual(plan.notional_usd, 2_000.0)

    def test_caps_notional_and_reduces_risk(self) -> None:
        plan = size_position(result("LONG"), account_equity_usd=10_000, risk_pct=1.0, max_notional_usd=500)

        self.assertEqual(plan.notional_usd, 500)
        self.assertEqual(plan.quantity, 5.0)
        self.assertEqual(plan.risk_amount_usd, 25.0)

    def test_rejects_leverage_in_first_phase(self) -> None:
        plan = size_position(result("LONG"), account_equity_usd=10_000, risk_pct=1.0, leverage=2.0)

        self.assertEqual(plan.quantity, 0.0)
        self.assertIn("no leverage", plan.reason)

    def test_no_trade_has_zero_size(self) -> None:
        plan = size_position(result("NO_TRADE"), account_equity_usd=10_000, risk_pct=1.0)

        self.assertEqual(plan.quantity, 0.0)
        self.assertEqual(plan.notional_usd, 0.0)


if __name__ == "__main__":
    unittest.main()
