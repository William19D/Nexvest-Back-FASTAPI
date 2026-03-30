"""
routers/analisis.py
-------------------
Endpoints de análisis y benchmarking de algoritmos de ordenamiento.

Este módulo implementa endpoints que ejecutan análisis de rendimiento
de múltiples algoritmos de ordenamiento sobre datos históricos reales
de la BVC (Bolsa de Valores de Colombia).

Análisis Disponibles:
    1. Ejecuta 12 algoritmos de ordenamiento distintos
    2. Mide tiempos de ejecución en segundos
    3. Genera ranking ascendente de mejores algoritmos
    4. Calcula top 15 días de mayor volumen por activo
    5. Genera gráfics PNG de resultados

Algoritmos Incluidos:
    - TimSort (Python default)
    - Comb Sort
    - Selection Sort
    - Tree Sort
    - Pigeonhole Sort
    - Bucket Sort
    - QuickSort
    - HeapSort
    - Bitonic Sort
    - Gnome Sort
    - Binary Insertion Sort
    - RadixSort

Almacenamiento:
    - Los resultados se guardan en etl/resultados_analisis (desarrollo)
    - En Vercel se usan /tmp (la única carpeta escribible)

Features:
    - Limitación configurable de registros
    - Opción de incluir dataset ordenado completo
    - Error handling robusto
    - Logging detallado
    - Soporte para Vercel serverless

Author:
    NexVest Development Team
    
Version:
    1.0.0
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Query

from algorithms.desempeno import ejecutar_analisis_ordenamiento

# ── Logger Setup ──────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

# ── Router Configuration ──────────────────────────────────────────────────────
router = APIRouter(
    prefix="/analisis",
    tags=["Análisis"],
    responses={
        404: {"description": "Datos no encontrados"},
        422: {"description": "Validación de datos falló"},
        500: {"description": "Error interno del servidor"}
    }
)

# ── Constants ─────────────────────────────────────────────────────────────────
# Algoritmos soportados por este endpoint
ALGORITMOS_SOPORTADOS = [
    "TimSort",
    "Comb Sort",
    "Selection Sort",
    "Tree Sort",
    "Pigeonhole Sort",
    "Bucket Sort",
    "QuickSort",
    "HeapSort",
    "Bitonic Sort",
    "Gnome Sort",
    "Binary Insertion Sort",
    "RadixSort"
]

# Límites de validación
MIN_REGISTROS = 0
MAX_REGISTROS = 1000000  # 1 millón máximo


# ── Utility Functions ─────────────────────────────────────────────────────────

def _get_output_path() -> Path:
    """
    Determina la ruta de salida para almacenar resultados.
    
    En Vercel, el sistema de archivos es de solo lectura excepto /tmp.
    En desarrollo local, usa la carpeta etl/resultados_analisis.
    
    Returns:
        Path: Ruta donde guardar resultados
        
    Example:
        >>> path = _get_output_path()
        >>> print(path)
        Path('/tmp/resultados_analisis')  # En Vercel
        # o
        Path('etl/resultados_analisis')   # En desarrollo
    """
    ruta_base = Path(__file__).resolve().parents[1]
    
    # En Vercel, /tmp es el único directorio escribible
    if os.environ.get("VERCEL"):
        logger.debug("Ejecutando en Vercel, usando /tmp para almacenamiento")
        return Path("/tmp") / "resultados_analisis"
    
    logger.debug("Ejecutando localmente, usando carpeta etl/resultados_analisis")
    return ruta_base / "etl" / "resultados_analisis"


def _validate_max_registros(max_registros: int) -> bool:
    """
    Valida el parámetro max_registros.
    
    Args:
        max_registros: Número de registros a analizar
        
    Returns:
        bool: True si el valor es válido
        
    Raises:
        ValueError: Si el valor es inválido
    """
    if max_registros < MIN_REGISTROS:
        raise ValueError(
            f"max_registros debe ser >= {MIN_REGISTROS} "
            f"(recibió: {max_registros})"
        )
    
    if max_registros > MAX_REGISTROS and max_registros != 0:
        raise ValueError(
            f"max_registros debe ser <= {MAX_REGISTROS} "
            f"(recibió: {max_registros})"
        )
    
    return True


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get(
    "/ordenamiento",
    summary="Análisis de 12 algoritmos de ordenamiento",
    response_description="Resultados de benchmarking de algoritmos"
)
def analisis_ordenamiento(
    max_registros: int = Query(
        0,
        ge=MIN_REGISTROS,
        description=(
            "Limita el dataset al número especificado de registros. "
            "0 = sin límite (usa todos los datos disponibles)."
        ),
        example=0
    ),
    incluir_dataset_ordenado: bool = Query(
        False,
        description=(
            "Si true, incluye en la respuesta el dataset ordenado completo. "
            "Puede incrementar significativamente el tamaño de la respuesta."
        ),
        example=False
    ),
) -> Dict[str, Any]:
    """
    Ejecuta análisis completo de rendimiento de 12 algoritmos de ordenamiento.
    
    Este endpoint:
    1. Carga datos históricos de la BVC desde archivos JSON
    2. Ejecuta los 12 algoritmos sobre el dataset unificado
    3. Mide tiempos de ejecución en segundos
    4. Genera ranking ascendente de algoritmos (mejores primero)
    5. Calcula TOP 15 días de mayor volumen por activo
    6. Genera gráficos PNG con resultados
    7. Guarda todos los resultados en archivos JSON
    
    Límites y Restricciones:
    - Si max_registros = 0, procesa todos los datos disponibles
    - Máximo 1,000,000 registros por consulta
    - La respuesta puede ser grande si incluir_dataset_ordenado=true
    
    Args:
        max_registros: Límite de registros a procesar (0 = todos)
        incluir_dataset_ordenado: Incluir dataset completo ordenado en respuesta
        
    Returns:
        Dict con estructura:
        {
            "status": "ok",
            "total_registros": <número>,
            "tiempos_algoritmos_asc": [
                {
                    "Metodo": <nombre>,
                    "Tamano": <registros>,
                    "Tiempo": "<segundos>",
                    "Estado": "OK" | "ERROR: ..."
                },
                ...
            ],
            "top_15_mayor_volumen_por_activo": {
                "<TICKER>": [
                    {
                        "fecha": "YYYY-MM-DD",
                        "close": <precio>,
                        "volumen": <vol>
                    },
                    ...
                ],
                ...
            },
            "rutas_archivos": {
                "dataset_ordenado": "<ruta>",
                "tiempos_asc": "<ruta>",
                "top_15": "<ruta>",
                "grafico_barras": "<ruta>"
            },
            "dataset_ordenado": [...]  # Solo si incluir_dataset_ordenado=true
        }
        
    Raises:
        HTTPException 404: Si no se encuentran datos históricos
        HTTPException 422: Si la validación de parámetros falla
        HTTPException 500: Si ocurre error durante el análisis
        
    Response Example:
        {
            "status": "ok",
            "total_registros": 5000,
            "tiempos_algoritmos_asc": [
                {
                    "Metodo": "TimSort",
                    "Tamano": 5000,
                    "Tiempo": "0.001234 seg",
                    "Estado": "OK"
                },
                ...
            ],
            "top_15_mayor_volumen_por_activo": {
                "ECOPETROL": [
                    {
                        "fecha": "2024-01-15",
                        "close": 2750.0,
                        "volumen": 50000000
                    },
                    ...
                ]
            },
            "rutas_archivos": {
                "dataset_ordenado": "/tmp/resultados_analisis/dataset_unificado_ordenado.json",
                "tiempos_asc": "/tmp/resultados_analisis/tiempos_algoritmos_asc.json",
                "top_15": "/tmp/resultados_analisis/top_15_mayor_volumen_por_activo.json",
                "grafico_barras": "/tmp/resultados_analisis/tiempos_algoritmos_barras_asc.png"
            }
        }
    """
    logger.info(
        f"Iniciando análisis de ordenamiento: "
        f"max_registros={max_registros}, "
        f"incluir_dataset_ordenado={incluir_dataset_ordenado}"
    )
    
    try:
        # Validar parámetro max_registros
        logger.debug(f"Validando parámetro max_registros={max_registros}")
        _validate_max_registros(max_registros)
        
        # Determinar rutas
        ruta_base = Path(__file__).resolve().parents[1]
        ruta_historicos = ruta_base / "etl" / "historicos"
        carpeta_salida = _get_output_path()
        
        logger.debug(f"Ruta históricos: {ruta_historicos}")
        logger.debug(f"Ruta salida: {carpeta_salida}")
        
        # Verificar que existe la ruta de históricos
        if not ruta_historicos.exists():
            logger.error(f"Carpeta de históricos no existe: {ruta_historicos}")
            raise FileNotFoundError(
                f"No se encontró la carpeta de datos históricos en {ruta_historicos}"
            )
        
        # Ejecutar análisis
        logger.info("Ejecutando análisis de rendimiento de algoritmos")
        resultado = ejecutar_analisis_ordenamiento(
            ruta_hist=ruta_historicos,
            max_registros=max_registros,
            carpeta_salida=carpeta_salida,
            generar_grafico=True,
        )
        
        logger.info(
            f"Análisis completado exitosamente: "
            f"{resultado['total_registros']} registros procesados"
        )
        
        # Construir respuesta
        response = {
            "status": "ok",
            "total_registros": resultado["total_registros"],
            "tiempos_algoritmos_asc": resultado["resultados_tiempos"],
            "top_15_mayor_volumen_por_activo": resultado["top_15_por_activo"],
            "rutas_archivos": resultado["rutas_archivos"],
        }
        
        # Incluir dataset ordenado si se solicita
        if incluir_dataset_ordenado:
            logger.debug("Incluyendo dataset orderado completo en respuesta")
            response["dataset_ordenado"] = resultado.get("dataset_ordenado")
        
        logger.debug("Respuesta construida exitosamente")
        return response
    
    except FileNotFoundError as exc:
        logger.error(f"Archivo no encontrado: {exc}")
        raise HTTPException(
            status_code=404,
            detail=f"Error: {str(exc)}"
        ) from exc
    
    except ValueError as exc:
        logger.error(f"Error de validación: {exc}")
        raise HTTPException(
            status_code=422,
            detail=f"Parámetros inválidos: {str(exc)}"
        ) from exc
    
    except Exception as exc:
        logger.error(f"Error no esperado durante análisis: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(exc)}"
        ) from exc


@router.get(
    "/info",
    summary="Información de algoritmos soportados",
    tags=["Información"]
)
def info_algoritmos() -> Dict[str, Any]:
    """
    Retorna información sobre los algoritmos soportados.
    
    Returns:
        Dict con lista de algoritmos y descripción del análisis
        
    Example:
        GET /api/analisis/info
        
        Response:
        {
            "algoritmos": [
                "TimSort",
                "Comb Sort",
                ...
            ],
            "total": 12,
            "descripcion": "Benchmarking de algoritmos de ordenamiento",
            "tipo_analisis": "Performance Measurement"
        }
    """
    logger.debug("Retornando información de algoritmos")
    return {
        "algoritmos": ALGORITMOS_SOPORTADOS,
        "total": len(ALGORITMOS_SOPORTADOS),
        "descripcion": "Benchmarking comparativo de 12 algoritmos de ordenamiento",
        "tipo_analisis": "Performance Measurement",
        "metrica": "Tiempo de ejecución en segundos",
        "status": "ok"
    }

