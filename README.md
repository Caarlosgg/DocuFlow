# DocuFlow — Sistema RAG Empresarial

<p align="center">
  <strong>Consulta tus documentos corporativos con Inteligencia Artificial</strong><br>
  <em>PDF & CSV → Embeddings → Búsqueda Vectorial → Respuesta LLM</em>
</p>

---

## Descripción

**DocuFlow** es un sistema **RAG (Retrieval-Augmented Generation)** de grado empresarial que permite cargar documentos PDF y CSV, indexarlos como vectores semánticos en Qdrant y consultarlos en lenguaje natural usando un LLM de última generación a través de Groq.

### Características principales

- **Chat IA** — Pregunta sobre tus documentos y obtén respuestas precisas con fuentes citadas
- **Subida de archivos** — Interfaz drag-and-drop para cargar PDFs y CSVs desde el navegador
- **Reindexación en caliente** — Reindexa la base de conocimiento sin reiniciar el servidor
- **Dashboard** — Vista general del estado del sistema, archivos y tecnología
- **Modelo LLM configurable** — Cambia de modelo editando una variable de entorno
- **Doble modo Qdrant** — Docker (producción) o local en disco (desarrollo rápido)

---

## Stack Tecnológico

| Componente | Tecnología | Descripción |
|---|---|---|
| **LLM** | Groq + LLaMA 3.3 70B | Inferencia ultra-rápida vía API |
| **Embeddings** | HuggingFace `all-MiniLM-L6-v2` | Modelo local, CPU, 384 dimensiones |
| **Vector DB** | Qdrant (Docker) | Base de datos vectorial de alto rendimiento |
| **Backend** | FastAPI + Uvicorn | API REST asíncrona con documentación automática |
| **Frontend** | HTML/CSS/JS vanilla | SPA ligera con tema oscuro profesional |
| **ETL** | LangChain + PyPDF + Polars | Pipeline de extracción y chunking |
| **Orquestación** | Docker Compose | Infraestructura como código |

---

## Estructura del Proyecto

```
DocuFlow/
├── backend/
│   ├── main.py           # Servidor FastAPI (lifespan, endpoints, static files)
│   ├── rag_service.py    # Servicio RAG (embedding → búsqueda → LLM)
│   └── schemas.py        # Modelos Pydantic (request/response)
├── core/
│   ├── config.py         # Configuración centralizada (Settings dataclass)
│   └── ingest.py         # Pipeline ETL (PDF/CSV → chunks → Qdrant)
├── frontend/
│   ├── index.html        # SPA: Dashboard + Chat + Upload
│   ├── css/styles.css    # Estilos dark theme responsive
│   └── js/app.js         # Lógica de navegación, chat, upload
├── data/                 # Directorio de documentos (PDFs, CSVs)
├── docker-compose.yml    # Qdrant container
├── requirements.txt      # Dependencias Python
├── .env                  # Variables de entorno (no se sube a Git)
├── .env.example          # Plantilla de configuración
├── .gitignore
└── README.md
```

---

## Requisitos Previos

