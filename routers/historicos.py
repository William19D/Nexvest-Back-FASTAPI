"""
routers/historicos.py
---------------------
Endpoints for querying historical stock data stored in MongoDB.

Collections follow the naming convention:  historico_<mnemonic_lowercase>
e.g.  historico_ecopetrol, historico_geb, historico_isa, historico_pfbcolom

Available endpoints
-------------------
GET /historicos/mnemonics
    List all available stock mnemonics.

GET /historicos/{mnemonic}
    Return all records for a stock, with optional date-range filters.

GET /historicos/{mnemonic}/{date}
    Return the single record for an exact date (YYYY-MM-DD).
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.database import Database

from database import get_db

router = APIRouter(prefix="/historicos", tags=["Históricos"])

# ── known mnemonics ────────────────────────────────────────────────────────────
KNOWN_MNEMONICS = ["ecopetrol", "geb", "isa", "pfbcolom"]


def _collection_name(mnemonic: str) -> str:
    return f"historico_{mnemonic.lower()}"


def _serialize(doc: dict) -> dict:
    """Convert MongoDB document to JSON-serialisable dict (remove _id)."""
    doc.pop("_id", None)
    return doc


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.get("/mnemonics", summary="Lista de acciones disponibles")
def list_mnemonics(db: Database = Depends(get_db)):
    """
    Returns every stock mnemonic that has a collection in MongoDB.
    """
    collections = db.list_collection_names()
    mnemonics = [
        c.replace("historico_", "").upper()
        for c in collections
        if c.startswith("historico_")
    ]
    return {"mnemonics": sorted(mnemonics)}


@router.get(
    "/{mnemonic}",
    summary="Datos históricos de una acción",
)
def get_historico(
    mnemonic: str,
    desde: Optional[str] = Query(
        None, description="Fecha inicio (YYYY-MM-DD) inclusive"
    ),
    hasta: Optional[str] = Query(
        None, description="Fecha fin (YYYY-MM-DD) inclusive"
    ),
    limit: Optional[int] = Query(
        None, ge=1, description="Máximo de registros a retornar. Sin filtro de fechas el default es 100."
    ),
    db: Database = Depends(get_db),
):
    """
    Retrieves historical records for `mnemonic`.

    - **desde** / **hasta**: optional date filters (YYYY-MM-DD).
      When a date range is provided, ALL matching records are returned unless `limit` is also specified.
    - **limit**: max records returned. Defaults to 100 only when no date range is given.

    Records are returned sorted by date ascending.
    """
    col_name = _collection_name(mnemonic)
    if col_name not in db.list_collection_names():
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró información para el mnemónico '{mnemonic.upper()}'. "
                   f"Disponibles: {', '.join(m.upper() for m in KNOWN_MNEMONICS)}",
        )

    query: dict = {}
    has_date_filter = bool(desde or hasta)
    if has_date_filter:
        query["date"] = {}
        if desde:
            query["date"]["$gte"] = desde
        if hasta:
            query["date"]["$lte"] = hasta

    # Apply limit only when explicitly requested or when there is no date filter
    effective_limit = limit if limit is not None else (None if has_date_filter else 100)

    cursor = db[col_name].find(query, {"_id": 0}).sort("date", 1)
    if effective_limit is not None:
        cursor = cursor.limit(effective_limit)

    records = list(cursor)

    return {
        "mnemonic": mnemonic.upper(),
        "total": len(records),
        "desde": desde,
        "hasta": hasta,
        "data": records,
    }


@router.get(
    "/{mnemonic}/{date}",
    summary="Registro de una fecha específica",
)
def get_historico_by_date(
    mnemonic: str,
    date: str,
    db: Database = Depends(get_db),
):
    """
    Returns the single historical record for `mnemonic` on `date` (YYYY-MM-DD).
    """
    col_name = _collection_name(mnemonic)
    if col_name not in db.list_collection_names():
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró información para '{mnemonic.upper()}'.",
        )

    doc = db[col_name].find_one({"date": date}, {"_id": 0})
    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"No hay registro para {mnemonic.upper()} en la fecha {date}.",
        )

    return doc
