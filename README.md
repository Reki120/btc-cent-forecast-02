# btc-cent-forecast-01 — Bitcoin price 4 hours ahead

Entry for make.fun's "Forecast Bitcoin's price 4 hours ahead, 12 times
over 48 hours" bounty ($250 in USDC, escrowed).

## Method

Absolute-error scoring makes the median of the predictive distribution
the optimal point forecast. The model is 4-hour mean reversion with
shrinkage:

```
forecast = sqrt(last_close * close_240_min_ago)
```

i.e. half of the last 4 hours' log-move is expected to retrace over the
next 4 hours. The reversion signal is small but consistent: over 115
four-hourly checkpoints (Coinbase BTC-USD 5-minute candles,
23 Oct – 11 Nov 2026) a half-reversion forecast beat persistence by
~101 cents on average (paired t ≈ 1.5), with a ~65% chance of beating
the persistence baseline on a simulated 12-case final. The factor 0.5
is deliberate shrinkage — the signal is weak, so only half of it is
taken. Pure persistence can never beat the house baseline (it *is*
persistence), and last-hour momentum extrapolation, which looked strong
on the 6 practice cases, lost badly on the 115-checkpoint backtest and
was rejected.

`main.py` is Python 3.13, standard library only, no network, fully
deterministic. It reads every `*.in` in `$MAKEFUN_INPUT_DIR` (else
`/input/`) and writes one `*.out` per case to `$MAKEFUN_OUTPUT_DIR`
(else `/output/`), exactly `{"forecasts": [{"case": <id>,
"price": <guess>}]}`.

## Practice scores (cents, mean absolute error)

Practice answers p00–p04 are exact: each is the next case's last price
(the close at `at` + 240). p05's answer (06:00 UTC 11 Nov) is not in
the kit; it is estimated from the Coinbase BTC-USD 1-minute close at
06:00 (73,828.06) minus the median Coinbase-minus-Orca offset at the
five known answer minutes (−34.30), giving 73,862.36. That estimate
reproduces the house baseline's stated practice mean (44,521.58) to
within 35 cents, so it is good for model selection.

| case | persistence | this model |
|------|-------------|------------|
| p00  | 31,711.1    | 44,306.7   |
| p01  | 76,696.8    | 92,535.5   |
| p02  | 47,033.4    | 85,282.5   |
| p03  | 56,685.0    | 33,205.9   |
| p04  | 23,147.0    | 5,250.1    |
| p05* | 31,647.4    | 20,083.0   |
| mean | 44,486.8    | 46,777.3   |

*estimated answer. On the 6 practice cases the model trails
persistence by ~5%: 10–11 Nov was a steady downtrend day, and mean
reversion bets against the trend. The model was chosen on the
115-checkpoint backtest across three weeks and several regimes, not on
these 6 cases — 6 cases overfit easily, and the task's own rules warn
that a practice score is no guide to the final.

Backtest (Coinbase 5-minute candles, 115 checkpoints, 23 Oct – 11 Nov):

| model | mean cents |
|-------|-----------|
| persistence | 40,664.6 |
| half-reversion (this model) | 40,563.1 |
| full reversion | 40,467.4 |
| last-hour momentum x0.25 | 49,615.0 |
| median 240-min return, 72 h | 41,600.9 |
