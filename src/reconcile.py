"""End-to-end reconciliation orchestrator."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.ai_matcher import AIMatcher, top_candidates
from src.explain import explain_match
from src.gate import apply_gate
from src.ingest import load_bank, load_settlements
from src.rules import run_rules


@dataclass
class AuditEvent:
    ts: str
    settlement_id: str
    bank_txn_id: str | None
    stage: str
    method: str
    accepted: bool
    confidence: float
    reason: str


@dataclass
class ReconcileResult:
    matches: list[dict] = field(default_factory=list)
    exceptions: list[dict] = field(default_factory=list)
    collisions: list[dict] = field(default_factory=list)
    audit: list[AuditEvent] = field(default_factory=list)
    stats: dict = field(default_factory=dict)
    ai_mode: str = "heuristic"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_match(result: ReconcileResult, m: dict) -> None:
    enriched = {**m, "explanation": explain_match(m)}
    result.matches.append(enriched)


def reconcile(
    settlements_path: str | Path,
    bank_path: str | Path,
    ai: AIMatcher | None = None,
    confidence_threshold: float = 0.85,
) -> ReconcileResult:
    settlements = load_settlements(settlements_path)
    bank = load_bank(bank_path)
    ai = ai or AIMatcher()
    result = ReconcileResult(ai_mode=ai.mode)

    rule_matches, used_settlements, used_bank, collisions = run_rules(settlements, bank)
    result.collisions = collisions

    for m in rule_matches:
        row = {
            "settlement_id": m.settlement_id,
            "bank_txn_id": m.bank_txn_id,
            "method": m.method,
            "confidence": m.confidence,
            "reason": m.reason,
        }
        _append_match(result, row)
        result.audit.append(
            AuditEvent(
                ts=_now(),
                settlement_id=m.settlement_id,
                bank_txn_id=m.bank_txn_id,
                stage="rules",
                method=m.method,
                accepted=True,
                confidence=m.confidence,
                reason=m.reason,
            )
        )

    open_settlements = settlements[~settlements["settlement_id"].isin(used_settlements)]
    for _, s in open_settlements.iterrows():
        sid = s["settlement_id"]

        cands = top_candidates(s, bank, used_bank, limit=5)
        suggestion = ai.suggest(s, cands)
        decision = apply_gate(
            suggestion, threshold=confidence_threshold, used_bank=used_bank
        )
        result.audit.append(
            AuditEvent(
                ts=_now(),
                settlement_id=sid,
                bank_txn_id=decision.bank_txn_id,
                stage="ai",
                method="ai_gated",
                accepted=decision.accepted,
                confidence=decision.confidence,
                reason=decision.reason,
            )
        )
        if decision.accepted and decision.bank_txn_id:
            used_bank.add(decision.bank_txn_id)
            used_settlements.add(sid)
            _append_match(
                result,
                {
                    "settlement_id": sid,
                    "bank_txn_id": decision.bank_txn_id,
                    "method": "ai_gated",
                    "confidence": decision.confidence,
                    "reason": decision.reason,
                },
            )
        else:
            if "conflict" in decision.reason.lower() or "already matched" in decision.reason.lower():
                result.collisions.append(
                    {
                        "type": "bank_txn_conflict",
                        "settlement_id": sid,
                        "bank_txn_id": decision.bank_txn_id,
                        "detail": decision.reason,
                    }
                )
            result.exceptions.append(
                {
                    "settlement_id": sid,
                    "amount": float(s["amount"]),
                    "utr": s.get("utr", ""),
                    "reason": decision.reason,
                    "ai_confidence": decision.confidence,
                }
            )

    matched_ids = {m["settlement_id"] for m in result.matches}
    matched_amount = float(
        settlements[settlements["settlement_id"].isin(matched_ids)]["amount"].sum()
    )
    total_amount = float(settlements["amount"].sum())
    at_risk = float(
        sum(e.get("amount", 0) for e in result.exceptions)
    )
    total = len(settlements)
    rule_count = sum(1 for m in result.matches if m["method"].startswith("rule_"))
    ai_count = sum(1 for m in result.matches if m["method"] == "ai_gated")

    result.stats = {
        "total_settlements": total,
        "matched": len(result.matches),
        "exceptions": len(result.exceptions),
        "collisions_detected": len(result.collisions),
        "match_rate": round(len(result.matches) / total, 4) if total else 0.0,
        "rule_matches": rule_count,
        "ai_matches": ai_count,
        "money_matched_inr": round(matched_amount, 2),
        "money_at_risk_inr": round(at_risk, 2),
        "total_settlement_inr": round(total_amount, 2),
        "recovery_rate": round(matched_amount / total_amount, 4) if total_amount else 0.0,
        "ai_mode": ai.mode,
        "confidence_threshold": confidence_threshold,
    }
    return result


def simulate_thresholds(
    settlements_path: str | Path,
    bank_path: str | Path,
    thresholds: list[float] | None = None,
    ai: AIMatcher | None = None,
) -> list[dict]:
    """Run quick threshold comparison for feature #11."""
    thresholds = thresholds or [0.65, 0.75, 0.85, 0.95]
    ai = ai or AIMatcher()
    rows = []
    for t in thresholds:
        r = reconcile(settlements_path, bank_path, ai=ai, confidence_threshold=t)
        rows.append(
            {
                "threshold": t,
                "match_rate": r.stats["match_rate"],
                "matched": r.stats["matched"],
                "exceptions": r.stats["exceptions"],
                "ai_matches": r.stats["ai_matches"],
                "money_matched_inr": r.stats["money_matched_inr"],
                "recovery_rate": r.stats["recovery_rate"],
            }
        )
    return rows


def write_outputs(result: ReconcileResult, out_dir: str | Path) -> dict[str, Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    report_path = out / "report.json"
    exceptions_path = out / "exceptions.csv"
    matches_path = out / "matches.csv"
    audit_path = out / "audit_log.jsonl"
    collisions_path = out / "collisions.json"

    report_path.write_text(json.dumps(result.stats, indent=2), encoding="utf-8")
    pd.DataFrame(result.exceptions).to_csv(exceptions_path, index=False)
    pd.DataFrame(result.matches).to_csv(matches_path, index=False)
    collisions_path.write_text(json.dumps(result.collisions, indent=2), encoding="utf-8")
    with audit_path.open("w", encoding="utf-8") as f:
        for event in result.audit:
            f.write(json.dumps(asdict(event)) + "\n")

    return {
        "report": report_path,
        "exceptions": exceptions_path,
        "matches": matches_path,
        "audit": audit_path,
        "collisions": collisions_path,
    }
