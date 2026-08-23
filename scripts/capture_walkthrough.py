"""Capture SettleMatch UI screenshots after a full reconcile run."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "screenshots"
SETTLEMENTS = ROOT / "data" / "samples" / "settlements.csv"
BANK = ROOT / "data" / "samples" / "bank.csv"
BASE_URL = "http://localhost:8501"


def _click_sidebar(page, label: str) -> None:
    sidebar = page.locator('section[data-testid="stSidebar"]')
    sidebar.get_by_text(label, exact=True).click()
    page.wait_for_timeout(1500)


def _wait_reconcile_done(page, timeout_ms: int = 120000) -> None:
    page.get_by_text("Outcome metrics and charts for reviewers", exact=False).wait_for(
        timeout=timeout_ms
    )
    page.locator('section[data-testid="stSidebar"]').get_by_text(
        "Reconciliation ready", exact=False
    ).wait_for(timeout=10000)
    page.wait_for_timeout(1500)


def capture() -> list[Path]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit(
            "Install playwright: pip install playwright && playwright install chromium"
        ) from exc

    if not SETTLEMENTS.exists() or not BANK.exists():
        raise SystemExit("Sample files missing. Run: python scripts/generate_sample_docs.py")

    OUT.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto(BASE_URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2500)

        path = OUT / "01_upload_empty.png"
        page.screenshot(path=str(path), full_page=False)
        saved.append(path)
        print(f"Saved {path.name}")

        _click_sidebar(page, "Connections")
        path = OUT / "02_connections.png"
        page.screenshot(path=str(path), full_page=False)
        saved.append(path)
        print(f"Saved {path.name}")

        _click_sidebar(page, "Upload")
        page.locator('input[type="file"]').nth(0).set_input_files(str(SETTLEMENTS))
        page.locator('input[type="file"]').nth(1).set_input_files(str(BANK))
        page.wait_for_function(
            """() => {
                const t = document.body.innerText || '';
                return t.includes('100 rows') && t.includes('125 rows');
            }""",
            timeout=30000,
        )
        path = OUT / "04_upload_ready.png"
        page.screenshot(path=str(path), full_page=False)
        saved.append(path)
        print(f"Saved {path.name}")

        reconcile_btn = page.get_by_role("button", name="Reconcile")
        if reconcile_btn.is_disabled():
            raise RuntimeError("Reconcile button stayed disabled after upload.")
        reconcile_btn.click()
        print("Reconcile clicked — waiting for pipeline…")
        _wait_reconcile_done(page)

        path = OUT / "05_dashboard.png"
        page.screenshot(path=str(path), full_page=False)
        saved.append(path)
        print(f"Saved {path.name}")

        for idx, label in enumerate(
            ["Matches", "Exceptions", "Simulator", "Export"], start=6
        ):
            _click_sidebar(page, label)
            page.locator('section[data-testid="stSidebar"]').get_by_text(
                "Reconciliation ready", exact=False
            ).wait_for(timeout=10000)
            page.wait_for_timeout(800)
            path = OUT / f"{idx:02d}_{label.lower()}.png"
            page.screenshot(path=str(path), full_page=False)
            saved.append(path)
            print(f"Saved {path.name}")

        browser.close()

    return saved


if __name__ == "__main__":
    try:
        paths = capture()
        print(f"\nCaptured {len(paths)} screenshots in {OUT}")
    except Exception as exc:
        print(f"Capture failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
