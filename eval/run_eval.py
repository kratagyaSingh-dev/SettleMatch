"""Evaluate reconcile output against ground truth."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.reconcile import reconcile, write_outputs


def evaluate(
    settlements: str,
    bank: str,
    truth_path: str,
    threshold: float = 0.85,
) -> dict:
    result = reconcile(settlements, bank, confidence_threshold=threshold)
    truth = pd.read_csv(truth_path).fillna("")
    pred = {m["settlement_id"]: m["bank_txn_id"] for m in result.matches}

    correct = 0
    false_match = 0
    missed = 0
    true_exception_ok = 0

    for _, row in truth.iterrows():
        sid = row["settlement_id"]
        expected = str(row["bank_txn_id"]).strip()
        got = pred.get(sid)

        if expected == "":
            if got is None:
                true_exception_ok += 1
            else:
                false_match += 1
        else:
            if got == expected:
                correct += 1
            elif got is None:
                missed += 1
            else:
                false_match += 1

    total = len(truth)
    metrics = {
        **result.stats,
        "eval_correct_matches": correct,
        "eval_false_matches": false_match,
        "eval_missed_matches": missed,
        "eval_true_exceptions_respected": true_exception_ok,
        "eval_precision_like": round(
            correct / max(correct + false_match, 1), 4
        ),
        "eval_recall_like": round(correct / max(correct + missed, 1), 4),
        "ground_truth_rows": total,
    }
    return {"metrics": metrics, "result": result}


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--settlements", default="data/raw/settlements.csv")
    parser.add_argument("--bank", default="data/raw/bank.csv")
    parser.add_argument("--truth", default="data/expected/ground_truth.csv")
    parser.add_argument("--out", default="output")
    parser.add_argument("--threshold", type=float, default=0.85)
    args = parser.parse_args()

    payload = evaluate(args.settlements, args.bank, args.truth, args.threshold)
    paths = write_outputs(payload["result"], args.out)
    metrics_path = Path(args.out) / "eval_metrics.json"
    metrics_path.write_text(json.dumps(payload["metrics"], indent=2), encoding="utf-8")
    print(json.dumps(payload["metrics"], indent=2))
    print(f"Saved {metrics_path}")
    for k, v in paths.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
