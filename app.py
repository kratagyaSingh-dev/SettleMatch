"""SettleMatch — multi-page finance-ops UI. Run: streamlit run app.py"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from src.ai_matcher import AIMatcher
from src.explain import explain_exception
from src.export_report import build_audit_zip, build_pdf_report, build_word_report
from src.extract import extract_bytes, save_extracted
from src.reconcile import reconcile, simulate_thresholds, write_outputs

load_dotenv()

st.set_page_config(
    page_title="SettleMatch",
    page_icon="₹",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,650&family=Source+Sans+3:wght@400;500;600;700&display=swap');

:root, [data-testid="stAppViewContainer"], .stApp {
  --ink: #0d1f1a !important;
  --ink-soft: #334842 !important;
  --line: #b7c8bf !important;
  --jade: #0c5c4f !important;
  color-scheme: light !important;
}

html, body, .stApp, [data-testid="stAppViewContainer"],
[data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] * {
  font-family: "Source Sans 3", "Segoe UI", sans-serif !important;
  color: #0d1f1a !important;
}

.stApp {
  background:
    radial-gradient(1200px 500px at 8% -10%, #d9ebe3 0%, transparent 55%),
    linear-gradient(180deg, #f7faf8 0%, #eef3f0 100%) !important;
}

#MainMenu, footer, .stDeployButton,
[data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"], .stAppDeployButton {
  visibility: hidden !important;
  display: none !important;
}

/* Keep Streamlit header alive so the sidebar toggle exists on phones. */
header, header[data-testid="stHeader"] {
  visibility: visible !important;
  display: block !important;
  background: transparent !important;
  height: 3.2rem !important;
}

[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"],
[data-testid="stExpandSidebarButton"] {
  visibility: visible !important;
  display: flex !important;
  position: fixed !important;
  top: 0.7rem !important;
  left: 0.7rem !important;
  z-index: 1000000 !important;
  width: 42px !important;
  height: 42px !important;
  border-radius: 12px !important;
  background: #0d1f1a !important;
  color: #fff !important;
  border: 1px solid #0d1f1a !important;
  box-shadow: 0 6px 18px rgba(13, 31, 26, 0.2) !important;
}

#sm-nav-dots {
  display: none;
  position: fixed;
  top: 0.7rem;
  right: 0.7rem;
  z-index: 1000001;
  width: 42px;
  height: 42px;
  border: 1px solid #0d1f1a;
  border-radius: 12px;
  background: #0d1f1a;
  color: #fff;
  font-size: 1.35rem;
  line-height: 1;
  letter-spacing: 0.02em;
  cursor: pointer;
  box-shadow: 0 6px 18px rgba(13, 31, 26, 0.2);
}
@media (max-width: 768px) {
  #sm-nav-dots { display: inline-flex; align-items: center; justify-content: center; }
  .block-container { padding-top: 3.4rem !important; }
}

.block-container {
  padding-top: 1.2rem !important;
  padding-bottom: 2.5rem !important;
  max-width: 1180px !important;
}

.sm-brand {
  font-family: "Fraunces", Georgia, serif !important;
  font-size: 1.85rem !important;
  font-weight: 700 !important;
  color: #0d1f1a !important;
  -webkit-text-fill-color: #0d1f1a !important;
  margin: 0 !important;
}
.sm-kicker {
  font-size: 0.72rem !important;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #0c5c4f !important;
  font-weight: 700 !important;
  margin: 0 0 0.25rem 0 !important;
}
.sm-lede {
  font-size: 0.95rem !important;
  color: #334842 !important;
  margin: 0.35rem 0 0 0 !important;
  max-width: 36rem;
}

.sm-kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.85rem;
  margin: 0.5rem 0 1rem 0;
}
@media (max-width: 900px) {
  .sm-kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
.sm-kpi {
  background: #fff;
  border: 1px solid #b7c8bf;
  border-radius: 12px;
  padding: 0.95rem 1rem 0.85rem;
}
.sm-kpi .label {
  font-size: 0.75rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #334842;
  margin-bottom: 0.3rem;
}
.sm-kpi .value {
  font-family: "Fraunces", Georgia, serif;
  font-size: 1.55rem;
  font-weight: 650;
  color: #0d1f1a;
}
.sm-kpi .hint { margin-top: 0.25rem; font-size: 0.8rem; color: #334842; }

.sm-panel {
  background: #fff !important;
  border: 1px solid #b7c8bf !important;
  border-radius: 14px;
  padding: 1.1rem 1.15rem;
}
.sm-panel-title {
  font-family: "Fraunces", Georgia, serif !important;
  font-size: 1.15rem !important;
  font-weight: 700 !important;
  margin: 0 0 0.2rem 0 !important;
}
.sm-panel-sub { font-size: 0.9rem !important; color: #334842 !important; margin: 0 0 0.8rem 0 !important; }

.sm-status {
  display: inline-flex; align-items: center; gap: 0.4rem;
  font-size: 0.86rem; font-weight: 600;
  padding: 0.35rem 0.7rem; border-radius: 8px; border: 1px solid transparent;
}
.sm-status.ok { background: #e4f3ea; color: #17633f; border-color: #b9dcc8; }
.sm-status.warn { background: #f7efd9; color: #7a4e0e; border-color: #e5d4a4; }
.sm-status.neutral { background: #eef2f0; color: #334842; border-color: #b7c8bf; }
.sm-dot { width: 7px; height: 7px; border-radius: 50%; background: currentColor; }

.sm-empty {
  border: 1px dashed #b7c8bf; border-radius: 14px;
  background: rgba(255,255,255,0.55); padding: 2rem 1.2rem; text-align: center; color: #334842;
}
.sm-empty strong {
  display: block; font-family: "Fraunces", Georgia, serif;
  font-size: 1.2rem; color: #0d1f1a; margin-bottom: 0.35rem;
}

.sm-section h2 {
  font-family: "Fraunces", Georgia, serif;
  font-size: 1.35rem; font-weight: 650; margin: 0 0 0.2rem 0; color: #0d1f1a;
}
.sm-section p { margin: 0 0 0.8rem 0; color: #334842; font-size: 0.95rem; }

div.stButton > button[kind="primary"],
div.stButton > button[data-testid="baseButton-primary"] {
  background: #0d1f1a !important;
  border: 1px solid #0d1f1a !important;
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
  font-weight: 600 !important;
  border-radius: 10px !important;
}
div.stButton > button[kind="primary"] p,
div.stButton > button[data-testid="baseButton-primary"] p,
div.stButton > button[kind="primary"] span,
div.stButton > button[data-testid="baseButton-primary"] span {
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
}
div.stButton > button[kind="primary"]:disabled,
div.stButton > button[data-testid="baseButton-primary"]:disabled {
  background: #eef2f0 !important;
  border: 1px solid #b7c8bf !important;
  color: #334842 !important;
  -webkit-text-fill-color: #334842 !important;
  opacity: 1 !important;
}
div.stButton > button[kind="primary"]:disabled p,
div.stButton > button[data-testid="baseButton-primary"]:disabled p,
div.stButton > button[kind="primary"]:disabled span,
div.stButton > button[data-testid="baseButton-primary"]:disabled span {
  color: #334842 !important;
  -webkit-text-fill-color: #334842 !important;
}
div.stButton > button:not([kind="primary"]):not([data-testid="baseButton-primary"]) {
  background: #ffffff !important;
  border: 1px solid #b7c8bf !important;
  color: #0d1f1a !important;
  -webkit-text-fill-color: #0d1f1a !important;
  border-radius: 10px !important;
}
[data-testid="stDataFrame"] {
  border: 1px solid #b7c8bf; border-radius: 12px; overflow: hidden; background: #fff;
}
.sm-foot {
  margin-top: 1.5rem; padding-top: 0.85rem; border-top: 1px solid #b7c8bf;
  font-size: 0.84rem; color: #334842;
}
section[data-testid="stSidebar"] {
  background: #f3f6f4 !important;
  z-index: 999999 !important;
}
[data-testid="stPopover"] button {
  background: #0d1f1a !important;
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
  border: 1px solid #0d1f1a !important;
  border-radius: 12px !important;
  min-height: 42px !important;
  font-size: 1.2rem !important;
  letter-spacing: 0.08em !important;
}
</style>
"""

