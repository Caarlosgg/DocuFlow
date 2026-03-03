"""
DocuFlow — Esquemas Pydantic
==============================
Modelos de entrada/salida para la API REST.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Payload de entrada para el endpoint ``/api/chat``."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Pregunta del usuario sobre los documentos corporativos.",
        examples=["¿Cuáles fueron los ingresos del Q3?"],
    )
    k: int = Field(
        default=4,
        ge=1,
        le=20,
        description="Número de documentos similares a recuperar.",
    )
    files_filter: list[str] | None = Field(
        default=None,
        description="Lista de nombres de archivo a consultar. Si es None o vacía, se busca en todos.",
    )


class SourceInfo(BaseModel):
    """Información de una fuente utilizada en la respuesta."""

    filename: str
    doc_type: str
    score: float
    snippet: str = ""


class ChatResponse(BaseModel):
    """Payload de salida del endpoint ``/api/chat``."""

    answer: str = Field(description="Respuesta generada por el LLM.")
    sources: list[str] = Field(description="Nombres de archivos fuente.")
    source_details: list[SourceInfo] = Field(
        default_factory=list,
        description="Detalles extendidos de cada fuente.",
    )


class HealthResponse(BaseModel):
    """Respuesta del endpoint ``/api/health``."""

    status: str
    qdrant: str
    collection: str
    documents_count: int
    llm_model: str
    embedding_model: str


class DeleteResponse(BaseModel):
    """Respuesta del endpoint ``DELETE /api/files/{filename}``."""

    message: str
    filename: str


class UploadResponse(BaseModel):
    """Respuesta del endpoint ``/api/upload``."""

    message: str
    files_saved: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class ReindexResponse(BaseModel):
    """Respuesta del endpoint ``/api/reindex``."""

    message: str
    documents_indexed: int = 0
