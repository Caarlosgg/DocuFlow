"""
DocuFlow — Backend FastAPI
===========================
Servidor principal que expone la API REST y sirve el frontend estático.

Uso
---
    uvicorn backend.main:app --reload
    # o bien
    python -m backend.main
"""

from __future__ import annotations

import logging
import shutil
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from core.config import settings
from backend.schemas import (
    ChatRequest, ChatResponse, HealthResponse,
    UploadResponse, ReindexResponse, DeleteResponse,
)
from backend.rag_service import RAGService

# ── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("docuflow.api")

# ── Servicio RAG (singleton) ─────────────────────────────────────────
rag = RAGService()


# =====================================================================
#  LIFESPAN (inicio / parada)
# =====================================================================

@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Inicializa y libera recursos al arrancar / detener el servidor."""
    log.info("=" * 50)
    log.info("  DocuFlow API — Arrancando")
    log.info("=" * 50)

    try:
        rag.start()
    except Exception as exc:
        log.error("Error al inicializar RAGService: %s", exc)
        log.error("El servidor arrancará sin funcionalidad RAG.")
        log.error("Verifica: Qdrant, GROQ_API_KEY, modelo de embeddings.")

    yield

    rag.stop()
    log.info("DocuFlow API — Detenido")


# =====================================================================
#  APLICACIÓN FASTAPI
# =====================================================================

app = FastAPI(
    title="DocuFlow API",
    description="API REST del sistema RAG empresarial DocuFlow.",
    version="1.0.0",
    docs_url="/docs",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Archivos estáticos del frontend ─────────────────────────────────
_frontend_dir = settings.FRONTEND_DIR
if _frontend_dir.exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(_frontend_dir)),
        name="static",
    )
    log.info("Frontend estático montado desde %s", _frontend_dir)


# =====================================================================
#  MANEJADOR GLOBAL DE EXCEPCIONES
# =====================================================================

@app.exception_handler(Exception)
async def global_exception_handler(_req: Request, exc: Exception):
    log.error("Error no controlado: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor. Revisa los logs."},
    )


# =====================================================================
#  ENDPOINTS
# =====================================================================

# ── Frontend ─────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Sirve la página principal del frontend."""
    index = _frontend_dir / "index.html"
    if index.exists():
        return FileResponse(str(index), media_type="text/html")
    return JSONResponse(
        content={"message": "DocuFlow API activa. Frontend no encontrado."},
    )


# ── Health-check ─────────────────────────────────────────────────────

@app.get("/api/health", response_model=HealthResponse, tags=["Sistema"])
async def health():
    """Estado del servicio y sus dependencias."""
    try:
        count = rag.collection_count() if rag.is_ready else 0
        return HealthResponse(
            status="healthy" if rag.is_ready else "degraded",
            qdrant="connected" if rag.is_ready else "disconnected",
            collection=settings.COLLECTION_NAME,
            documents_count=count,
            llm_model=settings.LLM_MODEL,
            embedding_model=settings.EMBEDDING_MODEL,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


# ── Chat RAG ─────────────────────────────────────────────────────────

@app.post("/api/chat", response_model=ChatResponse, tags=["RAG"])
async def chat(request: ChatRequest):
    """
    Endpoint principal del sistema RAG.

    1. Genera embedding de la consulta.
    2. Busca los *k* documentos más similares en Qdrant.
    3. Construye un prompt contextual.
    4. Genera respuesta con ChatGroq.
    5. Retorna respuesta + fuentes.
    """
    if not rag.is_ready:
        raise HTTPException(
            status_code=503,
            detail=(
                "El servicio RAG no está inicializado. "
                "Verifica que Qdrant esté activo y GROQ_API_KEY configurada."
            ),
        )

    try:
        return await rag.query(
            text=request.query,
            k=request.k,
            files_filter=request.files_filter,
        )
    except Exception as exc:
        log.error("Error en /api/chat: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


# ── Subida de archivos ───────────────────────────────────────

ALLOWED_EXTENSIONS = {".pdf", ".csv"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


@app.post("/api/upload", response_model=UploadResponse, tags=["Archivos"])
async def upload_files(files: list[UploadFile] = File(...)):
    """
    Sube uno o más archivos PDF/CSV al directorio de datos.
    Los archivos estarán disponibles para indexar con /api/reindex.
    """
    saved: list[str] = []
    errors: list[str] = []

    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)

    for f in files:
        # Validar extensión
        ext = Path(f.filename or "").suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            errors.append(f"{f.filename}: tipo no soportado (solo PDF/CSV)")
            continue

        # Validar tamaño
        content = await f.read()
        if len(content) > MAX_FILE_SIZE:
            errors.append(f"{f.filename}: excede 50 MB")
            continue

        # Guardar archivo
        dest = settings.DATA_DIR / f.filename
        try:
            dest.write_bytes(content)
            saved.append(f.filename)
            log.info("Archivo subido: %s (%d bytes)", f.filename, len(content))
        except Exception as exc:
            errors.append(f"{f.filename}: {exc}")

    if not saved:
        raise HTTPException(
            status_code=400,
            detail="No se guardó ningún archivo. " + "; ".join(errors),
        )

    return UploadResponse(
        message=f"{len(saved)} archivo(s) subido(s) correctamente.",
        files_saved=saved,
        errors=errors,
    )


@app.get("/api/files", tags=["Archivos"])
async def list_files():
    """Lista los archivos disponibles en el directorio de datos."""
    if not settings.DATA_DIR.exists():
        return {"files": []}

    files = []
    for f in sorted(settings.DATA_DIR.rglob("*")):
        if f.suffix.lower() in ALLOWED_EXTENSIONS and not f.name.startswith("."):
            files.append({
                "name": f.name,
                "type": f.suffix.lower().lstrip("."),
                "size_kb": round(f.stat().st_size / 1024, 1),
            })

    return {"files": files}


@app.delete("/api/files/{filename}", response_model=DeleteResponse, tags=["Archivos"])
async def delete_file(filename: str):
    """
    Elimina un archivo del directorio de datos.
    Después de eliminar, se recomienda reindexar.
    """
    filepath = settings.DATA_DIR / filename
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(status_code=404, detail=f"Archivo '{filename}' no encontrado.")

    # Seguridad: verificar que está dentro de DATA_DIR
    try:
        filepath.resolve().relative_to(settings.DATA_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Ruta no permitida.")

    filepath.unlink()
    log.info("Archivo eliminado: %s", filename)
    return DeleteResponse(message=f"Archivo '{filename}' eliminado.", filename=filename)


@app.post("/api/reindex", response_model=ReindexResponse, tags=["Archivos"])
async def reindex():
    """
    Re-ejecuta el pipeline de ingesta: escanea data/, genera
    embeddings y reemplaza la colección en Qdrant.
    """
    import asyncio
    from core.ingest import scan_directory, index_in_qdrant

    try:
        docs = await asyncio.to_thread(scan_directory, settings.DATA_DIR)
        if not docs:
            return ReindexResponse(
                message="No se encontraron documentos PDF/CSV en el directorio.",
                documents_indexed=0,
            )

        await asyncio.to_thread(index_in_qdrant, docs, reset=True)

        # Reconectar RAG para reflejar la nueva colección
        if rag.is_ready:
            rag.stop()
            rag.start()

        return ReindexResponse(
            message=f"Indexación completada: {len(docs)} documentos procesados.",
            documents_indexed=len(docs),
        )
    except Exception as exc:
        log.error("Error en reindexación: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


# =====================================================================
#  EJECUCIÓN DIRECTA
# =====================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=True,
        log_level="info",
    )
