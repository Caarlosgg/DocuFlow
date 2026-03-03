"""
DocuFlow — Configuración Centralizada
=======================================
Único punto de verdad para todas las constantes y variables
de entorno del proyecto. Importar siempre desde aquí.

    from core.config import settings
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Cargar .env desde la raíz del proyecto
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


@dataclass(frozen=True, slots=True)
class Settings:
    """Configuración inmutable de la aplicación."""

    # ── Rutas ────────────────────────────────────────────────────────
    PROJECT_ROOT: Path = _PROJECT_ROOT
    DATA_DIR: Path = _PROJECT_ROOT / "data"
    FRONTEND_DIR: Path = _PROJECT_ROOT / "frontend"

    # ── Groq LLM ─────────────────────────────────────────────────────
    GROQ_API_KEY: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    LLM_MODEL: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "llama-3.3-70b-versatile"))
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 2048

    # ── Embeddings (local, CPU) ──────────────────────────────────────
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384

    # ── Qdrant ───────────────────────────────────────────────────────
    # Modo: "local" (disco, sin Docker) | "remote" (Docker/servidor)
    QDRANT_MODE: str = field(default_factory=lambda: os.getenv("QDRANT_MODE", "local"))
    QDRANT_LOCAL_PATH: Path = _PROJECT_ROOT / "qdrant_data"
    QDRANT_HOST: str = field(default_factory=lambda: os.getenv("QDRANT_HOST", "localhost"))
    QDRANT_PORT: int = field(default_factory=lambda: int(os.getenv("QDRANT_PORT", "6333")))
    COLLECTION_NAME: str = field(default_factory=lambda: os.getenv("COLLECTION_NAME", "docuflow_core"))

    # ── Text Splitting ───────────────────────────────────────────────
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 150

    # ── Backend ──────────────────────────────────────────────────────
    BACKEND_HOST: str = field(default_factory=lambda: os.getenv("BACKEND_HOST", "0.0.0.0"))
    BACKEND_PORT: int = field(default_factory=lambda: int(os.getenv("BACKEND_PORT", "8000")))

    def validate(self) -> None:
        """Valida que la configuración crítica esté presente."""
        errors: list[str] = []
        if not self.GROQ_API_KEY:
            errors.append("GROQ_API_KEY no configurada. Añádela en el archivo .env")
        if not self.DATA_DIR.exists():
            errors.append(f"Directorio de datos no encontrado: {self.DATA_DIR}")
        if errors:
            raise EnvironmentError(
                "Errores de configuración:\n  • " + "\n  • ".join(errors)
            )


# Singleton global
settings = Settings()
