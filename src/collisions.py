"""Collision detection — refuse ambiguous or duplicate money links."""

from __future__ import annotations

import pandas as pd


def scan_input_collisions(
    settlements: pd.DataFrame, bank: pd.DataFrame
) -> list[dict]:
    """Pre-run scan for duplicate UTRs and competing bank rows."""
    found: list[dict] = []

    # Duplicate settlement UTRs with different amounts
    if "utr_norm" in settlements.columns:
        utr_groups = settlements[settlements["utr_norm"].astype(str).str.len() > 0].groupby(
            "utr_norm"
        )
        for utr, grp in utr_groups:
            if len(grp) > 1 and grp["amount"].nunique() > 1:
                found.append(
                    {
                        "type": "duplicate_settlement_utr",
                        "settlement_id": ",".join(grp["settlement_id"].astype(str).tolist()[:3]),
                        "detail": f"UTR {utr} appears on {len(grp)} settlements with different amounts",
                    }
                )

    # Duplicate bank UTRs
    if "utr_norm" in bank.columns:
        bank_utr = bank[bank["utr_norm"].astype(str).str.len() > 0].groupby("utr_norm")
        for utr, grp in bank_utr:
            if len(grp) > 1:
                found.append(
                    {
                        "type": "duplicate_bank_utr",
                        "bank_txn_id": ",".join(grp["bank_txn_id"].astype(str).tolist()[:3]),
                        "detail": f"UTR {utr} on {len(grp)} bank rows — matching blocked until resolved",
                    }
                )

    return found


def rule_utr_collision(
    settlement_id: str, utr: str, candidate_count: int
) -> dict | None:
    if candidate_count > 1:
        return {
            "type": "ambiguous_utr_match",
            "settlement_id": settlement_id,
            "detail": f"{candidate_count} bank rows share UTR {utr} — refused (collision)",
        }
    return None


def rule_amount_collision(
    settlement_id: str, amount: float, candidate_count: int
) -> dict | None:
    if candidate_count > 1:
        return {
            "type": "ambiguous_amount_date",
            "settlement_id": settlement_id,
            "detail": f"{candidate_count} bank rows with amount {amount} in date window — refused",
        }
    return None
