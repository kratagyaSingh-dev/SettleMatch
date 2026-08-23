"""Human-readable explanations for matches and refusals."""

from __future__ import annotations


def explain_match(match: dict) -> dict:
    method = match.get("method", "")
    conf = match.get("confidence", 0)
    reason = match.get("reason", "")

    if method == "rule_exact_utr":
        stage = "Rules engine"
        steps = [
            "Normalized UTR on settlement and bank row",
            "Verified exact UTR + amount match",
            "Single candidate only — no collision",
            "Auto-accepted (confidence 1.0)",
        ]
    elif method == "rule_amount_date":
        stage = "Rules engine"
        steps = [
            "No unique UTR match found",
            "Matched same amount within ±1 day window",
            "Only one bank candidate in window",
            "Auto-accepted (confidence 1.0)",
        ]
    elif method == "ai_gated":
        stage = "AI + confidence gate"
        steps = [
            "Rules could not safely match this row",
            f"AI proposed bank link: {match.get('bank_txn_id')}",
            f"Confidence {conf:.2f} passed gate threshold",
            "Gate approved — logged in audit trail",
        ]
    else:
        stage = "Reconciliation"
        steps = [reason or "Matched by pipeline"]

    return {
        "stage": stage,
        "summary": reason,
        "steps": steps,
        "confidence": conf,
        "method": method,
    }


def explain_exception(exc: dict) -> dict:
    reason = exc.get("reason", "")
    steps = [
        "Settlement could not be matched safely",
        f"Reason: {reason}",
        "Gate refused rather than guess",
        "Listed as honest exception for human review",
    ]
    if "collision" in reason.lower() or "conflict" in reason.lower():
        steps.insert(1, "Collision detector flagged ambiguous candidates")

    return {
        "stage": "Refused",
        "summary": reason,
        "steps": steps,
        "amount_at_risk_inr": exc.get("amount"),
    }
