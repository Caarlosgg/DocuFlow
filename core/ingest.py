"""
DocuFlow — Pipeline ETL de Ingesta
====================================
Escanea recursivamente ``data/``, procesa PDFs y CSVs,
genera embeddings con HuggingFace (CPU) e indexa en Qdrant.

Uso
---
    python -m core.ingest              # indexar todo
    python -m core.ingest --reset      # borrar colección y reindexar
"""

from __future__ import annotations

import re
import sys
import logging
import argparse
from pathlib import Path

import polars as pl
from pypdf import PdfReader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from core.config import settings

# ── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("docuflow.ingest")


# =====================================================================
#  UTILIDADES
# =====================================================================

def _clean(text: str) -> str:
    """Normaliza espacios y elimina caracteres de control."""
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# =====================================================================
#  EXTRACTORES
# =====================================================================

def extract_pdf(path: Path) -> list[Document]:
    """
    Extrae texto de un PDF, lo limpia y divide en chunks semánticos.

    Retorna lista vacía si el archivo no tiene texto extraíble.
    """
    log.info("[PDF] %s", path.name)
    try:
        reader = PdfReader(str(path))
        pages: list[str] = []
        for i, page in enumerate(reader.pages, 1):
            txt = page.extract_text()
            if txt and txt.strip():
                pages.append(_clean(txt))
            else:
                log.debug("  Página %d: sin texto", i)

        if not pages:
            log.warning("  Sin texto extraíble — omitido")
            return []

        full_text = "\n\n".join(pages)

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", ", ", " ", ""],
            length_function=len,
        )
        chunks = splitter.split_text(full_text)

        docs = [
            Document(
                page_content=chunk,
                metadata={
                    "source": path.name,
                    "type": "pdf",
                    "chunk_index": idx,
                    "total_chunks": len(chunks),
                },
            )
            for idx, chunk in enumerate(chunks)
        ]
        log.info("  -> %d chunks", len(docs))
        return docs

    except Exception as exc:
        log.error("  ERROR: %s", exc)
        return []


def extract_csv(path: Path) -> list[Document]:
    """
    Lee un CSV con Polars, rellena nulos y convierte cada fila
    en un Document con formato enriquecido ``columna: valor``.
    """
    log.info("[CSV] %s", path.name)
    try:
        df = pl.read_csv(str(path), infer_schema_length=10_000, ignore_errors=True)
        log.info("  -> %d filas x %d columnas", df.height, df.width)

        if df.is_empty():
            log.warning("  CSV vacío — omitido")
            return []

        # ── Llenar nulos por tipo ────────────────────────────────────
        fill_exprs = []
        for col_name in df.columns:
            dtype = df[col_name].dtype
            if dtype == pl.Utf8 or dtype == pl.Categorical:
                fill_exprs.append(pl.col(col_name).fill_null("N/A"))
            elif dtype.is_numeric():
                fill_exprs.append(pl.col(col_name).fill_null(0))
            elif dtype == pl.Boolean:
                fill_exprs.append(pl.col(col_name).fill_null(False))
            else:
                fill_exprs.append(pl.col(col_name).cast(pl.Utf8).fill_null("N/A"))
        df = df.with_columns(fill_exprs)

        # ── Convertir filas a texto enriquecido ──────────────────────
        columns = df.columns
        docs: list[Document] = []
        for row_idx in range(df.height):
            row = df.row(row_idx)
            rich_text = " | ".join(f"{c}: {v}" for c, v in zip(columns, row))
            docs.append(
                Document(
                    page_content=_clean(rich_text),
                    metadata={
                        "source": path.name,
                        "type": "csv",
                        "row_index": row_idx,
                        "total_rows": df.height,
                    },
                )
            )

        log.info("  -> %d documentos", len(docs))
        return docs

    except Exception as exc:
        log.error("  ERROR: %s", exc)
        return []


# =====================================================================
#  ESCANEO DE DIRECTORIO
# =====================================================================

def scan_directory(data_dir: Path) -> list[Document]:
    """Busca recursivamente .pdf y .csv en ``data_dir``."""
    if not data_dir.exists():
        log.error("Directorio de datos no encontrado: %s", data_dir)
        sys.exit(1)

    files = sorted(
        f for f in data_dir.rglob("*")
        if f.suffix.lower() in (".pdf", ".csv") and not f.name.startswith(".")
    )

    if not files:
        log.warning("No se encontraron archivos PDF/CSV en %s", data_dir)
        return []

    log.info("Archivos encontrados: %d", len(files))

    documents: list[Document] = []
    for f in files:
        match f.suffix.lower():
            case ".pdf":
                documents.extend(extract_pdf(f))
            case ".csv":
                documents.extend(extract_csv(f))

    return documents


# =====================================================================
#  INDEXACIÓN EN QDRANT
# =====================================================================

