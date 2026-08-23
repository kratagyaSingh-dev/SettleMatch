"""LLM fuzzy matcher — Gemini only for unmatched leftovers."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

import pandas as pd

try:
    import google.generativeai as genai
except ImportError:  # pragma: no cover
    genai = None


@dataclass
class AISuggestion:
    settlement_id: str
    bank_txn_id: str | None
    confidence: float
    reason: str
    refuse: bool
    raw_response: str


def _extract_json(text: str) -> dict:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            text = text[start : end + 1]
    return json.loads(text)


def _build_prompt(settlement: pd.Series, candidates: pd.DataFrame) -> str:
    cand_rows = []
    for _, c in candidates.iterrows():
        cand_rows.append(
            {
                "bank_txn_id": c["bank_txn_id"],
                "amount": float(c["amount"]),
                "value_date": str(c["value_date"].date()) if pd.notna(c["value_date"]) else None,
                "utr": c.get("utr", ""),
                "narration": c["narration"],
            }
        )
    settlement_payload = {
        "settlement_id": settlement["settlement_id"],
        "amount": float(settlement["amount"]),
        "settled_at": str(settlement["settled_at"].date())
        if pd.notna(settlement["settled_at"])
        else None,
        "utr": settlement.get("utr", ""),
        "payment_id": settlement.get("payment_id", ""),
    }
    return f"""You are a finance reconciliation assistant.
Decide if the settlement matches exactly one bank transaction.
If unsure, refuse. Never invent a bank_txn_id.

Settlement:
{json.dumps(settlement_payload, indent=2)}

Candidate bank rows:
{json.dumps(cand_rows, indent=2)}

Return ONLY valid JSON with this schema:
{{
  "bank_txn_id": "BK-xxxx or null",
  "confidence": 0.0,
  "reason": "short reason",
  "refuse": false
}}
"""


def _heuristic_suggestion(
    settlement: pd.Series, candidates: pd.DataFrame
) -> AISuggestion:
    """Offline fallback when no GEMINI_API_KEY — still demoable."""
    best_id = None
    best_score = 0.0
    best_reason = "No strong candidate"
    s_utr = str(settlement.get("utr_norm") or "")
    s_amt = float(settlement["amount"])

    for _, c in candidates.iterrows():
        score = 0.0
        reasons = []
        if abs(float(c["amount"]) - s_amt) <= 0.01:
            score += 0.45
            reasons.append("amount match")
        narr = str(c["narration"]).upper()
        if s_utr and s_utr in narr:
            score += 0.4
            reasons.append("UTR found in narration")
        elif s_utr and len(s_utr) >= 6 and s_utr[3:9] in narr:
            score += 0.4
            reasons.append("partial UTR in narration")
        if s_utr and s_utr == str(c.get("utr_norm") or ""):
            score += 0.35
            reasons.append("UTR field match")
        if pd.notna(settlement["settled_at"]) and pd.notna(c["value_date"]):
            delta = abs((settlement["settled_at"] - c["value_date"]).days)
            if delta <= 1:
                score += 0.15
                reasons.append("date within 1 day")
        if score > best_score:
            best_score = score
            best_id = c["bank_txn_id"]
            best_reason = ", ".join(reasons) or best_reason

    refuse = best_score < 0.7 or best_id is None
    return AISuggestion(
        settlement_id=settlement["settlement_id"],
        bank_txn_id=None if refuse else best_id,
        confidence=round(min(best_score, 0.99), 2),
        reason=best_reason if not refuse else f"Ambiguous/low score ({best_score:.2f})",
        refuse=refuse,
        raw_response="heuristic_fallback",
    )


class AIMatcher:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model_name = model or os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
        self._model = None
        if self.api_key and genai is not None:
            genai.configure(api_key=self.api_key)
            self._model = genai.GenerativeModel(self.model_name)

    @property
    def mode(self) -> str:
        return "gemini" if self._model is not None else "heuristic"

    def suggest(
        self, settlement: pd.Series, candidates: pd.DataFrame
    ) -> AISuggestion:
        if candidates.empty:
            return AISuggestion(
                settlement_id=settlement["settlement_id"],
                bank_txn_id=None,
                confidence=0.0,
                reason="No bank candidates left",
                refuse=True,
                raw_response="",
            )

        if self._model is None:
            return _heuristic_suggestion(settlement, candidates)

        prompt = _build_prompt(settlement, candidates)
        try:
            response = self._model.generate_content(prompt)
            raw = response.text or ""
            data = _extract_json(raw)
            bank_txn_id = data.get("bank_txn_id")
            if bank_txn_id in ("null", "", None):
                bank_txn_id = None
            valid_ids = set(candidates["bank_txn_id"].astype(str))
            if bank_txn_id is not None and str(bank_txn_id) not in valid_ids:
                return AISuggestion(
                    settlement_id=settlement["settlement_id"],
                    bank_txn_id=None,
                    confidence=0.0,
                    reason="Model proposed invalid bank_txn_id — refused",
                    refuse=True,
                    raw_response=raw,
                )
            return AISuggestion(
                settlement_id=settlement["settlement_id"],
                bank_txn_id=bank_txn_id,
                confidence=float(data.get("confidence", 0)),
                reason=str(data.get("reason", "")),
                refuse=bool(data.get("refuse", False)) or bank_txn_id is None,
                raw_response=raw,
            )
        except Exception as exc:  # noqa: BLE001 — fall back so demo still works
            err = str(exc)
            # Quota / model / network failures → safe offline matcher
            if any(
                token in err.lower()
                for token in ("429", "quota", "404", "not available", "resource exhausted")
            ):
                fb = _heuristic_suggestion(settlement, candidates)
                fb.reason = f"Gemini unavailable — heuristic fallback: {fb.reason}"
                fb.raw_response = f"fallback_after_error: {err[:200]}"
                return fb
            return AISuggestion(
                settlement_id=settlement["settlement_id"],
                bank_txn_id=None,
                confidence=0.0,
                reason=f"AI call failed: {exc}",
                refuse=True,
                raw_response=str(exc),
            )


def top_candidates(
    settlement: pd.Series,
    bank: pd.DataFrame,
    used_bank: set[str],
    limit: int = 5,
) -> pd.DataFrame:
    open_bank = bank[~bank["bank_txn_id"].isin(used_bank)].copy()
    if open_bank.empty:
        return open_bank

    s_amt = float(settlement["amount"])
    open_bank["amount_diff"] = (open_bank["amount"] - s_amt).abs()
    if pd.notna(settlement["settled_at"]):
        open_bank["date_diff"] = open_bank["value_date"].apply(
            lambda d: abs((settlement["settled_at"] - d).days) if pd.notna(d) else 999
        )
    else:
        open_bank["date_diff"] = 999

    open_bank = open_bank.sort_values(["amount_diff", "date_diff"])
    return open_bank.head(limit)
