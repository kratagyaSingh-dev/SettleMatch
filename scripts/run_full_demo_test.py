"""Generate all demo files + run key combination tests + save report."""

from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.export_report import build_pdf_report, build_word_report
from src.extract import extract_bytes, required_columns, save_extracted
from src.reconcile import reconcile, write_outputs

# Saved on user's PC for demo / submission
DEMO_ROOT = ROOT / "demo_samples"
SETTLEMENTS_DIR = DEMO_ROOT / "settlements"
BANK_DIR = DEMO_ROOT / "bank"
OUTPUT_DIR = DEMO_ROOT / "reconciliation_outputs"
REPORT_DIR = DEMO_ROOT / "test_reports"

FORMATS = ["csv", "xlsx", "pdf", "docx", "txt"]

KEY_COMBOS = [
    ("docx", "docx", "Word + Word"),
    ("pdf", "pdf", "PDF + PDF"),
    ("csv", "docx", "CSV + Word"),
    ("docx", "pdf", "Word + PDF"),
    ("pdf", "docx", "PDF + Word"),
    ("txt", "txt", "TXT + TXT"),
]


def copy_all_samples() -> dict:
    src = ROOT / "data" / "samples"
    SETTLEMENTS_DIR.mkdir(parents=True, exist_ok=True)
    BANK_DIR.mkdir(parents=True, exist_ok=True)

    copied = {"settlements": [], "bank": []}
    for fmt in FORMATS:
        for kind, folder, key in [
            ("settlements", SETTLEMENTS_DIR, "settlements"),
            ("bank", BANK_DIR, "bank"),
        ]:
            f = src / f"{kind}.{fmt}"
            if f.exists():
                dest = folder / f"{kind}.{fmt}"
                shutil.copy2(f, dest)
                copied[key].append(str(dest.relative_to(ROOT)))
    return copied


def test_combo(s_fmt: str, b_fmt: str, label: str) -> dict:
    s_path = SETTLEMENTS_DIR / f"settlements.{s_fmt}"
    b_path = BANK_DIR / f"bank.{b_fmt}"
    out_dir = OUTPUT_DIR / label.replace(" + ", "_").replace(" ", "_").lower()

    s_ex = extract_bytes(s_path.read_bytes(), s_path.name, "settlements")
    b_ex = extract_bytes(b_path.read_bytes(), b_path.name, "bank")

    s_cols = list(s_ex.dataframe.columns)
    b_cols = list(b_ex.dataframe.columns)
    s_req = required_columns("settlements")
    b_req = required_columns("bank")

    out_dir.mkdir(parents=True, exist_ok=True)
    s_csv = save_extracted(s_ex, out_dir / "extracted_settlements.csv")
    b_csv = save_extracted(b_ex, out_dir / "extracted_bank.csv")

    result = reconcile(s_csv, b_csv, confidence_threshold=0.85)
    paths = write_outputs(result, out_dir)

    # Save export reports for this combo
    meta = {
        "settlements_source": f"settlements.{s_fmt}",
        "bank_source": f"bank.{b_fmt}",
        "label": label,
    }
    pdf_path = out_dir / "SettleMatch_report.pdf"
    docx_path = out_dir / "SettleMatch_report.docx"
    pdf_path.write_bytes(build_pdf_report(result.stats, result.matches, result.exceptions, meta))
    docx_path.write_bytes(build_word_report(result.stats, result.matches, result.exceptions, meta))

    return {
        "combination": label,
        "settlements_format": s_fmt,
        "bank_format": b_fmt,
        "settlement_rows": s_ex.rows_found,
        "bank_rows": b_ex.rows_found,
        "settlement_columns": s_cols,
        "bank_columns": b_cols,
        "columns_strict": s_cols == s_req and b_cols == b_req,
        "settlement_col_count": len(s_cols),
        "bank_col_count": len(b_cols),
        "match_rate": result.stats["match_rate"],
        "match_rate_pct": f"{result.stats['match_rate'] * 100:.0f}%",
        "matched": result.stats["matched"],
        "exceptions": result.stats["exceptions"],
        "rule_matches": result.stats["rule_matches"],
        "ai_matches": result.stats["ai_matches"],
        "output_folder": str(out_dir.relative_to(ROOT)),
        "files_saved": [
            str(p.relative_to(ROOT)) for p in [
                s_path, b_path, s_csv, b_csv, pdf_path, docx_path, *paths.values()
            ]
        ],
    }


def main() -> None:
    print("Step 1: Regenerating raw data + sample documents...")
    import subprocess

    subprocess.run([sys.executable, str(ROOT / "scripts/generate_data.py")], check=True, cwd=ROOT)
    subprocess.run([sys.executable, str(ROOT / "scripts/generate_sample_docs.py")], check=True, cwd=ROOT)

    print("Step 2: Copying all sample files to demo_samples/ on your PC...")
    copied = copy_all_samples()

    print("Step 3: Running 6 key combination tests...")
    results = []
    for s_fmt, b_fmt, label in KEY_COMBOS:
        print(f"  Testing {label}...")
        results.append(test_combo(s_fmt, b_fmt, label))

    print("Step 4: Running full 25-combination audit...")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, str(ROOT / "eval/audit_extract.py")], check=True, cwd=ROOT)
    shutil.copy2(ROOT / "output/audit/extract_audit.json", REPORT_DIR / "full_25_audit.json")
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "demo_folder": str(DEMO_ROOT.relative_to(ROOT)),
        "files_on_pc": copied,
        "key_combinations": results,
        "all_pass": all(r["columns_strict"] and r["match_rate"] >= 0.85 for r in results),
    }

    json_path = REPORT_DIR / "combination_test_summary.json"
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    txt_lines = [
        "SettleMatch — Combination Test Report",
        "=" * 40,
        f"Generated: {summary['generated_at']}",
        f"Demo folder: {DEMO_ROOT}",
        "",
        "SAMPLE FILES ON YOUR PC:",
        "  settlements/ -> csv, xlsx, pdf, docx, txt",
        "  bank/        -> csv, xlsx, pdf, docx, txt",
        "",
        "KEY COMBINATION RESULTS:",
        "-" * 40,
    ]
    for r in results:
        txt_lines.append(
            f"{r['combination']:16} | rows {r['settlement_rows']}+{r['bank_rows']} "
            f"| cols {r['settlement_col_count']}+{r['bank_col_count']} strict={r['columns_strict']} "
            f"| match {r['match_rate_pct']}"
        )
    txt_lines.append("")
    txt_lines.append(f"All 6 key combos passed: {summary['all_pass']}")
    txt_lines.append(f"Full audit: demo_samples/test_reports/full_25_audit.json")

    txt_path = REPORT_DIR / "combination_test_summary.txt"
    txt_path.write_text("\n".join(txt_lines), encoding="utf-8")

    print("\n" + "=" * 50)
    print("DONE — everything saved on your PC:")
    print(f"  {DEMO_ROOT}")
    print(f"    settlements/  (5 files)")
    print(f"    bank/         (5 files)")
    print(f"    reconciliation_outputs/  (6 combo folders)")
    print(f"    test_reports/ (summary + full audit)")
    print("=" * 50)
    for r in results:
        status = "OK" if r["columns_strict"] and r["match_rate"] >= 0.85 else "FAIL"
        print(
            f"[{status}] {r['combination']:16} rows={r['settlement_rows']}+{r['bank_rows']} "
            f"match={r['match_rate_pct']} cols_strict={r['columns_strict']}"
        )


if __name__ == "__main__":
    main()
