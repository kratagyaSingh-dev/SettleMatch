"""CLI entry: run reconciliation and print report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

from src.reconcile import reconcile, write_outputs


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="SettleMatch reconciliation")
    parser.add_argument(
        "--settlements",
        default="data/raw/settlements.csv",
    )
    parser.add_argument("--bank", default="data/raw/bank.csv")
    parser.add_argument("--out", default="output")
    parser.add_argument("--threshold", type=float, default=0.85)
    args = parser.parse_args()

    result = reconcile(args.settlements, args.bank, confidence_threshold=args.threshold)
    paths = write_outputs(result, args.out)
    print(json.dumps(result.stats, indent=2))
    print("Wrote:")
    for name, path in paths.items():
        print(f"  {name}: {path}")


if __name__ == "__main__":
    main()
