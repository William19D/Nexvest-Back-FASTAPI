"""
routers package
===============

Módulo que contiene todos los routers (endpoints) de la aplicación FastAPI.

Estructura:
    - historicos: Endpoints para consultar datos históricos de la BVC
    - analisis: Endpoints para análisis de rendimiento de algoritmos

Routers Incluidos:
    1. historicos.py
        - GET /historicos/mnemonics - Lista de acciones disponibles
        - GET /historicos/{mnemonic} - Datos históricos con filtros
        - GET /historicos/{mnemonic}/{date} - Dato de fecha específica
    
    2. analisis.py
        - GET /analisis/ordenamiento - Benchmarking de 12 algoritmos
        - GET /analisis/info - Información de algoritmos soportados

Uso:
    Los routers se registran en main.py con:
    
    from routers import analisis, historicos
    
    app.include_router(historicos.router, prefix="/api")
    app.include_router(analisis.router, prefix="/api")
    
Patrones Comunes:
    - Todas las funciones usan type hints completos
    - Logging detallado en cada operación
    - Error handling robusto con HTTPException
    - Documentación automática con Swagger (/docs)
    - Validación de parámetros con Pydantic y Query
    
Convenciones:
    - Funciones privadas inician con underscore (_)
    - Routers usan prefix="/ruta" para organización
    - Tags para agrupar endpoints en documentación
    - Summary y description para cada endpoint
    - Response examples en docstrings

Author:
    NexVest Development Team

Version:
    1.0.0
"""

# Importación explícita de routers para autocompletado
from . import analisis, historicos

__all__ = ["analisis", "historicos"]

__version__ = "1.0.0"
__author__ = "NexVest Development Team"
__description__ = "Routers de la API NexVest para acceso a datos históricos y análisis"
