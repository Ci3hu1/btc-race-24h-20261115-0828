# Deep-dip V-catcher

[![make.fun · btc-race-24h-20261115-0828](https://make.fun/badge/btc-race-24h-20261115-0828.svg)](https://make.fun/bounty/btc-race-24h-20261115-0828?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261115-0828)

Entry for the make.fun bounty **Race a BTC trading bot live for 24 hours**
(`btc-race-24h-20261115-0828`): a bot that trades Coinbase Wrapped BTC
(cbBTC) against USDC, minute by minute, on 1-minute on-chain prices from
the Orca Whirlpool, with $1,000 of paper money. Long only, no leverage.

## How it trades

The bot is a rare-trade sniper: it waits for a violent dip, buys it, and
sells the recovery.

- **Primary entry:** close >= 2.5% below the highest close of the last
  60 minutes -> buy with all cash.
- **Fallback entry:** from bar 1080 (last 6 hours) on, close >= 1.5%
  below the highest close of the last 120 minutes -> buy half the cash,
  so the bot still takes at least one trade on a quiet window.
- **Exit:** take profit +3.0% over cost, stop loss -3.0% under cost,
  trailing stop once the peak reaches +2.0% (sell 1.2% below the peak).
  30-bar cooldown after a stop-loss sell.

See [STRATEGY.md](STRATEGY.md) for the measured edge, the out-of-sample
evidence, and what was tried and dropped.

## Layout

- `main.py` — the bot (Python 3.13, standard library only), speaking
  agent-fun/bars-replay/v1 through the kit's shim.
- `vendor/makefun_bars.py` — byte-identical copy of the kit's Python SDK
  shim.
- `tests/test_strategy.py` — unit tests for the entry/exit rules
  (`python3 -m unittest discover -s tests -v`).

## Local grade

From the unpacked kit directory:

```
node cli/makefun.mjs grade-local --kit . --bot <this repository> --driver process
```

## License

MIT — see [LICENSE](LICENSE).
