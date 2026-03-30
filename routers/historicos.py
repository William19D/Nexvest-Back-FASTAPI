"""
routers/historicos.py
---------------------
Endpoints for querying historical stock data stored in MongoDB.

Este módulo proporciona acceso a datos históricos de acciones de la BVC
almacenadas en MongoDB con validaciones y filtrado flexible.

MongoDB Collection Naming Convention:
    historico_<mnemonic_lowercase>
    Ejemplos:
        - historico_ecopetrol
        - historico_geb
        - historico_isa
        - historico_pfbcolom

Available Endpoints:
    GET /historicos/mnemonics
        Retorna lista de todos los mnemonics disponibles
    
    GET /historicos/{mnemonic}
        Retorna registros históricos con filtros opcionales por fecha
    
    GET /historicos/{mnemonic}/{date}
        Retorna el registro para una fecha específica (YYYY-MM-DD)

Features:
    - Filtrado por rango de fechas
    - Limit configurable
    - Validación de mnemonics
    - Serialización automática de documentos MongoDB
    - Manejo robusto de errores
    - Logging detallado de operaciones

Data Format:
    Records contienen campos:
        - date: Fecha (YYYY-MM-DD)
        - close: Precio de cierre
        - volume: Volumen
        - open: Precio apertura
        - high: Máximo del día
        - low: Mínimo del día

Author:
    NexVest Development Team
    
Version:
    1.0.0
"""

import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.database import Database
from pymongo.cursor import Cursor

from database import get_db

# ── Logger Setup ──────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

# ── Router Configuration ──────────────────────────────────────────────────────
router = APIRouter(
    prefix="/historicos",
    tags=["Históricos"],
    responses={
        404: {"description": "Mnemónico o fecha no encontrada"},
        400: {"description": "Parámetros inválidos"},
        500: {"description": "Error interno del servidor"}
    }
)

# ── Constants & Configuration ─────────────────────────────────────────────────
# Known mnemonics para validación y documentación
KNOWN_MNEMONICS: List[str] = [
    "ecopetrol",
    "geb",
    "isa",
    "pfbcolom",
    "celsia",
    "cemargos",
    "clh",
    "cnec",
    "corficolcf",
    "cspx.l",
    "exito",
    "gruposura",
    "mineros",
    "nutresa",
    "promigas",
]

# Default limit para queries sin date range
DEFAULT_LIMIT: int = 100

# Default sort order
DEFAULT_SORT: int = 1  # 1 para ascendente, -1 para descendente


# ── Utility Functions ─────────────────────────────────────────────────────────

def _collection_name(mnemonic: str) -> str:
    """
    Convierte un mnemónico a nombre de colección MongoDB.
    
    Args:
        mnemonic: Símbolo de la acción (ej: "ECOPETROL")
        
    Returns:
        str: Nombre de colección (ej: "historico_ecopetrol")
        
    Example:
        >>> _collection_name("ECOPETROL")
        'historico_ecopetrol'
    """
    return f"historico_{mnemonic.lower()}"


