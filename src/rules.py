"""Deterministic rule-based matcher (runs before AI)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

import pandas as pd

from src.collisions import (
    rule_amount_collision,
    rule_utr_collision,
    scan_input_collisions,
)


@dataclass
class RuleMatch:
    settlement_id: str
    bank_txn_id: str
    method: str
    reason: str
    confidence: float = 1.0


def _amount_equal(a: float, b: float, tol: float = 0.01) -> bool:
    return abs(float(a) - float(b)) <= tol


def match_by_exact_utr(
    settlements: pd.DataFrame,
    bank: pd.DataFrame,
    used_bank: set[str],
    collisions: list[dict],
) -> list[RuleMatch]:
    matches: list[RuleMatch] = []
    bank_by_utr: dict[str, list[pd.Series]] = {}
    for _, row in bank.iterrows():
        utr = row["utr_norm"]
        if not utr:
            continue
        bank_by_utr.setdefault(utr, []).append(row)

    for _, s in settlements.iterrows():
        utr = s["utr_norm"]
        if not utr or utr not in bank_by_utr:
            continue
        candidates = [
            r
            for r in bank_by_utr[utr]
            if r["bank_txn_id"] not in used_bank and _amount_equal(s["amount"], r["amount"])
        ]
        if len(candidates) == 1:
            b = candidates[0]
            used_bank.add(b["bank_txn_id"])
            matches.append(
                RuleMatch(
                    settlement_id=s["settlement_id"],
                    bank_txn_id=b["bank_txn_id"],
                    method="rule_exact_utr",
                    reason=f"Exact UTR {utr} and amount match",
                )
            )
        elif len(candidates) > 1:
            hit = rule_utr_collision(s["settlement_id"], utr, len(candidates))
            if hit:
                collisions.append(hit)
    return matches


def match_by_amount_date(
    settlements: pd.DataFrame,
    bank: pd.DataFrame,
    used_settlements: set[str],
    used_bank: set[str],
    collisions: list[dict],
    day_window: int = 1,
) -> list[RuleMatch]:
    matches: list[RuleMatch] = []
    open_settlements = settlements[~settlements["settlement_id"].isin(used_settlements)]

    for _, s in open_settlements.iterrows():
        if pd.isna(s["settled_at"]):
            continue
        candidates = []
        for _, b in bank.iterrows():
            if b["bank_txn_id"] in used_bank:
                continue
            if pd.isna(b["value_date"]):
                continue
            if not _amount_equal(s["amount"], b["amount"]):
                continue
            delta = abs((s["settled_at"] - b["value_date"]).days)
            if delta <= day_window:
                candidates.append(b)

        if len(candidates) == 1:
            b = candidates[0]
            used_bank.add(b["bank_txn_id"])
            used_settlements.add(s["settlement_id"])
            matches.append(
                RuleMatch(
                    settlement_id=s["settlement_id"],
                    bank_txn_id=b["bank_txn_id"],
                    method="rule_amount_date",
                    reason=f"Unique amount {s['amount']} within ±{day_window} day window",
                )
            )
        elif len(candidates) > 1:
            hit = rule_amount_collision(
                s["settlement_id"], float(s["amount"]), len(candidates)
            )
            if hit:
                collisions.append(hit)
    return matches


def run_rules(
    settlements: pd.DataFrame, bank: pd.DataFrame
) -> tuple[list[RuleMatch], set[str], set[str], list[dict]]:
    used_bank: set[str] = set()
    used_settlements: set[str] = set()
    collisions: list[dict] = list(scan_input_collisions(settlements, bank))

    utr_matches = match_by_exact_utr(settlements, bank, used_bank, collisions)
    for m in utr_matches:
        used_settlements.add(m.settlement_id)

    amount_date_matches = match_by_amount_date(
        settlements, bank, used_settlements, used_bank, collisions
    )
    return utr_matches + amount_date_matches, used_settlements, used_bank, collisions
