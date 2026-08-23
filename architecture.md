# SettleMatch Architecture

## Track
Razorpay AI Buildathon — **04 AI Finance Controller**

## Goal
Close one finance-ops loop: reconcile merchant settlements to bank statement credits on a 100-record batch, report match rate and ₹ recovered, and list honest exceptions with auditability.

## Pipeline

```
PDF/Excel/Word/CSV/TXT
        │
        ▼
   Extract (strict schema only)
        │
        ▼
     Ingest normalize
        │
        ▼
   Rule matcher ──► Matches + Audit
        │ unmatched
        ▼
 Collision detector (ambiguous UTR / amount window)
        │
        ▼
   Gemini AI matcher (top-5 candidates only)
        │
        ▼
   Confidence gate (≥ threshold, no double-spend)
        │
        ├── accept → Matches
        └── refuse → Exceptions (+ human review queue)
                │
                ▼
     Report · Charts · PDF/Word/ZIP audit pack
```

## Stages

| Stage | Behavior | Failure handling |
|---|---|---|
| Extract | Map only required columns; drop extras | Bad/empty file → hard error |
| Rules | Exact UTR; unique amount ±1 day | Multi-candidate → collision / skip |
| AI | Gemini JSON pick from candidate list | Invalid ID / quota → refuse or heuristic fallback |
| Gate | Threshold (default 0.85) | Below threshold → exception |
| Review | Human approve / reject / follow-up | Does not auto-move money |
| Export | PDF, Word, ZIP audit pack | Always includes exception list |

## Safety invariants

1. AI never invents a `bank_txn_id` outside the candidate set  
2. Already-matched bank txns cannot be rematched  
3. Ambiguous collisions are refused, not guessed  
4. Every accept/refuse is written to the audit log  

## Metrics

- Match rate, recovery rate  
- Money matched vs money at risk (INR)  
- Rules vs AI split  
- Collisions detected  
- Ground-truth precision / recall / false matches (`eval/`)  

## Why this is Track 04

Verification capacity beats generation speed. SettleMatch optimizes for **measured close of a finance loop** with an honest exception list — not a chatbot wrapper.
