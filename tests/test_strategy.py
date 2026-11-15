#!/usr/bin/env python3
"""Tests for the deep-dip V-catcher (pure standard library).

Run from the repository root:  python3 -m unittest discover -s tests -v
These tests drive DipCatcher.on_batch through the kit shim's BarsState,
so they exercise the same decision code the graded run uses, without any
network or the kit's harness.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "vendor"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import makefun_bars
from main import DipCatcher

HELLO = {
    "type": "hello",
    "protocol": "agent-fun/bars-replay/v1",
    "seed": "1",
    "symbols": [{"symbol": "CBBTC", "mint": "cbbtcf3aa214zXHbiAZQwf4122FBYbraNdFqgw4iMij",
                 "price_scale": 5, "qty_scale": 8}],
    "capital": {"quote": "USDC", "quote_scale": 6, "quote_units": "1000000000"},
    "bar_interval": "1m",
    "first_close_ms": 0,
    "caps": {"max_open_positions": 1, "max_orders_per_bar": 16,
             "max_weight_bps": 10000, "shorts": False, "leverage": False},
    "fees": {"fee_bps": 4, "slippage_bps": 2, "min_notional_quote_units": "1000000"},
    "latency_bars": 1,
}


def batch(seq, close, cash="1000000000", positions=None):
    """One batch with a single flat bar closing at `close` (raw price units)."""
    return {
        "type": "batch",
        "seq": seq,
        "t": seq * 60000,
        "bars": [{"symbol": "CBBTC", "t": seq * 60000,
                  "o": str(close), "h": str(close), "l": str(close), "c": str(close),
                  "v": None, "o_depth": ["660000000000"], "c_depth": ["660000000000"]}],
        "fills": [],
        "account": {"cash_quote_units": cash, "positions": positions or [],
                    "equity_quote_units": cash},
    }


def flat_run(bot, closes, cash="1000000000"):
    """Feed closes as flat bars; return the list of replies (order lists)."""
    state = makefun_bars.BarsState(HELLO)
    replies = []
    for i, c in enumerate(closes):
        b = batch(i, c, cash=cash)
        state.apply_batch(b)
        replies.append(bot.on_batch(state, b))
    return replies


class TestDipCatcher(unittest.TestCase):
    def test_flat_market_never_trades(self):
        bot = DipCatcher()
        replies = flat_run(bot, [6500000000] * 300)
        self.assertTrue(all(r == [] for r in replies))

    def test_primary_dip_buys_full_cash(self):
        bot = DipCatcher()
        # 60 flat bars at 67000, then a close 3% below the 60-min high.
        closes = [6700000000] * 60 + [6499000000]
        replies = flat_run(bot, closes)
        self.assertEqual(replies[-1][0]["side"], "buy")
        self.assertEqual(replies[-1][0]["notional_quote_units"], 1000000000)

    def test_shallow_dip_does_not_buy(self):
        bot = DipCatcher()
        closes = [6700000000] * 60 + [6600000000]  # only -1.5%
        replies = flat_run(bot, closes)
        self.assertEqual(replies[-1], [])

    def test_take_profit_sells_whole_position(self):
        bot = DipCatcher()
        state = makefun_bars.BarsState(HELLO)
        # Buy at 65000: feed the dip, then pretend the fill happened.
        closes = [6700000000] * 60 + [6499000000]
        for i, c in enumerate(closes):
            b = batch(i, c)
            state.apply_batch(b)
            orders = bot.on_batch(state, b)
        self.assertEqual(orders[0]["side"], "buy")
        # Position: 1,538,000 satoshis (~0.0154 BTC) bought for ~$1,000.
        qty = 1538000
        pos = [{"symbol": "CBBTC", "qty": str(qty), "cost_quote_units": "1000000000"}]
        # Price +4% over the buy: value 1,040,000,000 > cost * 1.03.
        b = batch(len(closes), 6760000000, cash="0", positions=pos)
        state.apply_batch(b)
        orders = bot.on_batch(state, b)
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0]["side"], "sell")
        self.assertEqual(orders[0]["qty"], qty)

    def test_stop_loss_sells_and_cools_down(self):
        bot = DipCatcher()
        state = makefun_bars.BarsState(HELLO)
        closes = [6700000000] * 60 + [6499000000]
        for i, c in enumerate(closes):
            b = batch(i, c)
            state.apply_batch(b)
            bot.on_batch(state, b)
        qty = 1538000
        pos = [{"symbol": "CBBTC", "qty": str(qty), "cost_quote_units": "1000000000"}]
        # Price -4%: value ~960,000,000 < cost * 0.97 -> stop loss.
        b = batch(len(closes), 6240000000, cash="0", positions=pos)
        state.apply_batch(b)
        orders = bot.on_batch(state, b)
        self.assertEqual(orders[0]["side"], "sell")
        # Next bars: still dipping, but the 30-bar cooldown blocks re-entry.
        for j in range(1, 10):
            b = batch(len(closes) + j, 6000000000)
            state.apply_batch(b)
            self.assertEqual(bot.on_batch(state, b), [])

    def test_fallback_fires_late_on_shallow_dip(self):
        bot = DipCatcher()
        # 120 flat bars, then a -2% close at bar 1200 (past FALLBACK_BAR).
        closes = [6700000000] * 1200 + [6566000000]
        replies = flat_run(bot, closes)
        self.assertEqual(replies[-1][0]["side"], "buy")
        # Half the cash.
        self.assertEqual(replies[-1][0]["notional_quote_units"], 500000000)

    def test_no_fallback_before_bar_1080(self):
        bot = DipCatcher()
        closes = [6700000000] * 300 + [6566000000]  # -2% at bar 300
        replies = flat_run(bot, closes)
        self.assertEqual(replies[-1], [])


if __name__ == "__main__":
    unittest.main()
