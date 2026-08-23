"""Audit all settlement x bank format combinations."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.extract import extract_bytes, required_columns, save_extracted
from src.reconcile import reconcile

FORMATS = ["csv", "xlsx", "pdf", "docx", "txt"]
SAMPLE_DIR = ROOT / "data" / "samples"
OUT = ROOT / "output" / "audit"
EXPECTED_SETTLEMENTS = 100


def audit_combo(s_fmt: str, b_fmt: str) -> dict:
    s_path = SAMPLE_DIR / f"settlements.{s_fmt}"
    b_path = SAMPLE_DIR / f"bank.{b_fmt}"
    label = f"settlements.{s_fmt} + bank.{b_fmt}"

    if not s_path.exists() or not b_path.exists():
        return {"combo": label, "status": "SKIP", "error": "sample file missing"}

    try:
        s_ex = extract_bytes(s_path.read_bytes(), s_path.name, "settlements")
        b_ex = extract_bytes(b_path.read_bytes(), b_path.name, "bank")

        s_cols = list(s_ex.dataframe.columns)
        b_cols = list(b_ex.dataframe.columns)
        s_req = required_columns("settlements")
        b_req = required_columns("bank")

        col_ok = s_cols == s_req and b_cols == b_req
        extra_s = set(s_cols) - set(s_req)
        extra_b = set(b_cols) - set(b_req)

        OUT.mkdir(parents=True, exist_ok=True)
        s_csv = save_extracted(s_ex, OUT / f"s_{s_fmt}.csv")
        b_csv = save_extracted(b_ex, OUT / f"b_{b_fmt}.csv")

        result = reconcile(s_csv, b_csv, confidence_threshold=0.85)
        stats = result.stats

        row_ok = s_ex.rows_found >= EXPECTED_SETTLEMENTS * 0.9  # PDF may lose a few

        status = "PASS"
        notes = []
        if not col_ok:
            status = "FAIL"
            notes.append(f"extra cols s={extra_s} b={extra_b}")
        if not row_ok:
            status = "WARN"
            notes.append(f"settlement rows {s_ex.rows_found} (expected ~{EXPECTED_SETTLEMENTS})")
        if stats.get("match_rate", 0) < 0.5 and s_fmt != "pdf":
            status = "WARN" if status == "PASS" else status
            notes.append(f"low match rate {stats.get('match_rate')}")

        return {
            "combo": label,
            "status": status,
            "settlement_rows": s_ex.rows_found,
            "bank_rows": b_ex.rows_found,
            "settlement_cols": s_cols,
            "bank_cols": b_cols,
            "columns_strict": col_ok,
            "match_rate": stats.get("match_rate"),
            "matched": stats.get("matched"),
            "exceptions": stats.get("exceptions"),
            "notes": notes,
        }
    except Exception as exc:
        return {"combo": label, "status": "FAIL", "error": str(exc)}


def main() -> None:
    if not SAMPLE_DIR.exists():
        print("Run: python scripts/generate_sample_docs.py first")
        sys.exit(1)

    results = []
    for s_fmt in FORMATS:
        for b_fmt in FORMATS:
            results.append(audit_combo(s_fmt, b_fmt))

    report_path = OUT / "extract_audit.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    passed = sum(1 for r in results if r["status"] == "PASS")
    warned = sum(1 for r in results if r["status"] == "WARN")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    skipped = sum(1 for r in results if r["status"] == "SKIP")

    print(f"\n=== EXTRACT AUDIT ({len(results)} combinations) ===\n")
    for r in results:
        icon = {"PASS": "OK", "WARN": "!!", "FAIL": "XX", "SKIP": "--"}.get(r["status"], "?")
        line = f"[{icon}] {r['combo']}"
        if r["status"] in ("PASS", "WARN"):
            line += (
                f" | s_rows={r.get('settlement_rows')} b_rows={r.get('bank_rows')}"
                f" | cols_strict={r.get('columns_strict')}"
                f" | match={r.get('match_rate')}"
            )
            if r.get("notes"):
                line += f" | {', '.join(r['notes'])}"
        else:
            line += f" | {r.get('error', '')}"
        print(line)

    print(f"\nSummary: PASS={passed} WARN={warned} FAIL={failed} SKIP={skipped}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
