"""Confidence gate — refuse low-confidence or conflicting AI suggestions."""

from __future__ import annotations

import os
from dataclasses import dataclass

from src.ai_matcher import AISuggestion


@dataclass
class GateDecision:
    accepted: bool
    settlement_id: str
    bank_txn_id: str | None
    confidence: float
    reason: str
    method: str = "ai_gated"


def apply_gate(
    suggestion: AISuggestion,
    threshold: float | None = None,
    used_bank: set[str] | None = None,
) -> GateDecision:
    threshold = (
        threshold
        if threshold is not None
        else float(os.getenv("CONFIDENCE_THRESHOLD", "0.85"))
    )
    used_bank = used_bank or set()

    if suggestion.refuse or suggestion.bank_txn_id is None:
        return GateDecision(
            accepted=False,
            settlement_id=suggestion.settlement_id,
            bank_txn_id=None,
            confidence=suggestion.confidence,
            reason=suggestion.reason or "AI refused to match",
        )

    if suggestion.bank_txn_id in used_bank:
        return GateDecision(
            accepted=False,
            settlement_id=suggestion.settlement_id,
            bank_txn_id=suggestion.bank_txn_id,
            confidence=suggestion.confidence,
            reason="Bank txn already matched — conflict refused",
        )

    if suggestion.confidence < threshold:
        return GateDecision(
            accepted=False,
            settlement_id=suggestion.settlement_id,
            bank_txn_id=suggestion.bank_txn_id,
            confidence=suggestion.confidence,
            reason=f"Below threshold {threshold}: confidence={suggestion.confidence}",
        )

    return GateDecision(
        accepted=True,
        settlement_id=suggestion.settlement_id,
        bank_txn_id=suggestion.bank_txn_id,
        confidence=suggestion.confidence,
        reason=suggestion.reason,
    )
