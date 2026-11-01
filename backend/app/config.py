"""Runtime environment helpers (single place FORGE_ENV is read)."""
import os


def forge_env() -> str:
    return os.environ.get("FORGE_ENV", "development").strip().lower()


def is_production() -> bool:
    return forge_env() == "production"
