"""
storage.py
----------
Loads all historical JSON files from the `historicos/` folder
and upserts each record into MongoDB Atlas.

Each stock gets its own collection named after its mnemonic (e.g. ECOPETROL, GEB).
Documents are upserted by the `date` field so re-running is safe.

Usage:
    python -m etl.storage
"""

import json
import os
from pathlib import Path

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo import UpdateOne

# ── MongoDB connection ────────────────────────────────────────────────────────
MONGO_URI = (
    "mongodb+srv://nextVest_db_user:W0UiUrEoCgAH40x2"
    "@nexvest.kujeo6o.mongodb.net/?appName=NexVest"
)
DB_NAME = "nexvest"

# ── Path to historical data ───────────────────────────────────────────────────
HISTORICOS_DIR = Path(__file__).resolve().parent.parent / "historicos"


def get_client() -> MongoClient:
    """Create and return a MongoClient, verifying the connection with a ping."""
    client = MongoClient(MONGO_URI, server_api=ServerApi("1"))
    client.admin.command("ping")
    print("Connected to MongoDB Atlas successfully.")
    return client


def load_json(file_path: Path) -> list[dict]:
    """Read a JSON file and return the list of records."""
    with open(file_path, encoding="utf-8") as f:
        data = json.load(f)
    # Keep only well-formed records (must have at least a date)
    valid = [r for r in data if isinstance(r, dict) and r.get("date")]
    dropped = len(data) - len(valid)
    if dropped:
        print(f"  ⚠  Dropped {dropped} incomplete record(s) from {file_path.name}")
    return valid


def upsert_records(collection, records: list[dict]) -> dict:
    """
    Bulk-upsert records into `collection`.
    Each record is matched by its `date` field.
    Returns a summary dict with upserted/modified counts.
    """
    if not records:
        return {"upserted": 0, "modified": 0}

    operations = [
        UpdateOne(
            filter={"date": rec["date"]},
            update={"$set": rec},
            upsert=True,
        )
        for rec in records
    ]

    result = collection.bulk_write(operations, ordered=False)
    return {
        "upserted": result.upserted_count,
        "modified": result.modified_count,
    }


def upload_historicos(historicos_dir: Path = HISTORICOS_DIR) -> None:
    """
    Iterate over every *_historico.json file in `historicos_dir`,
    derive the collection name from the mnemonic, and upsert all records.
    """
    json_files = sorted(historicos_dir.glob("*_historico.json"))

    if not json_files:
        print(f"No *_historico.json files found in {historicos_dir}")
        return

    client = get_client()
    db = client[DB_NAME]

    for file_path in json_files:
        # Derive mnemonic from filename, e.g. ECOPETROL_historico.json → ECOPETROL
        mnemonic = file_path.stem.replace("_historico", "")
        collection_name = f"historico_{mnemonic.lower()}"

        print(f"\nProcessing {file_path.name} → collection '{collection_name}' ...")
        records = load_json(file_path)
        print(f"  Loaded {len(records)} valid records.")

        collection = db[collection_name]
        summary = upsert_records(collection, records)
        print(f"  Done — upserted: {summary['upserted']}, modified: {summary['modified']}")

    client.close()
    print("\nAll files uploaded. Connection closed.")


if __name__ == "__main__":
    upload_historicos()
