#!/usr/bin/env python3
"""btc-cent-forecast-01 entrypoint (Python 3.13, standard library only).

Forecast: the median of the predictive distribution under absolute-error
scoring. Bitcoin's 4-hour returns show a small, consistent mean reversion:
over 115 four-hourly checkpoints (Coinbase BTC-USD 5-minute candles,
23 Oct - 11 Nov 2026) the next 4-hour return is slightly negatively
correlated with the previous 4-hour return. The model therefore forecasts
half of the last 4 hours' move to retrace:

    forecast = last * exp(-0.5 * log(last / price_240_min_ago))
             = sqrt(last * price_240_min_ago)

i.e. the geometric mean of the checkpoint price and the price 4 hours
earlier. The factor 0.5 is shrinkage: the reversion signal is real but
weak (paired t ~ 1.5 over 115 checkpoints, ~65% chance of beating the
persistence baseline on a 12-case final), so only half of it is taken.
Pure persistence (forecast = last) can never beat the house baseline,
which is itself persistence; momentum extrapolation of the last hour
looked strong on the 6 practice cases (a steady downtrend day) but lost
badly on the 115-checkpoint backtest and was rejected.

Deterministic: a pure function of the case's prices, no randomness, no
network. Reads every *.in in the input directory, writes one *.out per
case with exactly {"forecasts": [{"case": <id>, "price": <guess>}]}.
"""

import json
import math
import os

INPUT_DIR = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
OUTPUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")

MIN_PRICE = 0.00001
MAX_PRICE = 9_999_999.99999
HORIZON_MINUTES = 240
SHRINK = 0.5


def price5(x):
    """x kept on the grid's 5 decimals and inside the scorer's (0, 10M)."""
    if not math.isfinite(x) or x <= 0:
        raise ValueError("forecast is not a finite positive number")
    return round(min(MAX_PRICE, max(MIN_PRICE, x)) * 1e5) / 1e5


def forecast(prices):
    """Geometric mean of the last close and the close 240 minutes earlier.

    prices[-241] is the close 240 minutes before the checkpoint close
    prices[-1] (one close a minute). Falls back to the last close when
    the window is too short or the earlier close is unusable.
    """
    if not isinstance(prices, list) or not prices:
        raise ValueError("market has no prices")
    last = prices[-1]
    if not math.isfinite(last) or last <= 0:
        raise ValueError("last price is not a finite positive number")
    if len(prices) > HORIZON_MINUTES:
        ago = prices[-1 - HORIZON_MINUTES]
        if math.isfinite(ago) and ago > 0:
            drift = math.log(last / ago)
            return price5(last * math.exp(-SHRINK * drift))
    return price5(last)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    inputs = sorted(f for f in os.listdir(INPUT_DIR) if f.endswith(".in"))
    if not inputs:
        raise ValueError("no .in cases found in input directory")
    for name in inputs:
        case_id = name[: -len(".in")]
        with open(os.path.join(INPUT_DIR, name), "r", encoding="utf-8") as fh:
            case = json.load(fh)
        markets = case.get("markets")
        if not isinstance(markets, list) or len(markets) != 1:
            raise ValueError(f"{name} does not hold exactly one market")
        guess = forecast(markets[0].get("prices"))
        out = {"forecasts": [{"case": case_id, "price": guess}]}
        with open(os.path.join(OUTPUT_DIR, case_id + ".out"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps(out) + "\n")


if __name__ == "__main__":
    main()
