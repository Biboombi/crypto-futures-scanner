import unittest

from scanner_agent.models import MarketSnapshot
from scanner_agent.scoring import score_snapshot


class ScoringTests(unittest.TestCase):
    def test_high_conviction_breakout_creates_paper_trade_and_live_candidate(self) -> None:
        snapshot = MarketSnapshot(
            exchange="binance",
            symbol="BTCUSDT",
            base_asset="BTC",
            quote_asset="USDT",
            last_price=105.0,
            quote_volume_24h=1_000_000_000,
            price_change_15m=1.5,
            price_change_1h=3.0,
            price_change_4h=5.0,
            price_change_24h=8.0,
            volume_change_1h=40.0,
            funding_rate=0.01,
            open_interest=100_000,
            open_interest_change_1h=4.0,
            support=90.0,
            resistance=100.0,
            breakout=True,
            breakdown=False,
            news_catalyst="ETF flows",
            data_warnings=[],
        )

        result = score_snapshot(snapshot)

        self.assertEqual(result.signal, "LONG")
        self.assertGreaterEqual(result.score, 85)
        self.assertTrue(result.paper_trade)
        self.assertTrue(result.live_candidate)

    def test_unclear_data_forces_no_trade(self) -> None:
        snapshot = MarketSnapshot(
            exchange="bybit",
            symbol="NEWUSDT",
            base_asset="NEW",
            quote_asset="USDT",
            last_price=1.0,
            quote_volume_24h=60_000_000,
            price_change_15m=None,
            price_change_1h=None,
            price_change_4h=None,
            price_change_24h=None,
            volume_change_1h=None,
            funding_rate=None,
            open_interest=None,
            open_interest_change_1h=None,
            support=None,
            resistance=None,
            breakout=False,
            breakdown=False,
            data_warnings=[],
        )

        result = score_snapshot(snapshot)

        self.assertEqual(result.signal, "NO_TRADE")
        self.assertEqual(result.score, 0)
        self.assertFalse(result.paper_trade)


if __name__ == "__main__":
    unittest.main()
