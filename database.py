"""
database.py
-----------
MongoDB connection for NexVest.
Uses python-dotenv to read MONGO_URI and MONGO_DB_NAME from .env
"""

import os

from dotenv import load_dotenv
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

load_dotenv()

MONGO_URI: str = os.getenv("MONGO_URI", "")
if not MONGO_URI:
    raise EnvironmentError(
        "MONGO_URI is not set. Please add it to your .env file.\n"
        "See .env.example for reference."
    )

MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "nexvest")

# Module-level singleton — reused across warm invocations in Vercel
_client = None  # type: MongoClient


def get_client() -> MongoClient:
    """Return a module-level MongoClient, creating it once per cold start."""
    global _client
    if _client is None:
        _client = MongoClient(
            MONGO_URI,
            server_api=ServerApi("1"),
            tls=True,
            tlsAllowInvalidCertificates=False,
            serverSelectionTimeoutMS=10000,
            connectTimeoutMS=10000,
            socketTimeoutMS=20000,
        )
    return _client


def get_db():
    """FastAPI dependency — yields the nexvest database."""
    client = get_client()
    yield client[MONGO_DB_NAME]
