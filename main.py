"""
main.py
-------
NexVest FastAPI application entry point.

Este módulo contiene la configuración principal de la aplicación FastAPI,
incluyendo middleware, routers y endpoints de salud.

Authors:
    - NexVest development team

Version:
    0.1.0

Environment Variables:
    - MONGO_URI: Conexión a MongoDB Atlas (requerido)
    - MONGO_DB_NAME: Nombre de la base de datos (default: nexvest)
    - VERCEL: Detecta si se ejecuta en Vercel (afecta rutas de almacenamiento)

Example:
    Para iniciar el servidor en desarrollo:
    $ uvicorn main:app --reload
    
    Accede a la documentación en http://localhost:8000/docs
"""

import logging
from typing import Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from routers import analisis, historicos

# ── Logger ────────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# ── FastAPI Application ───────────────────────────────────────────────────────
app = FastAPI(
    title="NexVest API",
    description=(
        "API de análisis financiero avanzado.\n\n"
        "Proporciona acceso a datos históricos de la Bolsa de Valores de Colombia (BVC) "
        "e implementa algoritmos de análisis de rendimiento."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

logger.info("Iniciando configuración de NexVest API")

# ── CORS Middleware ───────────────────────────────────────────────────────────
# Permite requests desde cualquier origen (ajustable en producción)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

logger.debug("CORS middleware configurado")

# ── Include Routers ───────────────────────────────────────────────────────────
# Registra los routers de módulos del negocio
app.include_router(historicos.router, prefix="/api")
app.include_router(analisis.router, prefix="/api")

logger.debug("Routers registrados: /historicos, /analisis")


# ── Health Check Endpoints ────────────────────────────────────────────────────

@app.get(
    "/",
    tags=["Health"],
    summary="Estado de la API",
    response_description="Estado actual del servidor"
)
def root() -> Dict[str, Any]:
    """
    Endpoint raíz que verifica el estado general de la API.
    
    Returns:
        Dict con información de estado básica.
        
    Example:
        GET /
        
        Response:
        {
            "status": "ok",
            "message": "NexVest API corriendo",
            "version": "0.1.0"
        }
    """
    logger.debug("Health check - root endpoint")
    return {
        "status": "ok",
        "message": "NexVest API corriendo correctamente",
        "version": "0.1.0",
        "documentation": "/docs"
    }


@app.get(
    "/health",
    tags=["Health"],
    summary="Health check detallado"
)
def health_check() -> Dict[str, Any]:
    """
    Realiza un health check más detallado de la API.
    
    Verifica:
        - Estado del servidor
        - Disponibilidad de routers
        - Configuración de CORS
    
    Returns:
        Dict con información detallada del estado.
    """
    logger.debug("Detailed health check")
    return {
        "status": "healthy",
        "service": "NexVest API",
        "version": "0.1.0",
        "endpoints": {
            "historicos": "/api/historicos",
            "analisis": "/api/analisis"
        },
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi": "/openapi.json"
        }
    }


# ── Error Handlers ────────────────────────────────────────────────────────────

@app.exception_handler(Exception)
def global_exception_handler(request, exc: Exception) -> JSONResponse:
    """
    Maneja excepciones no capturadas en la aplicación.
    
    Args:
        request: Request object de FastAPI
        exc: Excepción no manejada
        
    Returns:
        JSONResponse con información del error
    """
    logger.error(f"Excepción no manejada: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Error interno del servidor",
            "detail": str(exc)
        }
    )
