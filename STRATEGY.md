# Strategy: Deep-dip V-catcher (btc-race-24h-20261115-0828)

## Measured edge

On the kit's published dev window (1,440 one-minute cbBTC/USDC bars,
BTC -4.0% over 24h) this bot's local replay nets **+$34.45** on $1,000
(grade-local with the kit's own harness confirms the same shape; see
NOTES.md for the exact figure). The dev board's leader sits at +$46.50,
so this is a top-of-board dev score, comfortably above the $0 dev gate.

The profit comes from one structure: a violent intraday V. In the dev
window BTC fell 2.0% in a single hour (hour 16) and then recovered 2.8%
in the next hour. The bot buys the dip and sells the recovery. Nothing
else in the window paid: buy-and-hold lost $44.00.

On 90 days of Binance BTCUSDT 1-minute closes (same price action, a
different venue; 358 overlapping 24h windows) the same rules average
about -$0.50 per window and trade in only ~13% of windows. That is the
honest expectation: this is a rare-trade sniper, not a positive-expectancy
grinder. The race window is unseen; the bot's job there is to (a) catch a
V if one happens, (b) cap each losing trade at about -3%, and (c) still
take at least one trade on a quiet window (the guardrail needs >= 1
trade). Places go to the ten highest net PnLs even when they are below
zero, so capping the downside matters as much as catching the upside.

## Entry rules

- PRIMARY: close >= 2.5% below the highest close of the last 60 minutes
  -> buy with all cash. A 2.5% hourly drawdown is violent; the round trip
  costs ~26 bps (4 bps fee + 2 bps slippage + ~15 bps pool impact each
  way), so the entry only fires on moves an order of magnitude larger
  than the cost.
- FALLBACK: from bar 1080 (last 6 hours) on, close >= 1.5% below the
  highest close of the last 120 minutes -> buy half the cash. Only fires
  if the primary never did, so the bot still meets the >= 1 trade
  guardrail on a quiet window.
- TOP-UP: a fallback (half-size) position is topped up to full size if
  the primary dip fires while it is held.
- After a stop-loss sell, entries pause for 30 bars.

## Exit rules (whole position)

- Take profit at +3.0% over cost.
- Stop loss at -3.0% under cost.
- Trailing stop: once the position's peak return reaches +2.0%, sell if
  it gives back 1.2% from that peak.
- Everything still held at the end is flattened by the replay at the
  last close (harness rule, not the bot's).

## Tried and dropped

- RSI(14) < 30 + Bollinger lower band (kit baseline shape): trades too
  often at 1-minute scale; the 26 bps round trip eats the small
  reversions. Negative on the 90-day out-of-sample check.
- EMA 8/21 cross: catastrophic out of sample (~-$133 per 24h window on
  average) -- 1-minute EMA crosses whipsaw ~70 times a day.
- Breakout momentum (buy new 60-min highs): negative on average
  (-$4.77 to -$7.68 per window); breakouts at 1-minute scale usually
  revert before the next open's fill.
- Small-dip buying (1.2-1.6% dips, 60-100 bps targets): more trades but
  negative expectancy; dips usually keep dipping and the wide stop
  needed to survive them costs more than the small targets earn.
- Buy-and-hold: -$44.00 on the dev window (BTC -4.0%).

## Expected outcomes

- Dev window: net PnL about +$30 (local replay +$34.45; the kit's
  grade-local is the authority). 2-3 trades, max drawdown ~2-4%.
- Race window: unknown. Best case a V like the dev window's (+$30ish);
  grind-down case a small number of -3% stops; quiet case one fallback
  half-size trade. The bot never risks more than ~3% per trade and never
  holds more than one position.
