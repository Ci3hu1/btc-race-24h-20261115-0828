# btc-race-24h-20261115-0828 — entry notes

## Bounty

- Slug: `btc-race-24h-20261115-0828` — "Race a BTC trading bot live for 24 hours"
- Prize: $250 USDC (escrow on-chain), 10 paid places: 1st $60, 2nd $40,
  3rd $30, 4th $25, 5th $20, 6th–10th $15 each.
- Entry fee: none (free). No prerequisites.
- Opened: 2026-11-15T08:28:00Z (15:28 WIB). Entries close:
  2026-11-15T14:28:00Z (21:28 WIB). Race runs 14:43Z 15 Nov – 14:43Z 16 Nov.
- Field at build time: 263 submissions, 18 ranked on the dev board;
  dev leader +$46.50 net PnL.

## Entry (v1, exact, awaiting Joni's 'Setuju')

- Repo: https://github.com/Ci3hu1/btc-race-24h-20261115-0828
- Commit: `d26aa1d0d33d33efd3ebead2033868b46b3a2fc3`
  (first commit `dd3f38d6776722bc4cb215318bd857e19749292d` + SPDX LICENSE fix)
- Title for submit: "Deep-dip V-catcher"
- Bot: `main.py` — pure stdlib Python, agent-fun/bars-replay/v1 via the
  kit's vendored shim. Buys 2.5% dips from the 60-min high with all cash;
  fallback half-size buy on a 1.5% dip from bar 1080; exits at +3% TP /
  -3% SL / trailing stop (arms +2%, gives back 1.2%); 30-bar cooldown
  after a stop-loss sell. See STRATEGY.md.

## Verification (all in this session, after opening)

- Unit tests: 7/7 pass (`python3 -m unittest discover -s tests -v`).
- Exact integer replay of the kit's harness fill math, driving the real
  bot twice over the dev window: **net PnL +$34.45, 3 trades, max
  drawdown 1.56%, deterministic** (identical action logs both runs).
  The kit's `grade-local --driver docker` cannot run here (no Docker on
  the VM; `--driver process` runs Node bots only), so the replay above
  re-implements the harness's `barsBuyFill`/`barsSellFill` exactly from
  `harness/harness-src.tar.gz` (sim/bars/engine.ts) in integer math.
- Out-of-sample honesty check: on 90 days of Binance BTCUSDT 1-min
  closes the same rules average ~-$0.50 per 24h window and trade in only
  ~13% of windows — the dev profit is one V-trade, not a grinder. The
  race window is unseen; the bot caps each losing trade at ~-3%.

## Kit check (2026-11-15T09:18Z, commit dd3f38d6)

- 12 passed, 2 failed, 4 skipped, 5 checked at submission.
- Passed: competition_open, snapshot, entrypoint, transcripts_present,
  transcripts_recorded, thinking_wellformed, thinking_in_window,
  thinking_reproduces (94.6% authored), thinking_on_task (4/4),
  thinking_turns (63), thinking_revised, transcripts_run_record.
- `license_osi` FAILED (no SPDX line) — FIXED in commit d26aa1d0
  (added `SPDX-License-Identifier: MIT` to LICENSE, pushed).
- `thinking_priced` FAILED (0 usage rows for this build's session
  `a661c99a-b7e4-4425-957e-b5645903f90b`): Muse writes a message's usage
  row once it is delivered, so the rows appear only after this turn ends.
  NEXT RUN must: re-run the muse.db SELECT for that agent_id, write the
  rows to `btc-race-24h-20261115-0828-muse-usage.jsonl`, re-bundle with
  `--muse-usage`, re-run `check` (expect 0 failures), then report this
  exact entry to Joni for 'Setuju' and submit only on it:
  `node cli/makefun.mjs submit --competition btc-race-24h-20261115-0828
  --repo-url https://github.com/Ci3hu1/btc-race-24h-20261115-0828
  --commit d26aa1d0d33d33efd3ebead2033868b46b3a2fc3
  --title "Deep-dip V-catcher" --bundle <transcripts.tar.gz>
  --keypair ~/workspace/tools/makefun/makefun-keypair.json`
  (bundle flags used: --system-prompt /tmp/sysprompt.txt --harness
  muse-app --harness-version 1 --provider meta --model muse-spark-1.3
  --effort default --mcp none --prompt-file /tmp/prompt-file.txt
  --prompt-origin scheduled --prompt-via "scheduled hourly make.fun
  bounty check (cron makefun-cek-bounty-baru-rutin)" --redact "Joni
  Gunawan" --redact "+62 85175067683" --redact "joni07683@gmail.com").
  Bundle from this run (pre-usage-rows):
  `~/workspace/tools/makefun/btc-race-24h-20261115-0828-transcripts.tar.gz`
  (sha256 b9cb004115137590eb7613dca30b18bdd48a7a4e8a981dbf79bee12b5606c762).
  NOTE: the bundle's session contains a truncated mention of the API key
  prefix (`af_Ljm...` in a thinking line); the full key value was stripped
  by bundle's credential redaction (verified: no full key in the bundle).

## Live scores

- Not submitted yet — no live score. After submit, read the dev grade
  (status route / GET /api/competitions/btc-race-24h-20261115-0828/live)
  and record live rank + live score here.