def _serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convierte documento MongoDB a dict JSON-serializable.
    
    Elimina el campo _id que MongoDB añade automáticamente,
    ya que no es necesario en la respuesta API.
    
    Args:
        doc: Documento MongoDB
        
    Returns:
        Dict sin el campo _id
        
    Example:
        >>> doc = {"_id": ObjectId(...), "date": "2024-01-01", "close": 100}
        >>> _serialize(doc)
        {'date': '2024-01-01', 'close': 100}
    """
    if doc is None:
        return {}
    doc.pop("_id", None)
    return doc


def _validate_date_format(date_str: str) -> bool:
    """
    Valida que una fecha tenga el formato YYYY-MM-DD.
    
    Args:
        date_str: String de fecha a validar
        
    Returns:
        bool: True si el formato es válido
        
    Example:
        >>> _validate_date_format("2024-01-15")
        True
        >>> _validate_date_format("15/01/2024")
        False
    """
    if not date_str:
        return False
    try:
        parts = date_str.split("-")
        if len(parts) != 3:
            return False
        year, month, day = parts
        if len(year) != 4 or len(month) != 2 or len(day) != 2:
            return False
        int(year), int(month), int(day)
        return True
    except (ValueError, AttributeError):
        return False


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "/mnemonics",
    summary="Lista de acciones disponibles",
    response_description="Lista de mnemonics con datos almacenados"
)
def list_mnemonics(db: Database = Depends(get_db)) -> Dict[str, Any]:
    """
    Retorna lista de todos los mnemonics disponibles en la base de datos.
    
    Consulta MongoDB para obtener todas las colecciones que comienzan
    con 'historico_' y retorna los mnemonics en formato uppercase.
    
    Args:
        db: Dependencia de base de datos (inyectada por FastAPI)
        
    Returns:
        Dict con lista de mnemonics disponibles
        
    Raises:
        HTTPException: Si hay error al consultar colecciones
        
    Response Example:
        {
            "mnemonics": ["CELSIA", "ECOPETROL", "GEB", "ISA"],
            "total": 4
        }
    """
    try:
        logger.debug("Listando mnemonics disponibles")
        collections = db.list_collection_names()
        
        mnemonics = [
            c.replace("historico_", "").upper()
            for c in collections
            if c.startswith("historico_")
        ]
        
        mnemonics = sorted(mnemonics)
        logger.info(f"Se encontraron {len(mnemonics)} mnemonics disponibles")
        
        return {
            "mnemonics": mnemonics,
            "total": len(mnemonics),
            "status": "ok"
        }
    except Exception as exc:
        logger.error(f"Error al listar mnemonics: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al acceder a colecciones: {str(exc)}"
        )


@router.get(
    "/{mnemonic}",
    summary="Datos históricos de una acción",
    response_description="Registros históricos con fecha, precio y volumen"
)
def get_historico(
    mnemonic: str = Query(..., description="Símbolo de la acción (ej: ECOPETROL)"),
    desde: Optional[str] = Query(
        None,
        description="Fecha inicio YYYY-MM-DD (inclusive)",
        example="2024-01-01"
    ),
    hasta: Optional[str] = Query(
        None,
        description="Fecha fin YYYY-MM-DD (inclusive)",
        example="2024-12-31"
    ),
    limit: Optional[int] = Query(
        None,
        ge=1,
        le=10000,
        description="Máximo de registros a retornar. Sin filtro de fechas, default es 100."
    ),
    db: Database = Depends(get_db),
) -> Dict[str, Any]:
    """
    Retorna registros históricos para un mnemónico con filtros opcionales.
    
    Comportamiento del limit:
        - Si no se especifica fecha y no hay limit: retorna máximo 100 registros
        - Si se especifica rango de fechas y no hay limit: retorna TODOS los registros
        - Si se especifica limit: se respeta independientemente de fechas
    
    Comportamiento de ordenamiento:
        Los resultados siempre se ordenan por fecha ascendente (más antiguos primero).
    
    Args:
        mnemonic: Símbolo de acción (ej: "ECOPETROL")
        desde: Fecha inicio opcional (YYYY-MM-DD)
        hasta: Fecha fin opcional (YYYY-MM-DD)
        limit: Límite de registros a retornar
        db: Dependencia de base de datos
        
    Returns:
        Dict con:
            - mnemonic: Símbolo consultado
            - total: Cantidad de registros retornados
            - desde/hasta: Fechas de filtro (si aplican)
            - data: Lista de registros históricos
            
    Raises:
        HTTPException 404: Si el mnemónico no existe
        HTTPException 400: Si las fechas son inválidas
        HTTPException 500: Si hay error al consultar
        
    Response Example:
        {
            "mnemonic": "ECOPETROL",
            "total": 5,
            "desde": "2024-01-01",
            "hasta": "2024-01-05",
            "data": [
                {
                    "date": "2024-01-01",
                    "close": 2650.0,
                    "volume": 15000000,
                    "open": 2640.0,
                    "high": 2680.0,
                    "low": 2630.0
                },
                ...
            ]
        }
    """
    try:
        logger.debug(f"Consultando históricos de {mnemonic}")
        
        # Validar formato de fechas
        if desde and not _validate_date_format(desde):
            logger.warning(f"Fecha 'desde' inválida: {desde}")
            raise HTTPException(
                status_code=400,
                detail=f"Formato de fecha 'desde' inválido. Use YYYY-MM-DD (recibi: {desde})"
            )
        
        if hasta and not _validate_date_format(hasta):
            logger.warning(f"Fecha 'hasta' inválida: {hasta}")
            raise HTTPException(
                status_code=400,
                detail=f"Formato de fecha 'hasta' inválido. Use YYYY-MM-DD (recibi: {hasta})"
            )
        
        # Verificar que la colección existe
        col_name = _collection_name(mnemonic)
        if col_name not in db.list_collection_names():
            logger.info(f"Mnemónico no encontrado: {mnemonic}")
            raise HTTPException(
                status_code=404,
                detail=(
                    f"No se encontró información para el mnemónico '{mnemonic.upper()}'. "
                    f"Mnemonics disponibles: {', '.join(KNOWN_MNEMONICS).upper()}"
                ),
            )
        
        # Construir query de filtro
        query: Dict[str, Any] = {}
        has_date_filter = bool(desde or hasta)
        
        if has_date_filter:
            query["date"] = {}
            if desde:
                query["date"]["$gte"] = desde
            if hasta:
                query["date"]["$lte"] = hasta
        
        # Determinar limit efectivo
        effective_limit = (
            limit 
            if limit is not None 
            else (None if has_date_filter else DEFAULT_LIMIT)
        )
        
        # Ejecutar query
        collection = db[col_name]
        cursor: Cursor = collection.find(query, {"_id": 0}).sort("date", DEFAULT_SORT)
        
        if effective_limit is not None:
            cursor = cursor.limit(effective_limit)
        
        records = list(cursor)
        
        logger.info(
            f"Query exitoso: {mnemonic.upper()} - {len(records)} registros "
            f"(desde={desde}, hasta={hasta}, limit={limit})"
        )
        
        return {
            "mnemonic": mnemonic.upper(),
            "total": len(records),
            "desde": desde,
            "hasta": hasta,
            "limit_applied": effective_limit,
            "data": records,
            "status": "ok"
        }
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error al consultar históricos de {mnemonic}: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar datos: {str(exc)}"
        )


@router.get(
    "/{mnemonic}/{date}",
    summary="Registro de una fecha específica",
    response_description="Registro histórico para una fecha exacta"
)
def get_historico_by_date(
    mnemonic: str = Query(..., description="Símbolo de la acción"),
    date: str = Query(..., description="Fecha exact (YYYY-MM-DD)", example="2024-01-15"),
    db: Database = Depends(get_db),
) -> Dict[str, Any]:
    """
    Retorna el registro histórico para un mnemónico en una fecha específica.
    
    Args:
        mnemonic: Símbolo de acción
        date: Fecha exacta en formato YYYY-MM-DD
        db: Dependencia de base de datos
        
    Returns:
        Dict con el registro histórico:
            - date: Fecha
            - close: Precio de cierre
            - volume: Volumen
            - open: Precio de apertura
            - high: Máximo del día
            - low: Mínimo del día
            
    Raises:
        HTTPException 404: Si no hay registro para esa fecha
        HTTPException 400: Si el formato de fecha es inválido
        HTTPException 500: Si hay error al consultar
        
    Response Example:
        {
            "date": "2024-01-15",
            "close": 2750.0,
            "volume": 22500000,
            "open": 2700.0,
            "high": 2800.0,
            "low": 2680.0,
            "mnemonic": "ECOPETROL",
            "status": "ok"
        }
    """
    try:
        logger.debug(f"Consultando {mnemonic} para fecha {date}")
        
        # Validar formato de fecha
        if not _validate_date_format(date):
            logger.warning(f"Formato de fecha inválido: {date}")
            raise HTTPException(
                status_code=400,
                detail=f"Formato de fecha inválido. Use YYYY-MM-DD (recibió: {date})"
            )
        
        # Verificar que la colección existe
        col_name = _collection_name(mnemonic)
        if col_name not in db.list_collection_names():
            logger.info(f"Mnemónico no encontrado: {mnemonic}")
            raise HTTPException(
                status_code=404,
                detail=f"No se encontró información para '{mnemonic.upper()}'.",
            )
        
        # Buscar documento
        doc = db[col_name].find_one({"date": date}, {"_id": 0})
        
        if not doc:
            logger.info(f"No hay registro para {mnemonic.upper()} en {date}")
            raise HTTPException(
                status_code=404,
                detail=f"No hay registro para {mnemonic.upper()} en la fecha {date}.",
            )
        
        # Añadir metadata
        doc["mnemonic"] = mnemonic.upper()
        doc["status"] = "ok"
        
        logger.info(f"Registro encontrado: {mnemonic.upper()} en {date}")
        return doc
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error al consultar {mnemonic} para {date}: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar datos: {str(exc)}"
        )

