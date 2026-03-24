"""
routers/analisis.py
-------------------
Endpoints para ejecutar analisis de ordenamiento sobre historicos.
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from algorithms.desempeno import ejecutar_analisis_ordenamiento

router = APIRouter(prefix="/analisis", tags=["Analisis"])


@router.get("/ordenamiento", summary="Analisis de 12 algoritmos de ordenamiento")
def analisis_ordenamiento(
    max_registros: int = Query(
        0, ge=0, description="Limita el dataset (0 = sin limite)."
    ),
    incluir_dataset_ordenado: bool = Query(
        False,
        description="Si true, incluye en la respuesta el dataset ordenado completo.",
    ),
):
    """
    Ejecuta el analisis completo:
    - Ordenamiento ascendente del dataset unificado por fecha y close.
    - Ranking ascendente de tiempos de los 12 algoritmos.
    - Top 15 dias de mayor volumen por activo (ordenados ascendente).

    Tambien guarda los archivos de salida en etl/resultados_analisis.
    """
    ruta_base = Path(__file__).resolve().parents[1]
    ruta_historicos = ruta_base / "etl" / "historicos"
    carpeta_salida = ruta_base / "etl" / "resultados_analisis"

    try:
        resultado = ejecutar_analisis_ordenamiento(
            ruta_historicos=ruta_historicos,
            max_registros=max_registros,
            carpeta_salida=carpeta_salida,
            generar_grafico=True,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Error ejecutando analisis: {exc}") from exc

    response = {
        "status": "ok",
        "total_registros": resultado["total_registros"],
        "tiempos_algoritmos_asc": resultado["resultados_tiempos"],
        "top_15_mayor_volumen_por_activo": resultado["top_15_por_activo"],
        "rutas_archivos": resultado["rutas_archivos"],
    }

    if incluir_dataset_ordenado:
        response["dataset_ordenado"] = resultado.get("dataset_ordenado")

    return response
