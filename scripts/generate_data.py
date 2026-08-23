"""Generate synthetic settlements, bank rows, and ground-truth labels."""

from __future__ import annotations

import argparse
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

RNG = random.Random(42)


def _utr() -> str:
    return "UTR" + "".join(str(RNG.randint(0, 9)) for _ in range(10))


def generate(n: int = 100) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Mix:
      ~55 exact UTR
      ~20 amount+date (UTR missing on bank)
      ~15 messy narration (AI zone)
      ~10 true exceptions
    """
    n_exact = int(n * 0.55)
    n_amount_date = int(n * 0.20)
    n_messy = int(n * 0.15)
    n_ex = n - n_exact - n_amount_date - n_messy

    settlements = []
    bank = []
    truth = []
    base = date(2026, 8, 1)
    bank_id = 1

    def add_settlement(i: int, amount: float, settled: date, utr: str, status="settled"):
        sid = f"SET-{i:03d}"
        settlements.append(
            {
                "settlement_id": sid,
                "payment_id": f"pay_{1000 + i}",
                "amount": round(amount, 2),
                "currency": "INR",
                "utr": utr,
                "settled_at": settled.isoformat(),
                "status": status,
            }
        )
        return sid

    i = 1
    # Exact UTR matches
    for _ in range(n_exact):
        amount = RNG.choice([499, 999, 1499, 2500, 4999, 12000]) + RNG.random()
        amount = round(amount, 2)
        settled = base + timedelta(days=RNG.randint(0, 20))
        utr = _utr()
        sid = add_settlement(i, amount, settled, utr)
        bid = f"BK-{bank_id:04d}"
        bank_id += 1
        bank.append(
            {
                "bank_txn_id": bid,
                "amount": amount,
                "narration": f"NEFT RAZORPAY {utr}",
                "value_date": settled.isoformat(),
                "utr": utr,
            }
        )
        truth.append({"settlement_id": sid, "bank_txn_id": bid, "label": "exact_utr"})
        i += 1

    # Amount + date, UTR blank on bank
    for _ in range(n_amount_date):
        amount = round(RNG.uniform(200, 8000), 2)
        settled = base + timedelta(days=RNG.randint(0, 20))
        utr = _utr()
        sid = add_settlement(i, amount, settled, utr)
        bid = f"BK-{bank_id:04d}"
        bank_id += 1
        bank.append(
            {
                "bank_txn_id": bid,
                "amount": amount,
                "narration": f"RAZORPAY SETTLEMENT pay_{1000 + i}",
                "value_date": (settled + timedelta(days=RNG.choice([0, 1]))).isoformat(),
                "utr": "",
            }
        )
        truth.append({"settlement_id": sid, "bank_txn_id": bid, "label": "amount_date"})
        i += 1

    # Messy narration — partial UTR / OCR noise (AI zone).
    # Add a same-amount distractor in the date window so rules cannot uniquely match.
    for _ in range(n_messy):
        amount = round(RNG.uniform(300, 6000), 2)
        settled = base + timedelta(days=RNG.randint(0, 20))
        utr = _utr()
        sid = add_settlement(i, amount, settled, utr)
        bid = f"BK-{bank_id:04d}"
        bank_id += 1
        partial = utr[3:9]
        bank.append(
            {
                "bank_txn_id": bid,
                "amount": amount,
                "narration": f"RZP CR {partial} MERCHANT PAYOUT",
                "value_date": settled.isoformat(),
                "utr": "",
            }
        )
        # Distractor: same amount, nearby date, no UTR hint → blocks rule_amount_date
        distractor = f"BK-{bank_id:04d}"
        bank_id += 1
        bank.append(
            {
                "bank_txn_id": distractor,
                "amount": amount,
                "narration": "GENERIC NEFT CREDIT",
                "value_date": (settled + timedelta(days=RNG.choice([0, 1]))).isoformat(),
                "utr": "",
            }
        )
        truth.append({"settlement_id": sid, "bank_txn_id": bid, "label": "messy_ai"})
        i += 1

    # True exceptions — no correct bank row (or conflicting)
    for _ in range(n_ex):
        amount = round(RNG.uniform(500, 9000), 2)
        settled = base + timedelta(days=RNG.randint(0, 20))
        utr = _utr()
        sid = add_settlement(i, amount, settled, utr)
        # distractor with same amount different day, or missing credit
        if RNG.random() < 0.5:
            bid = f"BK-{bank_id:04d}"
            bank_id += 1
            bank.append(
                {
                    "bank_txn_id": bid,
                    "amount": amount,
                    "narration": "UNRELATED UPI CREDIT",
                    "value_date": (settled + timedelta(days=5)).isoformat(),
                    "utr": _utr(),
                }
            )
        truth.append({"settlement_id": sid, "bank_txn_id": "", "label": "exception"})
        i += 1

    # Noise bank rows
    for _ in range(15):
        bid = f"BK-{bank_id:04d}"
        bank_id += 1
        bank.append(
            {
                "bank_txn_id": bid,
                "amount": round(RNG.uniform(100, 3000), 2),
                "narration": RNG.choice(["SALARY", "UPI/merchant", "ATM WDL", "IMPS"]),
                "value_date": (base + timedelta(days=RNG.randint(0, 25))).isoformat(),
                "utr": _utr() if RNG.random() > 0.5 else "",
            }
        )

    RNG.shuffle(bank)
    return pd.DataFrame(settlements), pd.DataFrame(bank), pd.DataFrame(truth)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=100)
    parser.add_argument("--out", default="data")
    args = parser.parse_args()

    raw = Path(args.out) / "raw"
    expected = Path(args.out) / "expected"
    raw.mkdir(parents=True, exist_ok=True)
    expected.mkdir(parents=True, exist_ok=True)

    settlements, bank, truth = generate(args.n)
    settlements.to_csv(raw / "settlements.csv", index=False)
    bank.to_csv(raw / "bank.csv", index=False)
    truth.to_csv(expected / "ground_truth.csv", index=False)
    print(f"Wrote {len(settlements)} settlements, {len(bank)} bank rows -> {raw}")
    print(f"Ground truth -> {expected / 'ground_truth.csv'}")


if __name__ == "__main__":
    main()