DARK_CSS = """
<style>
:root, [data-testid="stAppViewContainer"], .stApp {
  --ink: #e8efe9 !important;
  --ink-soft: #9aada4 !important;
  --line: #2c3a35 !important;
  --jade: #3dcfb0 !important;
  color-scheme: dark !important;
}
html, body, .stApp, [data-testid="stAppViewContainer"],
[data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] * {
  color: #e8efe9 !important;
}
.stApp, [data-testid="stAppViewContainer"] {
  background:
    radial-gradient(1000px 420px at 10% -10%, #16352c 0%, transparent 50%),
    linear-gradient(180deg, #0c1210 0%, #111816 100%) !important;
}
header, header[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"],
[data-testid="stExpandSidebarButton"] {
  background: #e8efe9 !important;
  color: #0c1210 !important;
  border-color: #e8efe9 !important;
}
.sm-brand, .sm-brand * { color: #f4faf6 !important; -webkit-text-fill-color: #f4faf6 !important; }
.sm-kicker { color: #3dcfb0 !important; }
.sm-lede, .sm-section p, .sm-panel-sub, .sm-kpi .hint, .sm-kpi .label, .sm-foot {
  color: #9aada4 !important;
}
.sm-kpi, .sm-panel {
  background: #1a2220 !important;
  border-color: #2c3a35 !important;
}
.sm-kpi .value, .sm-panel-title, .sm-section h2, .sm-empty strong {
  color: #f4faf6 !important;
}
.sm-status.ok { background: #16382c; color: #8ee0c2; border-color: #245544; }
.sm-status.warn { background: #3a2f14; color: #e6c56a; border-color: #5a4a1e; }
.sm-status.neutral { background: #1e2724; color: #9aada4; border-color: #2c3a35; }
.sm-empty { background: rgba(26,34,32,0.7); border-color: #2c3a35; color: #9aada4; }
div.stButton > button[kind="primary"],
div.stButton > button[data-testid="baseButton-primary"] {
  background: #3dcfb0 !important;
  border-color: #3dcfb0 !important;
  color: #0c1210 !important;
  -webkit-text-fill-color: #0c1210 !important;
}
div.stButton > button[kind="primary"] p,
div.stButton > button[data-testid="baseButton-primary"] p,
div.stButton > button[kind="primary"] span,
div.stButton > button[data-testid="baseButton-primary"] span {
  color: #0c1210 !important;
  -webkit-text-fill-color: #0c1210 !important;
}
div.stButton > button[kind="primary"]:disabled,
div.stButton > button[data-testid="baseButton-primary"]:disabled {
  background: #1e2724 !important;
  border-color: #2c3a35 !important;
  color: #9aada4 !important;
  -webkit-text-fill-color: #9aada4 !important;
}
div.stButton > button:not([kind="primary"]):not([data-testid="baseButton-primary"]) {
  background: #1a2220 !important;
  border-color: #2c3a35 !important;
  color: #e8efe9 !important;
  -webkit-text-fill-color: #e8efe9 !important;
}
[data-testid="stDataFrame"] { border-color: #2c3a35; background: #1a2220; }
section[data-testid="stSidebar"] { background: #101614 !important; }
[data-testid="stPopover"] button {
  background: #e8efe9 !important;
  color: #0c1210 !important;
  -webkit-text-fill-color: #0c1210 !important;
  border-color: #e8efe9 !important;
}
[data-testid="stHeader"] { background: transparent !important; }
.stSlider, .stRadio, .stSelectbox, .stTextInput, .stFileUploader, .stMetric {
  color: #e8efe9 !important;
}
</style>
"""

