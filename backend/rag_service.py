"""
DocuFlow — Servicio RAG
========================
Lógica de negocio desacoplada: búsqueda vectorial + generación LLM.
El servicio se inicializa una vez al arrancar el backend y se reutiliza
en cada petición para evitar recargar modelos.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchAny, ScoredPoint

from core.config import settings
from backend.schemas import ChatResponse, SourceInfo

log = logging.getLogger("docuflow.rag")

# ── Prompt RAG ───────────────────────────────────────────────────────

_SYSTEM = """\
Eres DocuFlow, un asistente empresarial inteligente de alta precisión.
Tu ÚNICA fuente de información son los documentos corporativos que aparecen
en la sección CONTEXTO.

REGLAS:
1. Basa tu respuesta EXCLUSIVAMENTE en el contexto proporcionado.
2. Si el contexto no contiene información suficiente, dilo de forma clara
   y NO inventes datos.
3. Cuando cites información, indica de qué fuente proviene.
4. Sé conciso, profesional y directo.
5. Responde en el mismo idioma en que se formula la pregunta.
6. Usa formato Markdown cuando mejore la legibilidad (listas, negritas, etc.).
"""

_HUMAN = """\
CONTEXTO (fragmentos de documentos corporativos):
---
{context}
---

PREGUNTA:
{query}
"""

_prompt = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM),
    ("human", _HUMAN),
])


# =====================================================================
#  SERVICIO
# =====================================================================

@dataclass
class RAGService:
    """
    Encapsula la cadena RAG completa:
    query → embedding → búsqueda vectorial → prompt → LLM → respuesta.
    """

    _qdrant: QdrantClient = field(repr=False, default=None)
    _embeddings: HuggingFaceEmbeddings = field(repr=False, default=None)
    _llm: ChatGroq = field(repr=False, default=None)
    _ready: bool = False

    # ── Ciclo de vida ────────────────────────────────────────────────

    def start(self) -> None:
        """Carga modelos y conecta a Qdrant. Llamar una vez al arrancar."""
        log.info("Inicializando RAGService...")

        # Embeddings (local, CPU)
        self._embeddings = HuggingFaceEmbeddings(
            model_name=settings.EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        log.info("  Embeddings OK (%s)", settings.EMBEDDING_MODEL)

        # Qdrant
        if settings.QDRANT_MODE == "local":
            settings.QDRANT_LOCAL_PATH.mkdir(parents=True, exist_ok=True)
            self._qdrant = QdrantClient(path=str(settings.QDRANT_LOCAL_PATH))
            log.info("  Qdrant OK (modo local: %s)", settings.QDRANT_LOCAL_PATH)
        else:
            self._qdrant = QdrantClient(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT,
                timeout=30,
            )
            self._qdrant.get_collections()  # Health-check
            log.info("  Qdrant OK (%s:%d)", settings.QDRANT_HOST, settings.QDRANT_PORT)

        # LLM
        self._llm = ChatGroq(
            model=settings.LLM_MODEL,
            api_key=settings.GROQ_API_KEY,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )
        log.info("  LLM OK (%s)", settings.LLM_MODEL)

        self._ready = True
        log.info("RAGService listo.")

    def stop(self) -> None:
        """Libera recursos."""
        if self._qdrant:
            self._qdrant.close()
        self._ready = False
        log.info("RAGService detenido.")

    @property
    def is_ready(self) -> bool:
        return self._ready

    # ── Consulta RAG ─────────────────────────────────────────────────

    async def query(
        self, text: str, k: int = 4, files_filter: list[str] | None = None,
    ) -> ChatResponse:
        """
        Ejecuta la cadena RAG completa.

        Parameters
        ----------
        text         : pregunta del usuario.
        k            : número de documentos a recuperar.
        files_filter : si se proporciona, solo busca en estos archivos.

        Returns
        -------
        ChatResponse con la respuesta y las fuentes.
        """
        if not self._ready:
            raise RuntimeError("RAGService no inicializado. Llama a start() primero.")

        # 1. Embedding de la consulta
        query_vector = self._embeddings.embed_query(text)

        # 2. Construir filtro de Qdrant (por nombre de archivo)
        qdrant_filter = None
        if files_filter:
            qdrant_filter = Filter(
                must=[
                    FieldCondition(
                        key="source",
                        match=MatchAny(any=files_filter),
                    )
                ]
            )

        # 3. Búsqueda en Qdrant
        results: list[ScoredPoint] = self._qdrant.search(
            collection_name=settings.COLLECTION_NAME,
            query_vector=query_vector,
            query_filter=qdrant_filter,
            limit=k,
            score_threshold=0.20,
        )

        if not results:
            return ChatResponse(
                answer=(
                    "No encontré documentos relevantes para tu consulta en la base "
                    "de conocimiento. Intenta reformular la pregunta o verifica que "
                    "los documentos estén indexados."
                ),
                sources=[],
                source_details=[],
            )

        # 3. Construir contexto
        context_parts: list[str] = []
        sources_set: set[str] = set()
        source_details: list[SourceInfo] = []

        for hit in results:
            payload = hit.payload or {}
            content = payload.get("page_content", "")
            source = payload.get("source", "desconocido")
            doc_type = payload.get("type", "unknown")

            context_parts.append(f"[Fuente: {source}]\n{content}")
            sources_set.add(source)
            source_details.append(
                SourceInfo(
                    filename=source,
                    doc_type=doc_type,
                    score=round(hit.score, 4),
                    snippet=content[:200] + "..." if len(content) > 200 else content,
                )
            )

        context = "\n\n".join(context_parts)
        sources = sorted(sources_set)

        # 4. Generar respuesta con LLM
        chain = _prompt | self._llm
        llm_out = await chain.ainvoke({"context": context, "query": text})

        log.info("Consulta OK | k=%d | hits=%d | sources=%s", k, len(results), sources)

        return ChatResponse(
            answer=llm_out.content,
            sources=sources,
            source_details=source_details,
        )

    # ── Info de colección ────────────────────────────────────────────

    def collection_count(self) -> int:
        """Devuelve el número de puntos en la colección."""
        try:
            info = self._qdrant.get_collection(settings.COLLECTION_NAME)
            return info.points_count or 0
        except Exception:
            return 0