def index_in_qdrant(documents: list[Document], *, reset: bool = False) -> None:
    """
    Genera embeddings y los sube a Qdrant por lotes.

    Parameters
    ----------
    documents : lista de Documents para indexar.
    reset     : si True, borra la colección antes de indexar.
    """
    if not documents:
        log.warning("Sin documentos para indexar.")
        return

    # ── Modelo de embeddings ─────────────────────────────────────────
    log.info("Cargando modelo de embeddings: %s", settings.EMBEDDING_MODEL)
    embed_model = HuggingFaceEmbeddings(
        model_name=settings.EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True, "batch_size": 64},
    )

    # ── Conexión a Qdrant ────────────────────────────────────────────
    try:
        if settings.QDRANT_MODE == "local":
            log.info("Conectando a Qdrant (modo local: %s)", settings.QDRANT_LOCAL_PATH)
            settings.QDRANT_LOCAL_PATH.mkdir(parents=True, exist_ok=True)
            client = QdrantClient(path=str(settings.QDRANT_LOCAL_PATH))
        else:
            log.info("Conectando a Qdrant %s:%d ...", settings.QDRANT_HOST, settings.QDRANT_PORT)
            client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT, timeout=30)
        client.get_collections()
        log.info("  Qdrant OK")
    except Exception as exc:
        log.error("No se pudo conectar a Qdrant: %s", exc)
        sys.exit(1)

    # ── Gestión de colección ─────────────────────────────────────────
    existing = [c.name for c in client.get_collections().collections]
    if settings.COLLECTION_NAME in existing:
        if reset:
            log.info("  Eliminando colección existente '%s'...", settings.COLLECTION_NAME)
            client.delete_collection(settings.COLLECTION_NAME)
        else:
            log.info("  Colección '%s' ya existe — añadiendo documentos", settings.COLLECTION_NAME)

    if settings.COLLECTION_NAME not in [c.name for c in client.get_collections().collections]:
        client.create_collection(
            collection_name=settings.COLLECTION_NAME,
            vectors_config=VectorParams(
                size=settings.EMBEDDING_DIM,
                distance=Distance.COSINE,
            ),
        )
        log.info("  Colección '%s' creada", settings.COLLECTION_NAME)

    # ── Generar embeddings por lotes ─────────────────────────────────
    BATCH = 128
    texts = [d.page_content for d in documents]
    total = len(texts)
    points: list[PointStruct] = []

    # Obtener el offset de ID si la colección ya tiene puntos
    try:
        collection_info = client.get_collection(settings.COLLECTION_NAME)
        id_offset = collection_info.points_count or 0
    except Exception:
        id_offset = 0

    log.info("Generando embeddings (%d documentos)...", total)
    for start in range(0, total, BATCH):
        end = min(start + BATCH, total)
        batch_texts = texts[start:end]
        batch_docs = documents[start:end]

        try:
            vectors = embed_model.embed_documents(batch_texts)
            for i, (vec, doc) in enumerate(zip(vectors, batch_docs)):
                points.append(
                    PointStruct(
                        id=id_offset + start + i,
                        vector=vec,
                        payload={
                            "page_content": doc.page_content,
                            "source": doc.metadata.get("source", "unknown"),
                            "type": doc.metadata.get("type", "unknown"),
                            "chunk_index": doc.metadata.get(
                                "chunk_index",
                                doc.metadata.get("row_index", 0),
                            ),
                        },
                    )
                )
            log.info("  Embeddings %d-%d / %d", start + 1, end, total)
        except Exception as exc:
            log.error("  Error en lote %d: %s", start, exc)
            continue

    # ── Subir a Qdrant ───────────────────────────────────────────────
    if not points:
        log.error("No se generaron puntos — cancelando")
        return

    UPLOAD_BATCH = 256
    for i in range(0, len(points), UPLOAD_BATCH):
        batch = points[i : i + UPLOAD_BATCH]
        try:
            client.upsert(collection_name=settings.COLLECTION_NAME, points=batch)
            log.info("  Subidos %d / %d puntos", min(i + UPLOAD_BATCH, len(points)), len(points))
        except Exception as exc:
            log.error("  Error subiendo lote %d: %s", i, exc)

    log.info("Indexación completada: %d documentos en '%s'", len(points), settings.COLLECTION_NAME)


# =====================================================================
#  PUNTO DE ENTRADA
# =====================================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="DocuFlow — Pipeline de Ingesta")
    parser.add_argument("--reset", action="store_true", help="Borrar colección antes de indexar")
    parser.add_argument("--data-dir", type=str, default=None, help="Directorio de datos alternativo")
    args = parser.parse_args()

    data_dir = Path(args.data_dir) if args.data_dir else settings.DATA_DIR

    log.info("=" * 55)
    log.info("  DocuFlow — Pipeline de Ingesta")
    log.info("  Directorio: %s", data_dir)
    log.info("=" * 55)

    documents = scan_directory(data_dir)
    log.info("Total documentos extraídos: %d", len(documents))

    index_in_qdrant(documents, reset=args.reset)

    log.info("=" * 55)
    log.info("  Pipeline finalizado")
    log.info("=" * 55)


if __name__ == "__main__":
    main()
