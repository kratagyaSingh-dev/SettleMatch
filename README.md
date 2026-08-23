# SettleMatch

**Razorpay AI Buildathon — Track 04: AI Finance Controller**

SettleMatch closes one finance-ops loop: reconcile **Razorpay settlements** to **bank statement credits** with rules first, Gemini on leftovers, a confidence gate, collision detection, and an honest exception list.

> Every money-adjacent decision is explainable, bounded, and gated. Ambiguous cases are refused — never guessed.

---

## Problem

Finance teams get money in two places:

1. Razorpay settlement exports  
2. Bank statement credits  

Matching them by hand is slow, error-prone, and hard to audit. Generic AI chatbots *guess* links. Finance needs **verification capacity** — measured accuracy and a clear refuse path.

## Solution

SettleMatch runs a bounded pipeline:

```
Documents (PDF / Excel / Word / CSV / TXT)
        │
        ▼
   Extract (strict columns only)
        │
        ▼
   Rules (UTR · amount + date window)
        │ unmatched
        ▼
   Collision check
        │
        ▼
   Gemini on leftovers (candidate list only)
        │
        ▼
   Confidence gate (default ≥ 0.85)
        ├── accept → Matches + explanation
        └── refuse → Exceptions + human review
                │
                ▼
   Dashboard · Simulator · PDF / Word / Audit ZIP
```

**Product promise:** Rules first. AI second. Gate always.

---

## Demo results (100 settlements · 125 bank rows)

| Metric | Result |
|---|---|
| Match rate | **90%** (90 / 100) |
| Rules / AI | 75 / 15 |
| Exceptions | 10 honest refusals |
| Money matched | ₹3,30,755 |
| Money at risk | ₹47,774 |
| Recovery rate | 87.4% |
| False matches (eval) | **0** |
| Precision / recall (eval) | **1.0 / 1.0** |

---

## Features

- **Upload & reconcile** — ad-hoc runs on your own settlement + bank files  
- **Multi-format ingest** — PDF · Excel · Word · CSV · TXT (any mix)  
- **Connections** — production path: Razorpay test API + bank SFTP/webhook + daily schedule  
- **Dashboard** — match rate, recovery rate, ₹ matched vs at risk, charts, ground-truth eval  
- **Matches** — accepted pairs with step-by-step explainability  
- **Exceptions** — refused rows + human review (Approve / Reject / Follow-up)  
- **Simulator** — confidence-gate threshold tradeoffs  
- **Export** — PDF report, Word report, audit ZIP, matches CSV  
- **Safety** — AI cannot invent bank IDs; no double-spend; collisions refused  

---

## Tech stack

| Layer | Technology |
|---|---|
| Language | Python 3 |
| UI | Streamlit |
| Data | Pandas |
| AI | Google Gemini (`gemini-3.6-flash`) + heuristic fallback |
| Charts | Altair |
| Extract | pdfplumber · openpyxl · python-docx |
| Reports | fpdf2 · python-docx |
| Config | python-dotenv |

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

Add your key in `.env`:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.6-flash
CONFIDENCE_THRESHOLD=0.85
```

> Without a Gemini key, SettleMatch still runs end-to-end using the offline heuristic matcher.

### 3. Sample data (optional)

```powershell
python scripts/generate_data.py
python scripts/generate_sample_docs.py
```

Sample upload files live in `data/samples/` (CSV) and `demo_samples/`.

### 4. Run the app

```powershell
streamlit run app.py
```

Open **http://localhost:8501**

### 5. Product flow

1. **Upload** — drop settlements + bank files → **Reconcile**  
2. **Connections** — production ingest story (API / SFTP / schedule)  
3. **Dashboard** — KPIs + charts + eval strip  
4. **Matches** — accepted pairs + explanations  
5. **Exceptions** — refuse reasons + human review  
6. **Simulator** — gate threshold tradeoffs  
7. **Export** — PDF / Word / audit ZIP  

---

## Eval & accuracy

```powershell
python eval/run_eval.py
python eval/smoke_test.py
python eval/audit_extract.py
```

Outputs land in `output/` (gitignored). Eval metrics are also shown on the Dashboard.

---

## Repo map

| Path | Purpose |
|---|---|
| `app.py` | Streamlit multi-page product UI |
| `src/` | Extract, rules, AI, gate, collisions, reconcile, export |
| `architecture.md` | System design for reviewers |
| `eval/` | Ground-truth eval + smoke / extract audits |
| `data/samples/` | Sample settlement + bank files for upload |
| `demo_samples/` | Multi-format sample docs + combo outputs |
| `docs/screenshots/` | UI screenshots for the project guide |
| `SettleMatch_Project_Guide.pdf` | Full project manual + walkthrough |
| `SettleMatch_Pitch_Deck.pdf` | Pitch deck |
| `scripts/` | Data generation, capture, PDF builders |

---

## Safety invariants

1. AI never invents a `bank_txn_id` outside the candidate set  
2. Already-matched bank rows cannot be rematched  
3. Ambiguous collisions are refused, not guessed  
4. Every accept / refuse is written to the audit log  

---

## Production path

The **Connections** tab shows how this scales beyond manual upload:

- Razorpay settlements API (test → production keys)  
- Bank SFTP or webhook ingest  
- Daily auto-reconcile schedule  
- Humans only touch the **exception queue**  

Upload remains for ad-hoc / panel demos. Same pipeline either way.

---

## Pitch (5 min)

1. Problem — two lists, manual matching  
2. Live **Upload → Reconcile → Dashboard**  
3. Architecture — rules → AI → gate  
4. One refused exception + human review  
5. Connections (auto-ingest story) + download audit pack  

---

## Docs

- [`architecture.md`](architecture.md) — pipeline & invariants  
- [`SettleMatch_Project_Guide.pdf`](SettleMatch_Project_Guide.pdf) — full manual with screenshots  
- [`SettleMatch_Pitch_Deck.pdf`](SettleMatch_Pitch_Deck.pdf) — pitch deck  

---

## License

Built for the **Razorpay AI Buildathon** student internship application (Track 04 — AI Finance Controller).