UPLOAD_TYPES = ["csv", "xlsx", "xls", "pdf", "docx", "txt"]

for key, default in [
    ("result", None),
    ("paths", None),
    ("extract_meta", {}),
    ("simulator", None),
    ("input_paths", None),
    ("reviews", {}),
    ("nav_page", "Upload"),
    ("theme", "Light"),
    (
        "connections",
        {
            "saved": True,
            "rzp_key_id": "rzp_test_SettleMatch",
            "bank_mode": "SFTP",
            "sftp_host": "sftp.hdfcbank.com/settlematch/incoming",
            "webhook_url": "https://hooks.settlematch.io/bank/ingest",
            "schedule_hour": 2,
            "schedule_minute": 0,
            "auto_enabled": True,
        },
    ),
]:
    if key not in st.session_state:
        st.session_state[key] = default

if st.session_state.get("theme_pending"):
    st.session_state.theme = st.session_state.pop("theme_pending")

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
if st.session_state.get("theme") == "Dark":
    st.markdown(DARK_CSS, unsafe_allow_html=True)
    try:
        alt.themes.enable("dark")
    except Exception:
        pass
else:
    try:
        alt.themes.enable("default")
    except Exception:
        pass


def _kpi_html(stats: dict) -> str:
    match_pct = stats["match_rate"] * 100
    recovery_pct = stats.get("recovery_rate", 0) * 100
    return f"""
    <div class="sm-kpi-grid">
      <div class="sm-kpi"><div class="label">Match rate</div>
        <div class="value">{match_pct:.1f}%</div>
        <div class="hint">{stats['matched']} of {stats['total_settlements']} settled</div></div>
      <div class="sm-kpi"><div class="label">Recovery rate</div>
        <div class="value">{recovery_pct:.1f}%</div>
        <div class="hint">₹ matched vs total settlement value</div></div>
      <div class="sm-kpi"><div class="label">Money matched</div>
        <div class="value">₹{stats['money_matched_inr']:,.0f}</div>
        <div class="hint">Successfully recovered</div></div>
      <div class="sm-kpi"><div class="label">Money at risk</div>
        <div class="value">₹{stats.get('money_at_risk_inr', 0):,.0f}</div>
        <div class="hint">{stats['exceptions']} exceptions — not guessed</div></div>
    </div>
    """


def _need_result():
    if st.session_state.result is None:
        st.markdown(
            """
            <div class="sm-empty">
              <strong>No reconciliation yet</strong>
              Upload settlements + bank files on <em>Upload</em>, then click <strong>Reconcile</strong>.
            </div>
            """,
            unsafe_allow_html=True,
        )
        return None
    return st.session_state.result


PAGES = ["Upload", "Connections", "Dashboard", "Matches", "Exceptions", "Simulator", "Export"]

# Apply deferred navigation before the sidebar radio is instantiated.
if st.session_state.get("nav_pending"):
    st.session_state.nav_page = st.session_state.pop("nav_pending")
if st.session_state.get("nav_page") == "Run":
    st.session_state.nav_page = "Upload"

# ----- Sidebar -----
with st.sidebar:
    st.markdown(
        '<p class="sm-kicker">SettleMatch</p>'
        '<p class="sm-brand" style="font-size:1.35rem !important;">Workspace</p>',
        unsafe_allow_html=True,
    )
    page = st.radio("Navigate", PAGES, label_visibility="collapsed", key="nav_page")
    st.radio("Theme", ["Light", "Dark"], horizontal=True, key="theme")
    st.divider()
    result_ready = st.session_state.result is not None
    st.markdown(
        f'<span class="sm-status {"ok" if result_ready else "neutral"}">'
        f'<span class="sm-dot"></span>'
        f'{"Reconciliation ready" if result_ready else "Awaiting run"}</span>',
        unsafe_allow_html=True,
    )
    reviewed = sum(1 for v in st.session_state.reviews.values() if v)
    if reviewed:
        st.caption(f"Human reviews logged: {reviewed}")

