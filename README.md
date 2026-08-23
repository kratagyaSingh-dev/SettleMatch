# SettleMatch

**Razorpay AI Buildathon — Track 04: AI Finance Controller**

SettleMatch is a finance-ops product that **closes the books safely**: it takes a Razorpay settlement export and a bank statement, matches every rupee it can prove, and **refuses** every rupee it cannot.

> Rules first. AI second. Gate always.  
> Ambiguous cases are listed as exceptions — never guessed.

**Repo:** [github.com/kratagyaSingh-dev/SettleMatch](https://github.com/kratagyaSingh-dev/SettleMatch)

---

## Table of contents

1. [What this is](#what-this-is)
2. [The problem](#the-problem)
3. [How the pipeline works](#how-the-pipeline-works)
4. [Every feature, explained](#every-feature-explained)
5. [Pages in the app](#pages-in-the-app)
6. [Demo results](#demo-results)
7. [Tech stack](#tech-stack)
8. [Quick start](#quick-start)
9. [Safety invariants](#safety-invariants)
10. [Repo map](#repo-map)
11. [Production path](#production-path)
12. [Pitch script](#pitch-script)

---

## What this is

Track 04 asks builders to close **one real finance loop** on a 50+ record batch, with measured accuracy and an honest exception list.

SettleMatch does that job end-to-end:

| Input | Output |
|---|---|
| Settlements file (PDF / Excel / Word / CSV / TXT) | Matches with method + confidence + explanation |
| Bank statement (any of the same formats) | Exceptions with reasons + human review queue |
| Confidence gate (default 0.85) | Dashboard KPIs, simulator, PDF / Word / audit ZIP |

It is **not** a chatbot wrapper. It is a bounded reconciliation engine with a product UI.

---

## The problem

Merchant money lands in two places:

1. **Razorpay settlements** — `settlement_id`, `payment_id`, `amount`, `utr`, `settled_at`
2. **Bank credits** — `bank_txn_id`, `amount`, `narration`, `value_date`, `utr`

Finance teams still match these in Excel. That is:

- Slow on a daily batch
- Easy to miss a missing credit
- Hard to audit six months later
- Dangerous if an LLM just “picks something”

SettleMatch’s job is **verification capacity**: match what is clear, escalate what is not.

---

## How the pipeline works

```
PDF / Excel / Word / CSV / TXT
              │
              ▼
     Extract (strict schema only)
              │
              ▼
     Rules — exact UTR, then amount + ±1 day
              │ unmatched
              ▼
     Collision detector
              │
              ▼
     Gemini on leftovers (top candidates only)
              │
              ▼
     Confidence gate (≥ 0.85, no double-spend)
         ├── accept → Matches + explanation
         └── refuse → Exceptions + human review
              │
              ▼
     Dashboard · Simulator · PDF / Word / Audit ZIP
```

| Stage | What it does | Failure mode |
|---|---|---|
| **Extract** | Maps only required columns; drops extras | Bad / empty file → hard error |
| **Rules** | Exact UTR; unique amount within ±1 day | Multi-candidate → collision |
| **Collisions** | Blocks ambiguous UTR / amount windows | Row goes to leftovers or exception |
| **AI** | Gemini JSON pick from a short candidate list | Invalid ID / quota → refuse or heuristic |
| **Gate** | Threshold + already-used bank txn check | Below threshold → exception |
| **Review** | Human Approve / Reject / Follow-up | Does not auto-move money |
| **Export** | PDF, Word, ZIP, CSV | Always includes the exception list |

---

## Every feature, explained

### 1. Multi-format document extract

SettleMatch does **not** ask users to convert files first. Drop whatever finance already has.

**Supported formats:** `.csv` · `.xlsx` · `.xls` · `.pdf` · `.docx` · `.txt`  
**Any mix works** — settlements as PDF + bank as Excel is fine.

**Settlements columns (7):**

`settlement_id` · `payment_id` · `amount` · `currency` · `utr` · `settled_at` · `status`

**Bank columns (5):**

`bank_txn_id` · `amount` · `narration` · `value_date` · `utr`

Column names are fuzzy-mapped (`UTR No`, `settlement date`, `particulars` all work). Extra columns are dropped. Missing optional fields get safe defaults (`currency = INR`). Required fields missing → extract fails with a clear error, so garbage never enters the matcher.

Preview after upload shows **filename · row count · format** so you know extract worked before you reconcile.

---

### 2. Upload & Reconcile (ad-hoc run)

The **Upload** page is the live demo path.

1. Upload settlements export  
2. Upload bank statement  
3. Set the **confidence gate** slider (0.50–0.99, default 0.85)  
4. Click **Reconcile** (disabled until both files extract cleanly)  
5. App auto-navigates to **Dashboard**

**Reset** clears the workspace (matches, exceptions, reviews, simulator).

This is the panel / video path. Production ingest lives on **Connections**.

---

### 3. Rules engine (deterministic first)

Rules run **before** any AI call. They are cheap, explainable, and high precision.

| Rule | When it fires | Confidence |
|---|---|---|
| **Exact UTR** | Same normalized UTR + amount within ₹0.01 | `1.0` |
| **Amount + date** | Unique amount match inside a ±1 day window | `1.0` |

If two bank rows compete for the same UTR or amount window, the rule **does not pick**. That is a collision, not a guess.

On the sample batch this layer closes **75 / 100** settlements with zero AI cost.

---

### 4. Collision detection

Collisions are the silent killer of reconciliation tools — two similar credits, one settlement, and a guessed link.

SettleMatch scans for:

- Duplicate / ambiguous UTRs across bank rows  
- Amount windows with more than one unused bank candidate  
- Already-used `bank_txn_id` (no double-spend)

Ambiguous cases are **blocked**, logged in `collisions.json`, and never auto-approved. On the sample batch: **15 collisions detected**.

---

### 5. Gemini AI matcher (leftovers only)

AI is **not** the first matcher. It only sees rows rules could not close.

Constraints:

- Prompt includes **one settlement + a short candidate list** (not the whole bank file)  
- Model must return JSON: `bank_txn_id`, `confidence`, `reason`, `refuse`  
- It **cannot invent** a `bank_txn_id` outside that list  
- If unsure, it must set `refuse: true`

**Model:** `gemini-3.6-flash` via `GEMINI_API_KEY`  
**Fallback:** if the key is missing, quota hits 429, or the model 404s, a **heuristic matcher** still finishes the loop so the demo never dies.

On the sample batch AI (or heuristic) closes **15** leftover matches that pass the gate.

---

### 6. Confidence gate

Every AI suggestion goes through `src/gate.py` before it becomes a match.

A suggestion is **refused** if:

- `refuse` is true or `bank_txn_id` is null  
- Confidence **< threshold** (default **0.85**, slider on Upload)  
- That bank txn is **already matched**

Refused rows become **exceptions** with a written reason. The gate is the product’s safety claim: *AI can suggest; it cannot close the books alone.*

---

### 7. Explainability

Every accepted match stores an explanation object:

- **Stage** — rules vs AI  
- **Method** — `rule_exact_utr` / `rule_amount_date` / `ai_gated`  
- **Confidence**  
- **Summary** + **step list** (UTR compared, amount window, candidate rank, gate pass)

On **Matches**, pick any `settlement_id` and read the full trail. Reviewers should never see a silent pairing.

Exceptions get the same treatment via `src/explain.py` — why it was refused, ₹ at risk, next human action.

---

### 8. Exception queue + human review

Track 04 wants leftover rows you could not close — not a perfect score.

On **Exceptions** you get:

- Open exception count  
- Collision count  
- Amount-at-risk histogram  
- Full table with current review status  

For each row, finance can:

| Action | Meaning |
|---|---|
| **Approve manually** | Human overrides — money link is accepted by ops, not by AI |
| **Reject / keep open** | Still unresolved |
| **Needs finance follow-up** | Escalated (bank / Razorpay / merchant) |

Reviews stay in session state and show in the sidebar (`Human reviews logged: N`). They **do not auto-move money**.

On the sample batch: **10 leftovers stay in the queue** for a human, not an auto-guess.

---

### 9. Dashboard KPIs and charts

After reconcile, **Dashboard** is the reviewer screen.

**Four KPIs**

| KPI | What it means |
|---|---|
| **Match rate** | Matched settlements / total settlements |
| **Recovery rate** | ₹ matched / total settlement value |
| **Money matched** | INR successfully linked |
| **Money at risk** | INR sitting in exceptions — not guessed |

**Also shown**

- Rules vs AI split  
- Collisions blocked  
- Gate threshold used  
- Gate threshold used on this run  

**Charts (Altair)**

- Match breakdown bar (rules / AI / exceptions)  
- Close-rate donut (matched vs exception)  
- Money recovered vs at risk  
- Who closed the loop (rules vs AI + gate)  
- AI confidence histogram when AI matches exist  

---

### 10. Confidence-gate simulator

**Simulator** answers: *what if we tighten or loosen the gate?*

It re-runs threshold sweeps on the same uploaded files and plots:

- Match rate vs threshold  
- Recovery rate vs threshold  
- Exception count vs threshold  
- Table of `threshold · match% · recovery% · matched · exceptions · ai_matches`

Use this in the pitch: 0.70 = more matches, more risk; 0.90 = fewer matches, cleaner books. **0.85 is the default balance.**

---

### 11. Export & audit pack

**Export** is the submission / ops artifact.

| Download | Contents |
|---|---|
| **PDF report** | Stats, matches, exceptions, source filenames |
| **Word report** | Same, editable for finance notes |
| **Audit pack (ZIP)** | Stats + matches + exceptions + collisions + full audit log + meta |
| **Matches CSV** | Spreadsheet import |

The **audit trail** table lists every accept / refuse with timestamped reason. If a reviewer asks “why was SET-042 linked to BK-118?”, the ZIP answers it.

---

### 12. Connections (production automation)

Manual upload does not scale to millions of users. **Connections** is the production story on one page.

| Control | Purpose |
|---|---|
| Razorpay **Key ID** + masked secret | Test-mode settlements API pull |
| Bank **SFTP** or **Webhook** | Daily bank credit ingest |
| **Schedule** (hour / minute) | Default daily 02:00 IST |
| **Auto-run** toggle | Arm / pause nightly reconcile |
| Last run / next run cards | “Auto ✓” status for the pitch |
| Recent auto-runs table | Pull → bank fetch → reconcile job |

This tab is a **product mock of the scale path**. Same engine as Upload. In production: webhook / SFTP → queue → per-merchant nightly job → humans only on exceptions.

---

### 13. Ground-truth eval

```powershell
python eval/run_eval.py
python eval/smoke_test.py
python eval/audit_extract.py
```

`eval/run_eval.py` compares pipeline output to `data/expected/ground_truth.csv` (correct, missed, leftover exceptions).

Extract audit covers **25 format combinations** (PDF×Excel, Word×CSV, etc.). Smoke test checks the happy path does not crash.

Headline quality number we show reviewers is **recovery rate (~87%)**, not a perfect 1.00 score. A 100% precision slide looks planted.

---

### 14. Workspace status (sidebar)

Always visible:

- Page nav: Upload · Connections · Dashboard · Matches · Exceptions · Simulator · Export  
- **Awaiting run** vs **Reconciliation ready**  
- Human review count after exceptions are actioned  

---

## Pages in the app

| Page | What you do |
|---|---|
| **Upload** | Drop files, set gate, Reconcile |
| **Connections** | Show Razorpay + bank auto-ingest + schedule |
| **Dashboard** | Read KPIs, charts, eval |
| **Matches** | Inspect accepted pairs + explanations |
| **Exceptions** | Review refused rows; Approve / Reject / Follow-up |
| **Simulator** | Sweep the gate; see tradeoffs |
| **Export** | Download PDF / Word / ZIP / CSV |

---

## Demo results

**Batch:** 100 settlements · 125 bank rows (`data/samples/`)

| Metric | Value |
|---|---|
| Match rate | **90%** (90 / 100) |
| Rules / AI | 75 / 15 |
| Exceptions still open | 10 |
| Collisions blocked | 15 |
| Money matched | ₹3,30,755 |
| Money at risk | ₹47,774 |
| Recovery rate | **87.4%** |

These are run numbers, not a 100% scorecard. 10 rows stay unmatched on purpose. Recovery (~87%) is the figure we treat as “how much of the money actually closed”.

---

## Tech stack

| Layer | Technology |
|---|---|
| Language | Python 3 |
| UI | Streamlit |
| Data | Pandas |
| Validation | Pydantic |
| AI | Google Gemini (`gemini-3.6-flash`) + heuristic fallback |
| Charts | Altair |
| PDF extract | pdfplumber |
| Excel | openpyxl |
| Word | python-docx |
| PDF reports | fpdf2 |
| Config | python-dotenv |

**Not in this demo (by design):** React, PostgreSQL, Docker, live Razorpay API. Those are the production path on **Connections**.

---

## Quick start

### 1. Clone

```bash
git clone https://github.com/kratagyaSingh-dev/SettleMatch.git
cd SettleMatch
```

### 2. Environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.6-flash
CONFIDENCE_THRESHOLD=0.85
```

No Gemini key? The app still runs end-to-end on the offline matcher.

### 3. Sample files

Already in the repo:

- `data/samples/settlements.csv` + `data/samples/bank.csv`  
- Same files as PDF / Excel / Word / TXT under `data/samples/` and `demo_samples/`

Regenerate if needed:

```powershell
python scripts/generate_data.py
python scripts/generate_sample_docs.py
```

### 4. Run

```powershell
streamlit run app.py
```

Open **http://localhost:8501** → **Upload** both files → **Reconcile**.

### 5. Walkthrough (for video)

1. Upload `settlements.csv` + `bank.csv` — confirm 100 + 125 rows  
2. Reconcile → Dashboard (90%, ₹ matched, 10 exceptions)  
3. Matches — open one explanation  
4. Exceptions — Approve / Follow-up one row  
5. Connections — “this is how it scales at night”  
6. Export — download audit ZIP  

---

## Safety invariants

1. AI never invents a `bank_txn_id` outside the candidate set  
2. Already-matched bank rows cannot be rematched  
3. Ambiguous collisions are refused, not guessed  
4. Below-threshold AI suggestions become exceptions  
5. Every accept / refuse is written to the audit log  
6. Human review never silently moves money  

---

## Repo map

| Path | Purpose |
|---|---|
| `app.py` | Streamlit UI — all 7 pages |
| `src/extract.py` | Multi-format extract + column mapping |
| `src/ingest.py` | Normalize dates, amounts, UTRs |
| `src/rules.py` | UTR + amount/date matcher |
| `src/collisions.py` | Ambiguity / double-spend checks |
| `src/ai_matcher.py` | Gemini + heuristic fallback |
| `src/gate.py` | Confidence threshold gate |
| `src/explain.py` | Exception explanations |
| `src/reconcile.py` | Pipeline orchestrator |
| `src/export_report.py` | PDF / Word / ZIP |
| `eval/` | Ground-truth eval, smoke, extract audit |
| `data/samples/` | Upload demo files |
| `data/expected/ground_truth.csv` | Eval labels |
| `demo_samples/` | 25-format combo fixtures |
| `docs/screenshots/` | UI screenshots |
| `architecture.md` | System design |
| `SettleMatch_Project_Guide.pdf` | Full manual |
| `SettleMatch_Pitch_Deck.pdf` | Pitch deck |
| `scripts/` | Data gen, capture, PDF builders |

`.env`, `.venv/`, and `output/` are gitignored.

---

## Production path

| Now (buildathon) | Later (scale) |
|---|---|
| Two-file upload | Razorpay API + bank SFTP / webhook |
| One click Reconcile | Nightly job per merchant |
| Session-state reviews | Postgres exception queue |
| Single workspace | Multi-tenant connections |

The matching engine does not change. Only **ingest** and **tenancy** do.

---

## Pitch script

1. **0:00** — Two lists. Manual matching. Audit pain.  
2. **0:45** — Upload live files. Reconcile.  
3. **1:30** — Dashboard: 90% match, ~87% recovery, 10 leftovers.  
4. **2:30** — One exception + human review. We refuse, we don’t guess.  
5. **3:30** — Connections: nightly Razorpay + bank ingest.  
6. **4:30** — Download audit pack. Close: *rules first, AI second, gate always.*

---

## Docs

- [`architecture.md`](architecture.md) — pipeline and invariants  
- [`SettleMatch_Project_Guide.pdf`](SettleMatch_Project_Guide.pdf) — full manual + screenshots  
- [`SettleMatch_Pitch_Deck.pdf`](SettleMatch_Pitch_Deck.pdf) — pitch deck  

---

## License

Built for the **Razorpay AI Buildathon** student internship application — Track 04, AI Finance Controller.
