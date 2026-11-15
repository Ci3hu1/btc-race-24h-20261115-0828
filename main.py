#!/usr/bin/env python3
"""Deep-dip V-catcher for the make.fun btc-race-24h-20261115-0828 bounty.

Entry for make.fun competition btc-race-24h-20261115-0828: race a BTC
trading bot live for 24 hours on 1-minute cbBTC/USDC bars from the Orca
Whirlpool on Solana. Long only, $1,000 paper USDC, no leverage.

Method (standard library only, no network, no wall clock, deterministic):
  The bot buys sharp dips and sells the recovery.  On every batch (one
  1-minute bar) it looks at the close of cbBTC:

  * PRIMARY entry: the close is at least 2.5% below the highest close of
    the last 60 minutes -> buy with all cash.  A 2.5% hourly drawdown is a
    rare, violent move; on the dev window it happened once, at the bottom
    of the -2% hour, and the recovery that followed was +2.8% in the next
    hour.  The trade needs a move larger than the ~26 bps a full-size
    round trip costs (4 bps fee + 2 bps slippage + ~15 bps of pool impact
    each way), so the entry only fires on moves an order of magnitude
    larger than the cost.
  * FALLBACK entry: from bar 1080 (the last 6 hours of the window) on,
    if no primary dip has fired yet, a close at least 1.5% below the
    highest close of the last 120 minutes buys half the cash.  This only
    exists so the bot still takes at least one trade (the guardrail needs
    >= 1 trade) on a quiet window where no 2.5% dip ever arrives.  A
    fallback position is topped up to full size if the primary dip then
    fires while it is held.
  * EXIT, whole position: take profit at +3.0% over cost, stop loss at
    -3.0% under cost, or a trailing stop once the position peaked at
    +2.0% or more (sell when it gives back 1.2% from that peak).  The
    stop caps the damage when a dip keeps dipping; the trailing stop
    locks in most of a V-recovery if the bounce stalls below +3%.
  * After a stop-loss sell the bot sits out the next 30 bars, so one
    falling market cannot trigger a fresh buy on every small bounce.

  Why this shape: on 90 days of Binance BTCUSDT 1-minute closes (the
  same price action, different venue) every simple rule tested --
  RSI/Bollinger mean reversion, EMA crosses, breakout momentum, small-dip
  buying -- lost money on average once the 26 bps round-trip cost is
  charged, because 1-minute noise is ~12 bps and dips usually keep
  dipping.  The only structure that paid on the dev window was the single
  deep V (a -2% hour followed by a +2.8% hour).  So the bot is deliberately
  a rare-trade sniper, not a frequent trader: it waits for a violent dip,
  takes the recovery, and otherwise stays in cash.  On the dev window it
  makes one primary round trip (+$29.95 in local replay) plus, in the
  last hours, one fallback half-size trade; the local replay of the final
  rules is in tests/ and the kit's grade-local confirms it.

  The final score is decided by the race window, which nobody has seen.
  This bot does not pretend to know what it will do there: if the race
  window has a deep dip and a recovery it catches it; if it grinds down,
  the stop loss caps each trade at about -3%; if it is quiet, the
  fallback still takes one disciplined trade.  Places go to the ten
  highest net PnLs even when they are below zero, so capping the downside
  matters as much as catching the upside.

Runs on the agent-fun/bars-replay/v1 protocol via the kit's Python shim
(vendor/makefun_bars.py, a byte-identical copy of the kit's SDK).  Orders
decided on a batch fill at the next bar's open; max_slippage_bps is 100
(1%) so a fill more than 1% past the close it was decided on is refused
rather than filled for almost nothing.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"

# Entry thresholds, in basis points.
PRIMARY_LOOKBACK = 60        # minutes of closes for the primary dip
PRIMARY_DIP_BPS = 250        # buy when close is 2.5% under the 60-min high
FALLBACK_BAR = 1080          # fallback only in the last 6 hours (bar 1080+)
FALLBACK_LOOKBACK = 120      # minutes of closes for the fallback dip
FALLBACK_DIP_BPS = 150       # buy half the cash when 1.5% under the 120-min high

# Exit thresholds, in basis points of the position's cost.
TAKE_PROFIT_BPS = 300        # sell at +3.0% over cost
STOP_LOSS_BPS = 300          # sell at -3.0% under cost
TRAIL_ARM_BPS = 200          # trailing stop arms once the peak is +2.0%
TRAIL_GIVEBACK_BPS = 120     # ... then sell 1.2% below that peak

COOLDOWN_BARS = 30           # sit out this many bars after a stop-loss sell
MAX_SLIPPAGE_BPS = 100       # refuse a fill more than 1% past the close


class DipCatcher:
    """State for one run: the closes seen so far and the exit bookkeeping."""

    def __init__(self):
        self.closes = []
        self.peak_bps = 0      # best return, in bps, since the current buy
        self.cooldown = 0      # bars left before entries are allowed again
        self.tier = None       # "primary" or "fallback" for the open position

    def on_batch(self, state, batch):
        if state.warming_up:
            return []
        close = state.close(SYMBOL)
        if close is None:
            return []
        self.closes.append(close)
        holding = state.positions.get(SYMBOL)
        orders = []

        if holding is None or holding.qty == 0:
            if self.cooldown > 0:
                self.cooldown -= 1
                return []
            # Primary: a violent dip from the 60-minute high.
            if len(self.closes) >= PRIMARY_LOOKBACK:
                high = max(self.closes[-PRIMARY_LOOKBACK:])
                if close * 10000 < high * (10000 - PRIMARY_DIP_BPS):
                    self.tier = "primary"
                    self.peak_bps = 0
                    buy = self._buy(state, state.cash)
                    return [buy] if buy is not None else []
            # Fallback: late in the window, a shallower dip, half size.
            if state.seq >= FALLBACK_BAR and len(self.closes) >= FALLBACK_LOOKBACK:
                high = max(self.closes[-FALLBACK_LOOKBACK:])
                if close * 10000 < high * (10000 - FALLBACK_DIP_BPS):
                    self.tier = "fallback"
                    self.peak_bps = 0
                    buy = self._buy(state, state.cash // 2)
                    return [buy] if buy is not None else []
            return []

        # Exit first: take profit, stop loss, or trailing stop.  When an
        # exit fires, no top-up buy is sent on the same batch.
        value = state.value(SYMBOL, holding.qty)
        cost = holding.cost
        if cost > 0:
            ret_bps = (value - cost) * 10000 // cost
        else:
            ret_bps = 0
        if ret_bps > self.peak_bps:
            self.peak_bps = ret_bps
        sell = False
        if ret_bps >= TAKE_PROFIT_BPS:
            sell = True
        elif ret_bps <= -STOP_LOSS_BPS:
            sell = True
            self.cooldown = COOLDOWN_BARS
        elif self.peak_bps >= TRAIL_ARM_BPS and ret_bps <= self.peak_bps - TRAIL_GIVEBACK_BPS:
            sell = True
        if sell:
            orders.append(
                {
                    "side": "sell",
                    "symbol": SYMBOL,
                    "qty": holding.qty,
                    "max_slippage_bps": MAX_SLIPPAGE_BPS,
                }
            )
            self.tier = None
            self.peak_bps = 0
            return orders

        # Holding a fallback (half-size) position: top it up to full size
        # if the primary dip fires while it is held.
        if self.tier == "fallback" and state.cash >= 1_000_000:
            if len(self.closes) >= PRIMARY_LOOKBACK:
                high = max(self.closes[-PRIMARY_LOOKBACK:])
                if close * 10000 < high * (10000 - PRIMARY_DIP_BPS):
                    self.tier = "primary"
                    buy = self._buy(state, state.cash)
                    if buy is not None:
                        orders.append(buy)
        return orders

    @staticmethod
    def _buy(state, amount):
        """A buy of `amount` quote units, or None below the $1 minimum."""
        if amount < 1_000_000:
            return None
        return {
            "side": "buy",
            "symbol": SYMBOL,
            "notional_quote_units": amount,
            "max_slippage_bps": MAX_SLIPPAGE_BPS,
        }


def main():
    bot = DipCatcher()
    makefun_bars.run(bot.on_batch)


if __name__ == "__main__":
    main()