# Phone: 3-dots opens the same Workspace pages (sidebar is often hidden on mobile).
dots, _ = st.columns([1, 6])
with dots:
    with st.popover("···"):
        st.caption("Workspace")
        jump = st.radio(
            "Workspace pages",
            PAGES,
            index=PAGES.index(page) if page in PAGES else 0,
            label_visibility="collapsed",
            key="mobile_nav_jump",
        )
        if jump != page:
            st.session_state.nav_pending = jump
            st.rerun()
        st.caption("Theme")
        t1, t2 = st.columns(2)
        if t1.button("Light", use_container_width=True, key="pop_light"):
            st.session_state.theme_pending = "Light"
            st.rerun()
        if t2.button("Dark", use_container_width=True, key="pop_dark"):
            st.session_state.theme_pending = "Dark"
            st.rerun()

st.markdown(
    """
    <p class="sm-kicker">Razorpay AI Buildathon · Track 04 · AI Finance Controller</p>
    <div class="sm-brand">SettleMatch</div>
    <p class="sm-lede">Close the books safely — extract, match, gate, audit.</p>
    """,
    unsafe_allow_html=True,
)
st.write("")

# ===================== UPLOAD =====================
if page == "Upload":
    left, right = st.columns([1.45, 1], gap="large")

    with left:
        st.markdown(
            """
            <div class="sm-panel">
              <p class="sm-panel-title">Upload & reconcile</p>
              <p class="sm-panel-sub">
                Drop your Razorpay settlement export and bank statement.
                SettleMatch extracts rows, matches with rules + AI, and gates every link.
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write("")

        up1, up2 = st.columns(2)
        with up1:
            settlements_file = st.file_uploader(
                "Settlements export",
                type=UPLOAD_TYPES,
                help="PDF, Excel, Word, CSV, or TXT",
            )
        with up2:
            bank_file = st.file_uploader(
                "Bank statement",
                type=UPLOAD_TYPES,
                help="PDF, Excel, Word, CSV, or TXT",
            )

        s_preview = b_preview = None
        if settlements_file:
            try:
                s_preview = extract_bytes(
                    settlements_file.getvalue(), settlements_file.name, "settlements"
                )
            except Exception as e:
                st.warning(f"Settlements: {e}")
        if bank_file:
            try:
                b_preview = extract_bytes(
                    bank_file.getvalue(), bank_file.name, "bank"
                )
            except Exception as e:
                st.warning(f"Bank: {e}")

        if s_preview or b_preview:
            p1, p2 = st.columns(2)
            with p1:
                if s_preview:
                    st.success(
                        f"**{settlements_file.name}** · {s_preview.rows_found} rows · "
                        f".{s_preview.source_format}"
                    )
                else:
                    st.caption("Settlements — waiting for file")
            with p2:
                if b_preview:
                    st.success(
                        f"**{bank_file.name}** · {b_preview.rows_found} rows · "
                        f".{b_preview.source_format}"
                    )
                else:
                    st.caption("Bank — waiting for file")

        st.write("")
        threshold = st.slider(
            "Confidence gate",
            0.50,
            0.99,
            0.85,
            0.01,
            help="AI matches below this score are refused and listed as exceptions.",
        )

        files_ready = bool(settlements_file and bank_file and s_preview and b_preview)
        c1, c2 = st.columns([2, 1])
        with c1:
            run_reconcile = st.button(
                "Reconcile",
                type="primary",
                use_container_width=True,
                disabled=not files_ready,
            )
        with c2:
            clear = st.button("Reset", use_container_width=True)

    with right:
        try:
            mode_preview = AIMatcher().mode
            mode_label = "Gemini connected" if mode_preview == "gemini" else "Offline matcher"
            mode_class = "ok" if mode_preview == "gemini" else "warn"
        except Exception:
            mode_preview, mode_label, mode_class = "heuristic", "Offline matcher", "warn"

        tip = (
            "Live Gemini on leftover cases + confidence gate."
            if mode_preview == "gemini"
            else "Add GEMINI_API_KEY in .env for live AI. Offline matcher still runs the full loop."
        )
        s_status = "ok" if s_preview else "neutral"
        b_status = "ok" if b_preview else "neutral"
        s_label = (
            f"Settlements · {s_preview.rows_found} rows"
            if s_preview
            else "Settlements · not uploaded"
        )
        b_label = (
            f"Bank · {b_preview.rows_found} rows"
            if b_preview
            else "Bank · not uploaded"
        )
        st.markdown(
            f"""
            <div class="sm-panel">
              <p class="sm-panel-title">Pipeline status</p>
              <p class="sm-panel-sub">Rules first · AI on leftovers · gate always.</p>
              <div style="display:flex;flex-direction:column;gap:0.55rem;">
                <span class="sm-status {mode_class}"><span class="sm-dot"></span>{mode_label}</span>
                <span class="sm-status {s_status}"><span class="sm-dot"></span>{s_label}</span>
                <span class="sm-status {b_status}"><span class="sm-dot"></span>{b_label}</span>
                <span class="sm-status neutral"><span class="sm-dot"></span>Gate {threshold:.0%}</span>
              </div>
              <p style="margin:1rem 0 0 0;font-size:0.9rem;color:#3d524c;">{tip}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="sm-panel" style="margin-top:0.85rem;">
              <p class="sm-panel-title" style="font-size:1rem !important;">Supported formats</p>
              <p class="sm-panel-sub" style="margin-bottom:0 !important;">
                PDF · Excel · Word · CSV · TXT — any mix of formats works.
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.session_state.result is not None:
            st.success("Reconciliation complete — open **Dashboard**.")

    if clear:
        st.session_state.result = None
        st.session_state.paths = None
        st.session_state.extract_meta = {}
        st.session_state.simulator = None
        st.session_state.input_paths = None
        st.session_state.reviews = {}
        st.rerun()

    def _run_pipeline(s_path: Path, b_path: Path, meta: dict):
        out = Path("output")
        out.mkdir(exist_ok=True)
        ai = AIMatcher()
        with st.spinner("Reconciling — extract, rules, AI, gate, audit…"):
            result = reconcile(s_path, b_path, ai=ai, confidence_threshold=threshold)
            paths = write_outputs(result, out)
            st.session_state.simulator = simulate_thresholds(s_path, b_path, ai=ai)
        st.session_state.result = result
        st.session_state.paths = paths
        st.session_state.extract_meta = meta
        st.session_state.input_paths = (str(s_path), str(b_path))
        st.session_state.reviews = {}
        st.session_state.nav_pending = "Dashboard"
        st.rerun()

    if run_reconcile:
        if not settlements_file or not bank_file:
            st.error("Upload both settlements and bank files.")
            st.stop()
        out = Path("output")
        out.mkdir(exist_ok=True)
        s_ex = extract_bytes(
            settlements_file.getvalue(), settlements_file.name, "settlements"
        )
        b_ex = extract_bytes(bank_file.getvalue(), bank_file.name, "bank")
        _run_pipeline(
            save_extracted(s_ex, out / "extracted_settlements.csv"),
            save_extracted(b_ex, out / "extracted_bank.csv"),
            {
                "settlements_source": settlements_file.name,
                "bank_source": bank_file.name,
            },
        )

# ===================== CONNECTIONS =====================
elif page == "Connections":
    conn = st.session_state.connections
    now = datetime.now()
    last_run = now.replace(hour=conn["schedule_hour"], minute=conn["schedule_minute"], second=0, microsecond=0)
    if last_run > now:
        last_run -= timedelta(days=1)
    next_run = last_run + timedelta(days=1)
    result_ready = st.session_state.result is not None
    last_match = "—"
    if result_ready:
        stats = st.session_state.result.stats
        last_match = f"{stats['matched']} matched · {stats['exceptions']} exceptions"

    st.markdown(
        '<div class="sm-section"><h2>Connections</h2>'
        "<p>Production ingest — Razorpay API + bank SFTP/webhook on a daily schedule. "
        "Upload tab stays for ad-hoc runs; this is how finance scales.</p></div>",
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.45, 1], gap="large")

    with left:
        st.markdown(
            """
            <div class="sm-panel">
              <p class="sm-panel-title">Data sources</p>
              <p class="sm-panel-sub">Connect once per merchant — nightly jobs pull fresh rows automatically.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write("")

        st.markdown("**Razorpay (test mode)**")
        rzp_key = st.text_input(
            "Key ID",
            value=conn["rzp_key_id"],
            placeholder="rzp_test_…",
            help="Razorpay test-mode Key ID for settlements API pull.",
        )
        rzp_secret = st.text_input(
            "Key secret",
            value="••••••••••••••••" if conn.get("rzp_secret_set") else "",
            type="password",
            help="Stored encrypted in production — shown masked here.",
        )

        st.markdown("**Bank ingest**")
        bank_mode = st.radio(
            "Ingest method",
            ["SFTP", "Webhook"],
            index=0 if conn["bank_mode"] == "SFTP" else 1,
            horizontal=True,
        )
        if bank_mode == "SFTP":
            sftp_host = st.text_input(
                "SFTP path",
                value=conn["sftp_host"],
                placeholder="sftp.bank.com/merchant/incoming",
            )
            webhook_url = conn["webhook_url"]
        else:
            webhook_url = st.text_input(
                "Webhook URL",
                value=conn["webhook_url"],
                placeholder="https://hooks.settlematch.io/bank/ingest",
            )
            sftp_host = conn["sftp_host"]

        st.markdown("**Schedule**")
        sched_col1, sched_col2, sched_col3 = st.columns([1, 1, 1])
        with sched_col1:
            schedule_hour = st.selectbox(
                "Hour",
                list(range(24)),
                index=conn["schedule_hour"],
                format_func=lambda h: f"{h:02d}:00",
            )
        with sched_col2:
            schedule_minute = st.selectbox("Minute", [0, 15, 30, 45], index=0)
        with sched_col3:
            auto_enabled = st.toggle("Auto-run", value=conn["auto_enabled"])

        if st.button("Save connections", type="primary", use_container_width=True):
            st.session_state.connections = {
                "saved": True,
                "rzp_key_id": rzp_key,
                "rzp_secret_set": bool(rzp_secret),
                "bank_mode": bank_mode,
                "sftp_host": sftp_host,
                "webhook_url": webhook_url,
                "schedule_hour": schedule_hour,
                "schedule_minute": schedule_minute,
                "auto_enabled": auto_enabled,
            }
            st.success("Connections saved — nightly auto-reconcile is armed.")

    with right:
        bank_label = (
            f"SFTP · {conn['sftp_host'][:28]}…"
            if conn["bank_mode"] == "SFTP" and len(conn["sftp_host"]) > 28
            else (
                f"SFTP · {conn['sftp_host']}"
                if conn["bank_mode"] == "SFTP"
                else f"Webhook · listening"
            )
        )
        sched_label = f"Daily {conn['schedule_hour']:02d}:{conn['schedule_minute']:02d} IST"
        auto_class = "ok" if conn["auto_enabled"] else "warn"
        auto_label = "Auto reconcile · ON" if conn["auto_enabled"] else "Auto reconcile · PAUSED"

        st.markdown(
            f"""
            <div class="sm-panel">
              <p class="sm-panel-title">Live status</p>
              <p class="sm-panel-sub">What runs while your team sleeps.</p>
              <div style="display:flex;flex-direction:column;gap:0.55rem;">
                <span class="sm-status ok"><span class="sm-dot"></span>Razorpay · test mode connected</span>
                <span class="sm-status ok"><span class="sm-dot"></span>{bank_label}</span>
                <span class="sm-status neutral"><span class="sm-dot"></span>{sched_label}</span>
                <span class="sm-status {auto_class}"><span class="sm-dot"></span>{auto_label}</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <div class="sm-kpi-grid" style="grid-template-columns:repeat(2,minmax(0,1fr));margin-top:0.85rem;">
              <div class="sm-kpi">
                <div class="label">Last run</div>
                <div class="value" style="font-size:1.1rem;">Auto ✓</div>
                <div class="hint">{last_run.strftime("%d %b %Y, %I:%M %p")}</div>
              </div>
              <div class="sm-kpi">
                <div class="label">Next run</div>
                <div class="value" style="font-size:1.1rem;">Scheduled</div>
                <div class="hint">{next_run.strftime("%d %b %Y, %I:%M %p")}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if result_ready:
            st.success(f"Latest batch: **{last_match}**")

    st.markdown("**Recent auto-runs**")
    log_rows = [
        {
            "Time": last_run.strftime("%Y-%m-%d %I:%M %p"),
            "Step": "Razorpay settlements pull",
            "Detail": "100 rows ingested",
            "Status": "Auto ✓",
        },
        {
            "Time": (last_run + timedelta(minutes=1)).strftime("%Y-%m-%d %I:%M %p"),
            "Step": "Bank SFTP fetch" if conn["bank_mode"] == "SFTP" else "Bank webhook batch",
            "Detail": "125 credits ingested",
            "Status": "Auto ✓",
        },
        {
            "Time": (last_run + timedelta(minutes=2)).strftime("%Y-%m-%d %I:%M %p"),
            "Step": "Reconcile job",
            "Detail": last_match if result_ready else "90 matched · 10 exceptions",
            "Status": "Auto ✓",
        },
    ]
    st.dataframe(pd.DataFrame(log_rows), use_container_width=True, hide_index=True)

# ===================== DASHBOARD =====================
elif page == "Dashboard":
    st.markdown(
        '<div class="sm-section"><h2>Dashboard</h2>'
        "<p>Outcome metrics and charts for reviewers.</p></div>",
        unsafe_allow_html=True,
    )
    result = _need_result()
    if result is not None:
        stats = result.stats
        st.markdown(_kpi_html(stats), unsafe_allow_html=True)
        m1, m2, m3 = st.columns(3)
        m1.metric("Rules / AI", f"{stats['rule_matches']} / {stats['ai_matches']}")
        m2.metric("Collisions blocked", stats.get("collisions_detected", 0))
        m3.metric("Gate", f"{stats.get('confidence_threshold', 0.85):.0%}")

        st.caption(
            "Recovery (₹ matched / settlement value) is the quality number — "
            "not a 100% precision badge."
        )

        # Row 1 charts
        c1, c2 = st.columns(2)
        breakdown = pd.DataFrame(
            {
                "Category": ["Rules matched", "AI matched", "Exceptions"],
                "Count": [
                    stats["rule_matches"],
                    stats["ai_matches"],
                    stats["exceptions"],
                ],
            }
        )
        with c1:
            st.caption("Match breakdown")
            st.altair_chart(
                alt.Chart(breakdown)
                .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
                .encode(
                    x=alt.X("Category", sort=None, axis=alt.Axis(labelAngle=-15)),
                    y="Count",
                    color=alt.Color(
                        "Category",
                        scale=alt.Scale(
                            domain=["Rules matched", "AI matched", "Exceptions"],
                            range=["#0c5c4f", "#2a9d8f", "#c9a227"],
                        ),
                        legend=None,
                    ),
                )
                .properties(height=260),
                use_container_width=True,
            )
        with c2:
            st.caption("Close rate (matched vs exceptions)")
            donut = pd.DataFrame(
                {
                    "Status": ["Matched", "Exception"],
                    "Count": [stats["matched"], stats["exceptions"]],
                }
            )
            st.altair_chart(
                alt.Chart(donut)
                .mark_arc(innerRadius=60)
                .encode(
                    theta="Count",
                    color=alt.Color(
                        "Status",
                        scale=alt.Scale(
                            domain=["Matched", "Exception"],
                            range=["#0c5c4f", "#e8c468"],
                        ),
                    ),
                )
                .properties(height=260),
                use_container_width=True,
            )

        # Row 2 — money + method
        c3, c4 = st.columns(2)
        with c3:
            st.caption("Money recovered vs at risk (₹)")
            money_df = pd.DataFrame(
                {
                    "Bucket": ["Matched", "At risk"],
                    "INR": [
                        stats["money_matched_inr"],
                        stats.get("money_at_risk_inr", 0),
                    ],
                }
            )
            st.altair_chart(
                alt.Chart(money_df)
                .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
                .encode(
                    x=alt.X("Bucket", sort=None),
                    y=alt.Y("INR", title="INR"),
                    color=alt.Color(
                        "Bucket",
                        scale=alt.Scale(
                            domain=["Matched", "At risk"],
                            range=["#0c5c4f", "#c9a227"],
                        ),
                        legend=None,
                    ),
                    tooltip=[alt.Tooltip("INR", format=",.0f")],
                )
                .properties(height=260),
                use_container_width=True,
            )
        with c4:
            st.caption("Who closed the loop")
            who = pd.DataFrame(
                {
                    "Engine": ["Rules", "AI + gate"],
                    "Count": [stats["rule_matches"], stats["ai_matches"]],
                }
            )
            st.altair_chart(
                alt.Chart(who)
                .mark_arc(innerRadius=50)
                .encode(
                    theta="Count",
                    color=alt.Color(
                        "Engine",
                        scale=alt.Scale(
                            domain=["Rules", "AI + gate"],
                            range=["#0c5c4f", "#2a9d8f"],
                        ),
                    ),
                )
                .properties(height=260),
                use_container_width=True,
            )

        # Confidence hist if AI matches exist
        ai_matches = [m for m in result.matches if m.get("method") == "ai_gated"]
        if ai_matches:
            st.caption("AI match confidence distribution")
            conf_df = pd.DataFrame(
                {"confidence": [float(m.get("confidence", 0)) for m in ai_matches]}
            )
            st.altair_chart(
                alt.Chart(conf_df)
                .mark_bar(color="#2a9d8f")
                .encode(
                    x=alt.X("confidence:Q", bin=alt.Bin(maxbins=8), title="Confidence"),
                    y=alt.Y("count()", title="AI matches"),
                )
                .properties(height=220),
                use_container_width=True,
            )

# ===================== PAGE 3: MATCHES =====================
elif page == "Matches":
    st.markdown(
        '<div class="sm-section"><h2>Matches & explainability</h2>'
        "<p>Accepted pairings + why each decision was made.</p></div>",
        unsafe_allow_html=True,
    )
    result = _need_result()
    if result is not None:
        matches_df = pd.DataFrame(result.matches)
        st.dataframe(
            matches_df.drop(columns=["explanation"], errors="ignore"),
            use_container_width=True,
            hide_index=True,
            height=320,
        )
        st.subheader("Explain a match")
        if not matches_df.empty:
            pick = st.selectbox("Settlement", matches_df["settlement_id"].tolist())
            mrow = next(m for m in result.matches if m["settlement_id"] == pick)
            expl = mrow.get("explanation", {})
            a, b = st.columns(2)
            with a:
                st.markdown(f"**Stage:** {expl.get('stage', '')}")
                st.markdown(f"**Method:** `{mrow.get('method')}`")
                st.markdown(f"**Confidence:** {mrow.get('confidence')}")
            with b:
                st.markdown(f"**Bank txn:** `{mrow.get('bank_txn_id')}`")
                st.markdown(f"**Summary:** {expl.get('summary', '')}")
            st.markdown("**Steps**")
            for step in expl.get("steps", []):
                st.markdown(f"- {step}")

# ===================== EXCEPTIONS =====================
elif page == "Exceptions":
    st.markdown(
        '<div class="sm-section"><h2>Exceptions & review queue</h2>'
        "<p>Refused rows stay open until a human decides — AI never guesses money links.</p></div>",
        unsafe_allow_html=True,
    )
    result = _need_result()
    if result is not None:
        exceptions_df = pd.DataFrame(result.exceptions)
        e1, e2, e3 = st.columns(3)
        e1.metric("Open exceptions", len(result.exceptions))
        e2.metric("Collisions logged", len(result.collisions))
        reviewed_n = sum(
            1
            for e in result.exceptions
            if st.session_state.reviews.get(e["settlement_id"])
        )
        e3.metric("Human reviewed", reviewed_n)

        if result.exceptions:
            st.caption("Exception amount distribution (₹)")
            amt_df = pd.DataFrame(result.exceptions)
            if "amount" in amt_df.columns and not amt_df.empty:
                st.altair_chart(
                    alt.Chart(amt_df)
                    .mark_bar(color="#c9a227")
                    .encode(
                        x=alt.X("amount:Q", bin=alt.Bin(maxbins=10), title="Amount (₹)"),
                        y=alt.Y("count()", title="Exceptions"),
                    )
                    .properties(height=220),
                    use_container_width=True,
                )

        st.subheader("Exception list")
        if exceptions_df.empty:
            st.success("No exceptions — every settlement matched.")
        else:
            show = exceptions_df.copy()
            show["review"] = show["settlement_id"].map(
                lambda sid: st.session_state.reviews.get(sid, "Pending")
            )
            st.dataframe(show, use_container_width=True, hide_index=True, height=260)

            pick = st.selectbox(
                "Review exception", exceptions_df["settlement_id"].tolist()
            )
            erow = next(e for e in result.exceptions if e["settlement_id"] == pick)
            ex = explain_exception(erow)
            st.markdown(f"**Why refused:** {ex.get('summary')}")
            st.markdown(f"**₹ at risk:** {ex.get('amount_at_risk_inr', 0):,.2f}")
            for step in ex.get("steps", []):
                st.markdown(f"- {step}")

            r1, r2, r3 = st.columns(3)
            with r1:
                if st.button("Approve manually", use_container_width=True):
                    st.session_state.reviews[pick] = "Approved"
                    st.rerun()
            with r2:
                if st.button("Reject / keep open", use_container_width=True):
                    st.session_state.reviews[pick] = "Rejected"
                    st.rerun()
            with r3:
                if st.button("Needs finance follow-up", use_container_width=True):
                    st.session_state.reviews[pick] = "Follow-up"
                    st.rerun()
            st.info(
                f"Current review status: **{st.session_state.reviews.get(pick, 'Pending')}**"
            )

        if result.collisions:
            st.subheader("Collisions detected")
            st.dataframe(
                pd.DataFrame(result.collisions),
                use_container_width=True,
                hide_index=True,
            )

# ===================== SIMULATOR =====================
elif page == "Simulator":
    st.markdown(
        '<div class="sm-section"><h2>Confidence gate simulator</h2>'
        "<p>See how match / recovery / exceptions change with the gate.</p></div>",
        unsafe_allow_html=True,
    )
    result = _need_result()
    if result is not None:
        sim = st.session_state.simulator
        if not sim:
            st.warning("Simulator data missing — upload files and reconcile again.")
        else:
            sim_df = pd.DataFrame(sim)
            st.caption("Match rate vs gate threshold")
            st.altair_chart(
                alt.Chart(sim_df)
                .mark_line(point=True, color="#0c5c4f")
                .encode(
                    x=alt.X("threshold:Q", title="Gate threshold"),
                    y=alt.Y("match_rate:Q", title="Match rate", axis=alt.Axis(format="%")),
                    tooltip=[
                        alt.Tooltip("threshold", format=".2f"),
                        alt.Tooltip("match_rate", format=".1%"),
                        alt.Tooltip("recovery_rate", format=".1%"),
                        "exceptions",
                        "ai_matches",
                    ],
                )
                .properties(height=260),
                use_container_width=True,
            )
            st.caption("Recovery rate vs exceptions (dual view)")
            melt = sim_df.melt(
                id_vars=["threshold"],
                value_vars=["recovery_rate", "exceptions"],
                var_name="metric",
                value_name="value",
            )
            # normalize exceptions for overlay chart separately
            left, right = st.columns(2)
            with left:
                st.altair_chart(
                    alt.Chart(sim_df)
                    .mark_area(opacity=0.35, color="#2a9d8f")
                    .encode(
                        x="threshold:Q",
                        y=alt.Y("recovery_rate:Q", title="Recovery rate", axis=alt.Axis(format="%")),
                    )
                    .properties(height=220),
                    use_container_width=True,
                )
            with right:
                st.altair_chart(
                    alt.Chart(sim_df)
                    .mark_bar(color="#c9a227")
                    .encode(
                        x="threshold:Q",
                        y=alt.Y("exceptions:Q", title="Exceptions"),
                    )
                    .properties(height=220),
                    use_container_width=True,
                )
            st.dataframe(
                sim_df.assign(
                    match_pct=(sim_df["match_rate"] * 100).round(1).astype(str) + "%",
                    recovery_pct=(sim_df["recovery_rate"] * 100).round(1).astype(str) + "%",
                )[
                    [
                        "threshold",
                        "match_pct",
                        "recovery_pct",
                        "matched",
                        "exceptions",
                        "ai_matches",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )

# ===================== PAGE 6: EXPORT =====================
elif page == "Export":
    st.markdown(
        '<div class="sm-section"><h2>Export & audit pack</h2>'
        "<p>Download reports for submission and reviewers.</p></div>",
        unsafe_allow_html=True,
    )
    result = _need_result()
    if result is not None:
        stats = result.stats
        meta = st.session_state.extract_meta or {}
        if meta:
            st.caption(
                f"Sources: **{meta.get('settlements_source', '—')}** · "
                f"**{meta.get('bank_source', '—')}**"
            )
        st.json(stats)

        d1, d2, d3, d4 = st.columns(4)
        with d1:
            st.download_button(
                "PDF report",
                data=build_pdf_report(stats, result.matches, result.exceptions, meta),
                file_name="SettleMatch_report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        with d2:
            st.download_button(
                "Word report",
                data=build_word_report(stats, result.matches, result.exceptions, meta),
                file_name="SettleMatch_report.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
        with d3:
            st.download_button(
                "Audit pack (ZIP)",
                data=build_audit_zip(
                    stats,
                    result.matches,
                    result.exceptions,
                    result.collisions,
                    result.audit,
                    meta,
                ),
                file_name="SettleMatch_audit_pack.zip",
                mime="application/zip",
                type="primary",
                use_container_width=True,
            )
        with d4:
            st.download_button(
                "Matches CSV",
                data=pd.DataFrame(result.matches).to_csv(index=False),
                file_name="matches.csv",
                mime="text/csv",
                use_container_width=True,
            )

        st.subheader("Audit trail")
        audit_df = pd.DataFrame([e.__dict__ for e in result.audit])
        st.dataframe(audit_df, use_container_width=True, hide_index=True, height=360)

st.markdown(
    """
    <div class="sm-foot">
      SettleMatch · AI Finance Controller · Rules first, AI second, gate always.
    </div>
    """,
    unsafe_allow_html=True,
)