- **Python 3.11+** (probado con 3.12)
- **Docker Desktop** (para Qdrant en modo Docker)
- **Clave API de Groq** — gratuita en [console.groq.com/keys](https://console.groq.com/keys)

---

## Instalación y Primer Uso

### 1. Clonar / descargar el proyecto

```bash
cd tu-directorio
git clone <url-del-repo> DocuFlow
cd DocuFlow
```

### 2. Crear entorno virtual e instalar dependencias

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configurar variables de entorno

```bash
copy .env.example .env
```

Editar `.env` y poner tu clave de Groq:

```ini
GROQ_API_KEY=gsk_tu_clave_aqui

# Modo Qdrant: "remote" (Docker) o "local" (sin Docker)
QDRANT_MODE=remote
QDRANT_HOST=127.0.0.1
QDRANT_PORT=6333

# Modelo LLM (cambiar para mejorar/abaratar)
LLM_MODEL=llama-3.3-70b-versatile

COLLECTION_NAME=docuflow_core
```

### 4. Levantar Qdrant con Docker

```bash
docker compose up -d
```

Verificar que está activo:

```bash
curl http://127.0.0.1:6333/healthz
# Respuesta esperada: "healthz check passed"
```

### 5. Colocar documentos en `data/`

Copia tus archivos PDF y/o CSV a la carpeta `data/`:

```bash
# Ejemplo
copy mi_reporte.pdf data/
copy datos_ventas.csv data/
```

### 6. Ejecutar la ingesta

```bash
python -m core.ingest --reset
```

Esto escaneará `data/`, extraerá texto, generará embeddings y los indexará en Qdrant.

### 7. Iniciar el servidor

```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### 8. Abrir en el navegador

```
http://localhost:8000
```

---

## Uso de la Aplicación

### Dashboard

La pantalla principal muestra:
- **Estado del sistema** — Backend, Qdrant y documentos indexados
- **Stack tecnológico** — Modelo LLM, embeddings y colección activa
- **Archivos disponibles** — Lista de PDFs/CSVs en el sistema
- **Accesos directos** — Botones para ir al Chat o Subir Archivos

### Chat IA

1. Haz clic en **"Chat IA"** en la barra de navegación
2. Escribe tu pregunta en el campo de texto
3. El sistema busca los fragmentos más relevantes y genera una respuesta
4. Haz clic en **"X fuentes utilizadas"** para ver los fragmentos exactos
5. Usa el selector **"Contexto"** para controlar cuántos fragmentos recuperar (2-10)
6. El botón de **papelera** limpia el historial del chat

### Subir Archivos

1. Haz clic en **"Subir Archivos"** en la barra de navegación
2. **Arrastra** archivos PDF/CSV a la zona de drop, o **haz clic** para seleccionar
3. Revisa los archivos en la cola y haz clic en **"Subir Archivos"**
4. Tras subir, haz clic en **"Reindexar Ahora"** para que estén disponibles en el chat

### Navegación

- Usa la **barra superior** para moverte entre Dashboard, Chat y Upload
- En Chat y Upload hay un **botón de flecha ←** para volver al Dashboard
- El indicador de estado en la esquina superior derecha muestra si el sistema está Online/Offline

---

## Cómo Cambiar / Mejorar el Modelo LLM

El modelo se configura en el archivo `.env`:

```ini
LLM_MODEL=llama-3.3-70b-versatile
```

### Modelos disponibles en Groq (Feb 2026)

| Modelo | Velocidad | Calidad | Ideal para |
|---|---|---|---|
| `llama-3.3-70b-versatile` | Media | Muy alta | Uso general, respuestas complejas |
| `llama-3.1-8b-instant` | Muy rápida | Buena | Respuestas rápidas, menor costo |
| `gemma2-9b-it` | Rápida | Buena | Alternativa ligera |
| `mixtral-8x7b-32768` | Rápida | Alta | Contextos largos (32K tokens) |

Para cambiar el modelo:
1. Edita `LLM_MODEL` en `.env`
2. Reinicia el servidor (`Ctrl+C` y volver a lanzar uvicorn)

> Consulta los modelos actuales en [console.groq.com/docs/models](https://console.groq.com/docs/models)

---

## Cómo Añadir Nuevos Documentos

### Opción A — Desde el Frontend (recomendado)

1. Abre `http://localhost:8000`
2. Ve a **"Subir Archivos"**
3. Arrastra tus PDFs/CSVs
4. Sube → Reindexar

### Opción B — Desde la terminal

```bash
# 1. Copiar archivos a data/
copy nuevo_archivo.pdf data/

# 2. Reindexar
python -m core.ingest --reset
```

### Opción C — API REST directa

```bash
# Subir archivo
curl -X POST http://localhost:8000/api/upload \
  -F "files=@mi_archivo.pdf"

# Reindexar
curl -X POST http://localhost:8000/api/reindex
```

---

## Endpoints de la API

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/` | Frontend (SPA) |
| `GET` | `/api/health` | Estado del sistema |
| `POST` | `/api/chat` | Consulta RAG (query + k) |
| `POST` | `/api/upload` | Subir archivos PDF/CSV |
| `GET` | `/api/files` | Listar archivos en data/ |
| `POST` | `/api/reindex` | Reindexar toda la colección |
| `GET` | `/docs` | Documentación Swagger interactiva |

### Ejemplo de consulta

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "¿Cuáles fueron los ingresos totales?", "k": 4}'
```

---

## Modo Qdrant Local (sin Docker)

Si no tienes Docker, puedes usar Qdrant en modo local (almacenamiento en disco):

```ini
# En .env
QDRANT_MODE=local
```

Los datos se guardarán en `qdrant_data/`. No requiere Docker pero tiene limitaciones de rendimiento para grandes volúmenes.

---

## Variables de Entorno

| Variable | Descripción | Valor por defecto |
|---|---|---|
| `GROQ_API_KEY` | Clave API de Groq (obligatoria) | — |
| `QDRANT_MODE` | `remote` (Docker) o `local` (disco) | `local` |
| `QDRANT_HOST` | Host de Qdrant | `127.0.0.1` |
| `QDRANT_PORT` | Puerto de Qdrant | `6333` |
| `LLM_MODEL` | Modelo de Groq a usar | `llama-3.3-70b-versatile` |
| `COLLECTION_NAME` | Nombre de la colección vectorial | `docuflow_core` |
| `BACKEND_HOST` | Host del servidor | `0.0.0.0` |
| `BACKEND_PORT` | Puerto del servidor | `8000` |

---

## Arquitectura

```
┌────────────────┐     ┌──────────────────┐     ┌──────────────┐
│   Frontend     │────▶│   FastAPI         │────▶│   Groq API   │
│   (HTML/JS)    │◀────│   Backend         │◀────│   (LLaMA 3)  │
└────────────────┘     └──────┬───────────┘     └──────────────┘
                              │
                    ┌─────────▼─────────┐
                    │     Qdrant DB     │
                    │ (Vectores 384d)   │
                    └───────────────────┘
                              ▲
                    ┌─────────┴─────────┐
                    │   Pipeline ETL    │
                    │ PDF/CSV → Chunks  │
                    │ → Embeddings      │
                    └───────────────────┘
```

**Flujo de una consulta:**
1. El usuario escribe una pregunta en el chat
2. El backend genera un embedding de la pregunta con HuggingFace
3. Qdrant busca los K fragmentos más similares (cosine similarity)
4. Se construye un prompt con el contexto recuperado
5. Groq genera la respuesta con LLaMA 3.3 70B
6. Se devuelve la respuesta + fuentes al frontend

---

## Solución de Problemas

| Problema | Solución |
|---|---|
| `GROQ_API_KEY no configurada` | Edita `.env` y añade tu clave |
| `ConnectionRefused` en Qdrant | Ejecuta `docker compose up -d` |
| Puerto 8000 ocupado | `netstat -ano \| findstr :8000` → `taskkill /PID <pid> /F` |
| Modelo deprecado | Cambia `LLM_MODEL` en `.env` (ver tabla de modelos) |
| Qdrant corrupto | Elimina `qdrant_storage/`, ejecuta `docker compose down && docker compose up -d` |

---

## Licencia

Proyecto educativo / personal. Usa las APIs y modelos según sus propios términos de servicio.
