#!/usr/bin/env python3
"""Bitcoin price, four hours ahead: a one-line forecaster.

For every case file this script reads the minute-by-minute closes of
BTC/USDC, looks at where the price stands at the checkpoint and where it
stood four hours earlier, and answers with a single number: the price it
expects four hours after the checkpoint.

The answer is deliberately boring. Markets that have drifted away from
where they were tend, on average, to drift part of the way back, so the
forecast splits the difference between "nothing changes" and "the whole
move reverses": it takes the geometric mean of the checkpoint close and
the close 240 minutes before it. In other words, half of the log-return
over the last four hours is assumed to unwind over the next four.

    forecast = last_close * exp(-0.5 * log(last_close / close_240m_ago))

That is the entire model. There is no fitted parameter beyond the fixed
one-half, no look at the clock, no randomness, and no network access, so
two runs over the same inputs produce byte-identical outputs.

Usage: python3 main.py
  reads  *.in  from $MAKEFUN_INPUT_DIR (default /input/)
  writes <case>.out to $MAKEFUN_OUTPUT_DIR (default /output/)
"""

import json
import math
import os
import sys
from pathlib import Path

# How far back the reference close sits, in minutes.
REFERENCE_LAG_MINUTES = 240

# Fraction of the last four hours' log-move assumed to unwind.
REVERSION_FRACTION = 0.5

# A forecast is never allowed outside this band.
LOWEST_ALLOWED_PRICE = 0.00001
HIGHEST_ALLOWED_PRICE = 9999999.99999

# Answers are quoted to five places after the point.
DECIMAL_PLACES = 5


def pull_cases(folder):
    """Collect every case file in `folder`, in filename order.

    Returns a list of (case_id, closes) pairs. A case file must name a
    240-minute horizon and carry exactly one market; anything else is a
    data error and stops the run loudly instead of guessing.
    """
    paths = sorted(Path(folder).glob("*.in"))
    if not paths:
        raise RuntimeError(f"no .in case files found in {folder}")

    gathered = []
    for path in paths:
        with open(path, "r", encoding="utf-8") as handle:
            case = json.load(handle)

        if case.get("horizon_minutes") != REFERENCE_LAG_MINUTES:
            raise ValueError(
                f"{path.name}: horizon_minutes is "
                f"{case.get('horizon_minutes')}, expected "
                f"{REFERENCE_LAG_MINUTES}"
            )

        markets = case.get("markets")
        if not isinstance(markets, list) or len(markets) != 1:
            raise ValueError(
                f"{path.name}: expected exactly one market, found "
                f"{len(markets) if isinstance(markets, list) else markets!r}"
            )

        case_id = case.get("case")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError(f"{path.name}: missing or empty case id")

        gathered.append((case_id, markets[0].get("prices")))
    return gathered


def project_price(closes):
    """Forecast the price 240 minutes after the final close.

    When the history is too short to reach 240 minutes back, or the
    reference close is missing or not a usable positive number, the
    forecast simply repeats the latest close.
    """
    if not closes:
        raise ValueError("price series is empty")

    latest = float(closes[-1])

    reference = None
    if len(closes) > REFERENCE_LAG_MINUTES:
        try:
            candidate = float(closes[-1 - REFERENCE_LAG_MINUTES])
        except (TypeError, ValueError):
            candidate = None
        if candidate is not None and math.isfinite(candidate) and candidate > 0:
            reference = candidate

    if reference is None or latest <= 0 or not math.isfinite(latest):
        guess = latest
    else:
        log_move = math.log(latest / reference)
        guess = latest * math.exp(-REVERSION_FRACTION * log_move)

    guess = round(guess, DECIMAL_PLACES)
    return min(max(guess, LOWEST_ALLOWED_PRICE), HIGHEST_ALLOWED_PRICE)


def main():
    input_folder = os.environ.get("MAKEFUN_INPUT_DIR", "/input/")
    output_folder = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output/")
    Path(output_folder).mkdir(parents=True, exist_ok=True)

    for case_id, closes in pull_cases(input_folder):
        answer = project_price(closes)
        payload = {"forecasts": [{"case": case_id, "price": answer}]}
        out_path = Path(output_folder) / f"{case_id}.out"
        with open(out_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
            handle.write("\n")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError) as problem:
        print(f"error: {problem}", file=sys.stderr)
        raise SystemExit(1)
