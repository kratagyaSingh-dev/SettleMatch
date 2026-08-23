"""Load settlements and bank statement CSVs into normalized DataFrames."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REQUIRED_SETTLEMENT_COLS = {
    "settlement_id",
    "payment_id",
    "amount",
    "currency",
    "utr",
    "settled_at",
    "status",
}
REQUIRED_BANK_COLS = {
    "bank_txn_id",
    "amount",
    "narration",
    "value_date",
    "utr",
}


def _normalize_utr(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip().upper()
    return "".join(ch for ch in text if ch.isalnum())


def _normalize_amount(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").round(2)


def load_settlements(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = REQUIRED_SETTLEMENT_COLS - set(df.columns)
    if missing:
        raise ValueError(f"Settlements CSV missing columns: {sorted(missing)}")
    df = df.copy()
    df["amount"] = _normalize_amount(df["amount"])
    df["settled_at"] = pd.to_datetime(df["settled_at"], errors="coerce")
    df["utr_norm"] = df["utr"].map(_normalize_utr)
    df["status"] = df["status"].astype(str).str.lower()
    return df


def load_bank(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = REQUIRED_BANK_COLS - set(df.columns)
    if missing:
        raise ValueError(f"Bank CSV missing columns: {sorted(missing)}")
    df = df.copy()
    df["amount"] = _normalize_amount(df["amount"])
    df["value_date"] = pd.to_datetime(df["value_date"], errors="coerce")
    df["utr_norm"] = df["utr"].map(_normalize_utr)
    df["narration"] = df["narration"].fillna("").astype(str)
    return df
