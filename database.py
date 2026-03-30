"""
database.py
-----------
MongoDB connection and database management for NexVest application.

Este módulo maneja:
  - Carga de variables de entorno (MONGO_URI y MONGO_DB_NAME)
  - Creación y mantenimiento de conexión a MongoDB Atlas
  - Provisión de dependencias para FastAPI
  - Validación de configuración

Environment Variables:
    MONGO_URI (required): MongoDB Atlas connection string
        Format: mongodb+srv://username:password@host/
    MONGO_DB_NAME (optional): Database name (default: nexvest)

Singleton Pattern:
    Utiliza un singleton a nivel de módulo para reutilizar la conexión
    en invocaciones warm en Vercel. Reduce latencia y consumo de recursos.

Example:
    from database import get_db
    from fastapi import Depends
    
    @app.get("/data")
    def read_data(db: Database = Depends(get_db)):
        collection = db["historico_ecopetrol"]
        records = collection.find_one()
        return records
"""

import logging
import os
from typing import Optional, Generator

from dotenv import load_dotenv
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo.database import Database
from pymongo.errors import ServerSelectionTimeoutError, ConfigurationError

# ── Logger Setup ──────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# ── Environment Configuration ─────────────────────────────────────────────────
# Carga variables de entorno desde .env
load_dotenv()

MONGO_URI: str = os.getenv("MONGO_URI", "")
if not MONGO_URI:
    logger.error(
        "MONGO_URI no configurada. Por favor add it a tu archivo .env. "
        "Ver .env.example para referencia."
    )
    raise EnvironmentError(
        "MONGO_URI is not set. Please add it to your .env file.\n"
        "See .env.example for reference.\n"
        "Example: mongodb+srv://user:password@cluster.mongodb.net/"
    )

MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "nexvest")
logger.info(f"Base de datos configurada: {MONGO_DB_NAME}")

# ── Singleton Client ──────────────────────────────────────────────────────────
# Module-level singleton — se reutiliza en invocaciones warm en Vercel
# Reduce latencia y overhead de conexión
_client: Optional[MongoClient] = None

# Configuración de conexión
MONGO_CONFIG = {
    "server_api": ServerApi("1"),
    "tls": True,
    "tlsAllowInvalidCertificates": False,
    "serverSelectionTimeoutMS": 10000,
    "connectTimeoutMS": 10000,
    "socketTimeoutMS": 20000,
    "maxPoolSize": 10,
    "minPoolSize": 5,
}


def get_client() -> MongoClient:
    """
    Obtiene el cliente singleton de MongoDB.
    
    La primera invocación crea el cliente con retry logic.
    Las subsecuentes reutilizan el cliente existente.
    
    Returns:
        MongoClient: Cliente conectado a MongoDB Atlas
        
    Raises:
        ServerSelectionTimeoutError: Si no puede conectarse a MongoDB
        ConfigurationError: Si la configuración es inválida
        
    Example:
        client = get_client()
        db = client["nexvest"]
        collection = db["historico_ecopetrol"]
    """
    global _client
    
    if _client is not None:
        logger.debug("Reutilizando cliente MongoDB existente")
        return _client
    
    logger.info("Creando nueva conexión a MongoDB Atlas")
    
    try:
        _client = MongoClient(MONGO_URI, **MONGO_CONFIG)
        
        # Valida la conexión
        _client.admin.command("ping")
        logger.info("Conexión a MongoDB exitosa ✓")
        
        return _client
        
    except ServerSelectionTimeoutError as e:
        logger.error(f"Timeout conectando a MongoDB: {e}")
        raise
    except ConfigurationError as e:
        logger.error(f"Error de configuración MongoDB: {e}")
        raise
    except Exception as e:
        logger.error(f"Error inesperado conectando a MongoDB: {e}")
        raise


def get_db() -> Generator[Database, None, None]:
    """
    FastAPI dependency que proporciona acceso a la base de datos.
    
    Se usa como parámetro con `Depends()` en endpoints FastAPI.
    Utiliza context manager para asegurar limpieza de recursos.
    
    Yields:
        Database: La base de datos MongoDB actual
        
    Example:
        from fastapi import Depends
        
        @app.get("/data")
        def endpoint(db: Database = Depends(get_db)):
            collection = db["historico_ecopetrol"]
            return collection.find_one()
    """
    try:
        client = get_client()
        db = client[MONGO_DB_NAME]
        logger.debug(f"Proporcionando acceso a base de datos: {MONGO_DB_NAME}")
        yield db
    except Exception as e:
        logger.error(f"Error al acceder a la base de datos: {e}")
        raise
    finally:
        logger.debug("Liberando recursos de base de datos")


# ── Utility Functions ─────────────────────────────────────────────────────────

def close_connection() -> None:
    """
    Cierra la conexión a MongoDB.
    
    Se debe llamar al shutdown de la aplicación o cuando se necesite
    liberar recursos explícitamente.
    
    Example:
        @app.on_event("shutdown")
        async def shutdown_event():
            close_connection()
    """
    global _client
    if _client is not None:
        logger.info("Cerrando conexión a MongoDB")
        _client.close()
        _client = None
    else:
        logger.debug("No hay conexión activa para cerrar")


def is_connected() -> bool:
    """
    Verifica si hay una conexión activa a MongoDB.
    
    Returns:
        bool: True si hay conexión, False en caso contrario
        
    Example:
        if is_connected():
            logger.info("Conexión activa a MongoDB")
        else:
            logger.warning("No hay conexión a MongoDB")
    """
    try:
        if _client is not None:
            _client.admin.command("ping")
            return True
    except Exception as e:
        logger.warning(f"Verificación de conexión falló: {e}")
    return False

