"""CSV validation and repeat-safe SQLite loading."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "data" / "sales.csv"
DEFAULT_DB_PATH = BASE_DIR / "data" / "sales.db"
REQUIRED = ["Transaction_Id", "Order_date", "Product", "Category", "Region", "Sales_channel", "Quantity", "Unit_price", "Discount_amount", "Status"]


def get_db_path(path: str | Path | None = None) -> Path:
    value = path or os.getenv("DATABASE_PATH") or DEFAULT_DB_PATH
    result = Path(value)
    return result if result.is_absolute() else (BASE_DIR / result).resolve()


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    db_path = get_db_path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database(db_path: str | Path | None = None, csv_path: str | Path | None = None) -> dict:
    source = Path(csv_path) if csv_path else CSV_PATH
    if not source.exists():
        raise FileNotFoundError(f"Sales CSV not found: {source}")
    frame = pd.read_csv(source, dtype={"Transaction_Id": "string"})
    missing = [column for column in REQUIRED if column not in frame.columns]
    if missing:
        raise ValueError(f"CSV is missing required columns: {', '.join(missing)}")
    frame = frame[REQUIRED].copy()
    frame["Order_date"] = pd.to_datetime(frame["Order_date"], format="%d-%m-%Y", errors="coerce")
    for col in ["Quantity", "Unit_price", "Discount_amount"]:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    conn = connect(db_path)
    try:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS sales (
          transaction_id TEXT PRIMARY KEY, order_date TEXT, product TEXT, category TEXT,
          region TEXT, sales_channel TEXT, quantity REAL, unit_price REAL,
          discount_amount REAL, status TEXT, net_revenue REAL, eligible INTEGER NOT NULL,
          exclusion_reason TEXT
        );
        CREATE TABLE IF NOT EXISTS import_state (source TEXT PRIMARY KEY, imported_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS import_exclusions (
          source TEXT NOT NULL, row_number INTEGER NOT NULL, transaction_id TEXT, reason TEXT NOT NULL,
          PRIMARY KEY(source, row_number)
        );
        """)
        already = conn.execute("SELECT 1 FROM import_state WHERE source=?", (str(source.resolve()),)).fetchone()
        if already:
            total = conn.execute("SELECT COUNT(*) FROM sales").fetchone()[0] + conn.execute("SELECT COUNT(*) FROM import_exclusions").fetchone()[0]
            eligible = conn.execute("SELECT COUNT(*) FROM sales WHERE eligible=1").fetchone()[0]
            return {"imported": total, "eligible": eligible, "excluded": total - eligible, "already_imported": True}
        seen: set[str] = set()
        rows = []
        duplicate_exclusions = []
        for row_number, record in enumerate(frame.to_dict(orient="records"), start=2):
            txid = str(record["Transaction_Id"]).strip() if pd.notna(record["Transaction_Id"]) else ""
            reason = []
            if not txid: reason.append("missing transaction ID")
            elif txid in seen:
                duplicate_exclusions.append((str(source.resolve()), row_number, txid, "duplicate transaction ID"))
                continue
            else: seen.add(txid)
            for col in ["Order_date", "Product", "Category", "Region", "Sales_channel", "Quantity", "Unit_price", "Discount_amount", "Status"]:
                if pd.isna(record[col]) or (isinstance(record[col], str) and not record[col].strip()): reason.append(f"missing {col}")
            if pd.notna(record["Unit_price"]) and record["Unit_price"] < 0: reason.append("invalid negative unit price")
            if pd.notna(record["Quantity"]) and record["Quantity"] < 0: reason.append("invalid negative quantity")
            if pd.notna(record["Discount_amount"]) and record["Discount_amount"] < 0: reason.append("invalid negative discount")
            if str(record["Status"]).strip().lower() == "returned": reason.append("returned transaction")
            quantity, price, discount = record["Quantity"], record["Unit_price"], record["Discount_amount"]
            revenue = quantity * price - discount if all(pd.notna(x) for x in (quantity, price, discount)) else None
            if revenue is not None and revenue < 0: reason.append("negative net revenue")
            rows.append((txid or None, record["Order_date"].strftime("%Y-%m-%d") if pd.notna(record["Order_date"]) else None,
                record["Product"] if pd.notna(record["Product"]) else None, record["Category"] if pd.notna(record["Category"]) else None,
                record["Region"] if pd.notna(record["Region"]) else None, record["Sales_channel"] if pd.notna(record["Sales_channel"]) else None,
                float(quantity) if pd.notna(quantity) else None, float(price) if pd.notna(price) else None,
                float(discount) if pd.notna(discount) else None, record["Status"] if pd.notna(record["Status"]) else None,
                float(revenue) if revenue is not None else None, 0 if reason else 1, "; ".join(dict.fromkeys(reason)) or None))
        conn.executemany("INSERT OR IGNORE INTO sales VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
        conn.executemany("INSERT OR IGNORE INTO import_exclusions VALUES (?,?,?,?)", duplicate_exclusions)
        conn.execute("INSERT INTO import_state(source) VALUES (?)", (str(source.resolve()),))
        conn.commit()
        total = conn.execute("SELECT COUNT(*) FROM sales").fetchone()[0] + conn.execute("SELECT COUNT(*) FROM import_exclusions").fetchone()[0]
        eligible = conn.execute("SELECT COUNT(*) FROM sales WHERE eligible=1").fetchone()[0]
        return {"imported": total, "eligible": eligible, "excluded": total - eligible, "already_imported": False}
    finally:
        conn.close()


def get_exclusions(db_path: str | Path | None = None) -> list[dict]:
    with connect(db_path) as conn:
        invalid_rows = [dict(row) for row in conn.execute("SELECT transaction_id, exclusion_reason FROM sales WHERE eligible=0")]
        duplicate_rows = [dict(row) for row in conn.execute("SELECT transaction_id, reason AS exclusion_reason FROM import_exclusions")]
        return invalid_rows + duplicate_rows
