"""Smoke test: reconcile + PDF/Word export + extract audit."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.export_report import build_pdf_report, build_word_report
from src.extract import extract_bytes
from src.reconcile import reconcile


def main() -> None:
    errors: list[str] = []

    # 1. Reconcile baseline
    s = ROOT / "data/raw/settlements.csv"
    b = ROOT / "data/raw/bank.csv"
    result = reconcile(s, b)
    stats = result.stats

    # 2. PDF + Word export (the Streamlit crash path)
    try:
        pdf = build_pdf_report(stats, result.matches, result.exceptions, {
            "settlements_source": "settlements.pdf",
            "bank_source": "bank.docx",
        })
        assert len(pdf) > 500, "PDF too small"
        (ROOT / "output/test_report.pdf").write_bytes(pdf)
        print(f"OK PDF export ({len(pdf)} bytes)")
    except Exception as exc:
        errors.append(f"PDF export: {exc}")

    try:
        docx = build_word_report(stats, result.matches, result.exceptions)
        assert len(docx) > 500, "Word too small"
        (ROOT / "output/test_report.docx").write_bytes(docx)
        print(f"OK Word export ({len(docx)} bytes)")
    except Exception as exc:
        errors.append(f"Word export: {exc}")

    # 3. Key format combos
    combos = [
        ("settlements.pdf", "bank.pdf", "settlements", "bank"),
        ("settlements.docx", "bank.docx", "settlements", "bank"),
        ("settlements.csv", "bank.docx", "settlements", "bank"),
    ]
    sample = ROOT / "data/samples"
    for sf, bf, sk, bk in combos:
        try:
            s_ex = extract_bytes((sample / sf).read_bytes(), sf, sk)
            b_ex = extract_bytes((sample / bf).read_bytes(), bf, bk)
            assert list(s_ex.dataframe.columns) == [
                "settlement_id", "payment_id", "amount", "currency", "utr", "settled_at", "status"
            ]
            assert list(b_ex.dataframe.columns) == [
                "bank_txn_id", "amount", "narration", "value_date", "utr"
            ]
            print(f"OK extract {sf} + {bf} ({s_ex.rows_found}/{b_ex.rows_found} rows, strict cols)")
        except Exception as exc:
            errors.append(f"extract {sf}+{bf}: {exc}")

    if errors:
        print("\nFAILED:")
        for e in errors:
            print(" -", e)
        sys.exit(1)

    print("\nAll smoke tests passed.")


if __name__ == "__main__":
    main()
