# 🚀 DocuFlow — Sistema RAG Empresarial

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Qdrant](https://img.shields.io/badge/Qdrant-1.12-FF4088?style=for-the-badge&logo=qdrant&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3_70B-F55036?style=for-the-badge&logo=groq&logoColor=white)

**Consulta tus documentos corporativos con Inteligencia Artificial**

*PDF & CSV → Embeddings → Búsqueda Vectorial → Respuesta LLM*

</div>

---

## 📋 ¿Qué es DocuFlow?

**DocuFlow** es un sistema **RAG (Retrieval-Augmented Generation)** de grado empresarial. Carga tus documentos PDF y CSV, los indexa como vectores semánticos en Qdrant y consúltalos en lenguaje natural usando LLaMA 3.3 a través de Groq con latencia ultra-baja.

---

## ✨ Características

| Función | Descripción |
|---|---|
| 💬 **Chat IA** | Pregunta sobre tus documentos en lenguaje natural |
| 📁 **Subida de archivos** | Drag & drop de PDFs y CSVs desde el navegador |
| 🔍 **Filtro por archivo** | Selecciona qué documentos usar en cada consulta |
| 🗑️ **Gestión de archivos** | Elimina documentos directamente desde el frontend |
| ⚡ **Reindexación en caliente** | Indexa nuevos documentos sin reiniciar el servidor |
| 📊 **Dashboard** | Vista general del sistema, estado y métricas |

---

## 🏗️ Arquitectura

```
                    ┌─────────────────────────────────┐
                    │         USUARIO (Browser)        │
                    │    HTML + CSS + JavaScript SPA   │
                    └────────────────┬────────────────┘
                                     │ HTTP REST
                    ┌────────────────▼────────────────┐
                    │         FastAPI Backend          │
                    │   /api/chat  /api/upload  ...    │
                    └──────┬─────────────┬────────────┘
                           │             │
           ┌───────────────▼──┐    ┌────▼──────────────────┐
           │   RAG Service    │    │     ETL Pipeline       │
           │  Busca vectores  │    │  PDF → PyPDF           │
           │  Llama al LLM    │    │  CSV → Polars          │
           └───────┬──────────┘    │  Chunks → Embeddings   │
                   │               └────────┬───────────────┘
        ┌──────────▼──────────┐             │
        │     Qdrant (Docker) │◄────────────┘
        │  Base Datos Vectorial│
        └──────────┬──────────┘
                   │
        ┌──────────▼──────────┐
        │    Groq API         │
        │  LLaMA 3.3 70B      │
        └─────────────────────┘
```

---

## 🛠️ Stack Tecnológico

| Capa | Tecnología | Motivo |
|---|---|---|
| **LLM** | Groq + LLaMA 3.3 70B | Inferencia < 500ms |
| **Embeddings** | HuggingFace `all-MiniLM-L6-v2` | Local, CPU, privacidad total |
| **Vector DB** | Qdrant (Docker) | Alto rendimiento, filtros avanzados |
| **Backend** | FastAPI + Uvicorn | Async, tipado, docs automáticas |
| **Frontend** | HTML / CSS / JS Vanilla | SPA ligera, sin dependencias |
| **ETL** | LangChain + PyPDF + Polars | Pipeline robusto y rápido |
| **Config** | python-dotenv | Gestión segura de secretos |
| **Orquestación** | Docker Compose | Infraestructura reproducible |

---

## 📁 Estructura del Proyecto

```
DocuFlow/
├── 📂 backend/
│   ├── main.py           # Servidor FastAPI, endpoints, static files
│   ├── rag_service.py    # Servicio RAG (búsqueda vectorial + LLM)
│   └── schemas.py        # Modelos Pydantic request/response
├── 📂 core/
│   ├── config.py         # Configuración centralizada (Settings)
│   └── ingest.py         # Pipeline ETL (PDF/CSV → Qdrant)
├── 📂 frontend/
│   ├── index.html        # SPA: Dashboard + Chat + Upload
│   ├── css/styles.css    # Dark theme responsive
│   └── js/app.js         # Lógica navegación, chat, filtros
├── 📂 data/              # ← Coloca aquí tus PDFs y CSVs
├── 🐳 docker-compose.yml # Qdrant container + volumen persistente
├── 📄 requirements.txt   # Dependencias Python
├── 🔒 .env               # Variables de entorno (no subir a Git)
└── 📄 .env.example       # Plantilla de configuración
```

---

## ⚙️ Instalación

### Requisitos previos

- **Python 3.11+**
- **Docker Desktop** activo
- **API Key de Groq** → [console.groq.com/keys](https://console.groq.com/keys) *(gratuita)*

---

### 1️⃣ Clonar el repositorio

```bash
git clone https://github.com/Caarlosgg/DocuFlow.git
cd DocuFlow
```

### 2️⃣ Entorno virtual y dependencias

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### 3️⃣ Configurar variables de entorno

```bash
# Windows
copy .env.example .env

# Linux/macOS
cp .env.example .env
```

Edita `.env` y añade tu clave:

```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
QDRANT_HOST=localhost
QDRANT_PORT=6333
COLLECTION_NAME=docuflow_core
LLM_MODEL=llama-3.3-70b-versatile
```

### 4️⃣ Levantar Qdrant

```bash
docker compose up -d
```

### 5️⃣ Indexar documentos

Coloca tus PDFs/CSVs en `data/` y ejecuta:

```bash
python -m core.ingest --reset
```

### 6️⃣ Iniciar el servidor

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

**Abre** → `http://localhost:8000` 🎉

---

## 🖥️ Uso

```
http://localhost:8000
        │
        ├── 📊 Dashboard    → Estado del sistema, archivos cargados
        ├── 💬 Chat IA      → Haz preguntas, activa filtros por archivo
        └── 📁 Subir Archivos → Drag & drop, reindexar, eliminar
```

---

## 🔌 API Endpoints

```
GET    /api/health              → Estado del sistema
POST   /api/chat                → Consulta RAG con filtros opcionales
POST   /api/upload              → Subir PDF o CSV
GET    /api/files               → Listar documentos indexados
POST   /api/reindex             → Reindexar toda la colección
DELETE /api/files/{filename}    → Eliminar un documento
GET    /docs                    → Swagger UI automático
```

---

## 🔧 Modelos LLM disponibles en Groq

| Modelo | Velocidad | Calidad |
|---|---|---|
| `llama-3.3-70b-versatile` | ⚡⚡ | ⭐⭐⭐⭐⭐ |
| `llama-3.1-8b-instant` | ⚡⚡⚡ | ⭐⭐⭐ |
| `mixtral-8x7b-32768` | ⚡⚡ | ⭐⭐⭐⭐ |
| `gemma2-9b-it` | ⚡⚡⚡ | ⭐⭐⭐ |

Cambia el modelo editando `LLM_MODEL` en `.env`, sin reiniciar.

---

## ❗ Solución de Problemas

<details>
<summary><b>Qdrant no responde</b></summary>

```bash
docker compose down
Remove-Item -Recurse -Force .\qdrant_storage  # Windows
rm -rf ./qdrant_storage                        # Linux/macOS
docker compose up -d
```
</details>

<details>
<summary><b>Puerto 8000 ocupado</b></summary>

```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <pid> /F

# Linux/macOS
lsof -i :8000
kill -9 <pid>
```
</details>

<details>
<summary><b>Error de API Key</b></summary>

Verifica que `.env` contiene `GROQ_API_KEY=gsk_...` y reinicia el servidor tras el cambio.
</details>

<details>
<summary><b>Modelo LLM deprecado</b></summary>

Cambia `LLM_MODEL` en `.env` por uno de la tabla de modelos disponibles y reinicia el servidor.
</details>

---

## 📄 Licencia

Proyecto de uso educativo y personal. Respeta los términos de servicio de [Groq](https://groq.com) y [HuggingFace](https://huggingface.co).

---

<div align="center">

**Hecho con ❤️ usando FastAPI, Qdrant y LLaMA**

</div>
