# PrepPilot API

PrepPilot is an AI-powered conceptual tutor and exam preparation RAG (Retrieval-Augmented Generation) backend. It indexes educational resources (notes, previous year questions (PYQs), and syllabi) into a vector database and allows students to ask questions about course content. The system supports streaming text responses and low-latency, real-time voice answers (using Gemini Live API WebSockets) via a specialized teaching assistant persona named **"Sakshi didi"**.

---

## Table of Contents
1. [Key Features](#key-features)
2. [Technology Stack](#technology-stack)
3. [Project Directory Structure](#project-directory-structure)
4. [Database Schemas & Storage](#database-schemas--storage)
5. [LangGraph Pipelines & Workflows](#langgraph-pipelines--workflows)
   - [Document Ingestion Pipeline](#document-ingestion-pipeline)
   - [Query & Retrieval Pipeline](#query--retrieval-pipeline)
6. [API Endpoints Reference](#api-endpoints-reference)
7. [Environment Configuration](#environment-configuration)
8. [Local Setup & Deployment](#local-setup--deployment)

---

## Key Features
- **Dynamic Ingestion (Native & Scanned PDFs)**: Evaluates PDF types and processes them accordingly. Native PDFs have text extracted and inline images described; scanned PDFs are rendered and processed page-by-page via visual models.
- **Incremental Batch Processing**: Processes PDFs in batches of 5 pages, clearing in-memory chunks at each step to prevent memory leaks or out-of-memory errors on large documents.
- **Intent-Based Query Routing**: Analyzes user query intent (e.g., course query, assignment help, greeting, code block, unsafe content) and adapts retrieval settings accordingly.
- **RAG-based Concept Tutoring**: Uses retrieved materials to guide the student towards answers rather than generating flat, copy-paste solutions (especially for assignment/homework intents).
- **Real-Time Text & Audio Streaming**: Supports standard Server-Sent Events (SSE) text streams as well as live binary audio streams through the Gemini Live API.
- **Guest Session Limit Management**: Imposes limits (maximum 20,000 tokens or 50 messages) on guest accounts using Redis tracking.

---

## Technology Stack
- **Framework**: FastAPI (Asynchronous REST API, Server-Sent Events)
- **Orchestration**: LangGraph (State Graph workflow engine)
- **Vector Database**: ChromaDB (Cosine similarity vector space, metadata filters)
- **Relational Databases**: 
  - PostgreSQL (via SQLAlchemy + `asyncpg`) for subject configuration
  - SQLite (`data/subjects.db`) for lightweight task tracking
- **Caching & Session Storage**: Redis (caching chat sessions, guest counters, conversation summaries)
- **AI Models**: Google Gemini models via LangChain & Google GenAI SDK:
  - `gemini-2.5-flash` / `gemini-3.5-flash` (Conversational reasoning & image descriptions)
  - `gemini-embedding-2` (Text chunk embeddings, 768 dimensions)
  - `gemini-3.1-flash-live-preview` (Bi-directional real-time audio interaction)

---

## Project Directory Structure

```
prep_pilot/
│
├── app/
│   ├── api/                 # FastAPI Router Modules
│   │   ├── admin.py         # Chunk queries, deletion, and document upload
│   │   ├── chats.py         # Sessions management and RAG queries
│   │   ├── ingestion.py     # Ingestion background task status
│   │   └── subjects.py      # Subject configuration CRUD
│   │
│   ├── core/                # Core System Utilities & Singletons
│   │   ├── chroma_db.py     # ChromaDB Client configuration
│   │   ├── database.py      # SQLAlchemy PostgreSQL async engine config
│   │   ├── helpers.py       # Helper functions (e.g., filename sanitation)
│   │   ├── llm.py           # LLM chains, schemas, and fallback setups
│   │   ├── redis_servcie.py # Redis connection, keys, and session getters
│   │   ├── settings.py      # Pydantic configuration loader (.env)
│   │   └── task_manager.py  # SQLite task tracking and background runner
│   │
│   ├── embedings/           # Embedding helpers
│   │
│   ├── graphs/              # LangGraph Graph Workflows
│   │   ├── chats/           # Query, routing, embedding, and retrieval nodes
│   │   └── ingestion/       # PDF parsing, chunking, and database upserts
│   │
│   ├── ingestion/           # Gemini Vision image/page extraction prompts
│   │   └── vision.py
│   │
│   ├── models/              # SQLAlchemy Database Models
│   │   └── subject_models.py
│   │
│   ├── schemas/             # Pydantic validation schemas
│   │
│   └── main.py              # Application initialization and Lifespan
│
├── data/                    # Local storage (ChromaDB, SQLite, uploads)
├── docker-compose.yml       # Docker container orchestration setup
└── Dockerfile               # Build configuration for API service
```

---

## Database Schemas & Storage

### 1. PostgreSQL (Relational Subject Storage)
Configured using SQLAlchemy async engine. It holds static subject metadata.

#### Table: `subjects`
| Column Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `subject_id` | `INTEGER` | Primary Key, Auto-increment | Unique identifier for a subject |
| `subject_name`| `VARCHAR` | Not Null | Display name of the subject |
| `subject_codes`| `ARRAY(VARCHAR)`| Nullable | Technical subject identifiers |
| `universities`| `ARRAY(VARCHAR)`| Nullable | Associated universities |
| `slugs` | `ARRAY(VARCHAR)`| Nullable | URL-friendly unique identifiers |
| `semester` | `INTEGER` | Nullable | Course semester index |

---

### 2. SQLite (Ingestion Task Tracking)
Located in `data/subjects.db`. Tracked asynchronously during document upload pipelines.

#### Table: `tasks`
| Column Name | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `task_id` | `TEXT` | Primary Key | Unique UUID string for the background task |
| `status` | `TEXT` | Not Null | `PROCESSING`, `EXTRACTING_TEXT`, `CHUNKING`, `EMBEDDING`, `STORING`, `COMPLETED`, `FAILED` |
| `file_name` | `TEXT` | | Sanitized filename of the uploaded PDF |
| `subject_id` | `INTEGER` | | FK mapping to the subject |
| `total_embedded`| `INTEGER` | | Number of chunks sent to the embedder |
| `stored` | `INTEGER` | | Number of chunks successfully upserted to ChromaDB |
| `error_message` | `TEXT` | | Error stack trace if task fails |
| `created_at` | `TEXT` | | ISO 8601 creation timestamp |
| `updated_at` | `TEXT` | | ISO 8601 modification timestamp |

---

### 3. Redis (Cache, Sessions & Limits)
Maintains transient state data. Keys expire after 24 hours (`86400s`) for guest accounts.

- **Session Info (`session:{session_id}`)**:
  Stored as serialized JSON containing:
  - `user_id` (`str | None`): Authenticated user ID.
  - `session_key` (`str`): The Redis key string.
  - `is_guest` (`bool`): Indicates if guest session limit rules apply.
  - `tokens_used` (`int`): Running total of tokens consumed by the session.
  - `messages_count` (`int`): Count of messages sent in the session.
- **Chat History (`chats:{session_id}:{subject_id}`)**:
  A Redis **List** containing JSON objects:
  ```json
  {"r": "u" | "a", "c": "message text"}
  ```
  *(where `r` is role (User/Assistant) and `c` is the content string)*
- **Conversation Summary (`chat_summary:{session_id}:{subject_id}`)**:
  A cached string containing a bulleted summary of previous exchanges to limit token bloat.

---

### 4. ChromaDB (Vector Database)
Persistent vector indexes are stored under `data/chromadb`.
- **Collection Name**: `prep_pilot_documents`
- **Metric**: Cosine Similarity (`hnsw:space: cosine`)
- **Payload Document**: Raw text chunk extracted from notes/PYQs.
- **Metadata Fields**:
  ```json
  {
    "doc_type": "notes" | "pyq" | "syllabus",
    "source_file": "filename.pdf",
    "subject": "Subject Name",
    "subject_id": 123,
    "chunk_index": 0
  }
  ```
- **Chunk ID Format**: `{subject_id}_s{source_file}_c{chunk_index}`

---

## LangGraph Pipelines & Workflows

### Document Ingestion Pipeline

Triggered asynchronously upon document upload. The pipeline processes document pages in batches of 5 pages. 

```mermaid
graph TD
    Start([START]) --> get_pdf_type[get_pdf_type]
    
    %% PDF Classification Route
    get_pdf_type --> RoutePDF{PDF Type?}
    RoutePDF -- "Text length > 300 (Native)" --> extract_native_batch[extract_native_batch]
    RoutePDF -- "Text length <= 300 (Vision)" --> extract_scanned_batch[extract_scanned_batch]
    
    %% Native Flow
    extract_native_batch --> create_chunks[create_chunks]
    create_chunks --> embed_chunks[embed_chunks]
    
    %% Vision Flow
    extract_scanned_batch --> embed_chunks
    
    %% Storage and Loop Check
    embed_chunks --> store_embeddings[store_embedings]
    store_embeddings --> RouteLoop{current_page < total_pages?}
    
    RouteLoop -- "Yes (Next Batch)" --> extract_native_batch
    RouteLoop -- "No (Finished)" --> End([END])
    
    classDef nodeFill fill:#1E293B,stroke:#475569,stroke-width:2px,color:#F8FAFC;
    classDef decisionFill fill:#3730A3,stroke:#6366F1,stroke-width:2px,color:#F8FAFC;
    class get_pdf_type,extract_native_batch,extract_scanned_batch,create_chunks,embed_chunks,store_embeddings nodeFill;
    class RoutePDF,RouteLoop decisionFill;
```

#### Pipeline Details & Conditions:
1. **`get_pdf_type`**: Evaluates the PDF. If the first three pages contain `> 300` characters total, it uses the **Native** route; otherwise, it switches to the **Vision** route.
2. **Native Batching (`extract_native_batch`)**: Parses 5 pages to Markdown. Searches for embedded diagrams or images, extracts their bytes, gets description from Gemini, and embeds descriptions inline like `<!-- IMAGE_START --> description <!-- IMAGE_END -->`.
3. **Chunking (`create_chunks`)**: Splits the Markdown using `MarkdownTextSplitter` (size 500, overlap 50) while preserving image block tags.
4. **Vision Batching (`extract_scanned_batch`)**: Converts 5 pages to high-resolution PNGs and passes them directly to Gemini Vision using structured schemas (`GeminiChunkList`) to return ready-to-use semantic chunks.
5. **Memory Flattening (`store_embeddings`)**: Inserts newly embedded chunks to ChromaDB and updates the SQLite status database. It returns empty arrays for chunks and markdown states to keep RAM utilization flat.

---

### Query & Retrieval Pipeline

Processes incoming questions from the API endpoints.

```mermaid
graph TD
    Start([START]) --> intent_analyser[intent_analyser]
    
    %% Intent Router
    intent_analyser --> RouteQuery{Retrieval Mode?}
    RouteQuery -- "required / optional" --> query_embeddings[query_embeddings]
    RouteQuery -- "none" --> End([END])
    
    %% Retrieval Flow
    query_embeddings --> retrieve_chunks[retrieve_chunks]
    retrieve_chunks --> End
    
    classDef nodeFill fill:#1E293B,stroke:#475569,stroke-width:2px,color:#F8FAFC;
    classDef decisionFill fill:#3730A3,stroke:#6366F1,stroke-width:2px,color:#F8FAFC;
    class intent_analyser,query_embeddings,retrieve_chunks nodeFill;
    class RouteQuery decisionFill;
```

#### Pipeline Details & Conditions:
1. **`intent_analyser`**: Pulls chat history and summaries from Redis. Passes them with the user query to Gemini to fetch structured intent analyses (`QueryAnalysis`).
   - *Intents*: `course_query`, `greeting`, `conversation`, `assistant_meta`, `general_question`, `assignment_request`, `code_generation`, `unsafe`.
   - *Standalone Query*: Rewrites the query to include conversational context.
   - *Expanded Queries*: Generates up to 3 alternative semantic variants for vector database matching.
2. **Direct Bypasses**: If the intent is `unsafe`, `code_generation`, or does not require retrieval (`retrieval_mode == "none"`), the graph terminates directly at `END`. The response generation endpoint handles these cases.
3. **`retrieve_chunks`**: Executes vector query searches in ChromaDB on all expanded query representations, merges results, deduplicates by Chunk ID, and ranks chunks by confidence (retrieval frequency divided by query count).

---

## API Endpoints Reference

### 1. Subject Management

#### `POST /subjects`
Creates a subject entry in PostgreSQL.
- **Request Body**:
  ```json
  {
    "subject_name": "Database Management Systems",
    "subject_codes": ["CS301"],
    "universities": ["State University"],
    "slugs": ["dbms"],
    "semester": 5
  }
  ```
- **Response**: `201 Created` with a confirmation payload.

#### `GET /subjects`
Fetches all subjects stored in PostgreSQL.

#### `PATCH /subjects/{subject_id}/update`
Updates subject details.

#### `DELETE /subjects/{subject_id}`
Deletes a subject from PostgreSQL.

---

### 2. Admin & Document Ingestion

#### `POST /admin/{subject_id}/upload/{doc_type}`
Uploads and indexes a PDF.
- **Path Params**:
  - `subject_id`: Subject ID.
  - `doc_type`: `notes`, `pyq`, or `syllabus`.
- **Form Data**: `file` (Multipart file upload, max 50MB).
- **Process**: Spawns ingestion in the background and returns a `task_id` for tracking.

#### `GET /tasks/{task_id}/status`
Check background ingestion task progress.
- **Response**:
  ```json
  {
    "success": true,
    "message": "Task status fetched successfully.",
    "data": {
      "task_id": "uuid_hex",
      "status": "STORING",
      "file_name": "dbms_notes.pdf",
      "subject_id": 1,
      "total_embedded": 45,
      "stored": 30,
      "error_message": null,
      "created_at": "timestamp",
      "updated_at": "timestamp"
    }
  }
  ```

#### `GET /admin/chunks`
Queries vector database index chunks. Supports filters for `subject_id`, `doc_type`, and `source_file`.

#### `DELETE /admin/chunks/{chunk_id}`
Deletes a single vector chunk from ChromaDB.

---

### 3. Chats & Queries

#### `POST /chats/query`
Sends a query to the tutor chatbot.
- **Request Body**:
  ```json
  {
    "query": "What is the 3rd Normal Form?",
    "subject_id": 1,
    "session_id": "optional_session_uuid",
    "format": "text" | "audio",
    "top_k": 5
  }
  ```
- **Response**: `200 OK` (Stream of Server-Sent Events `text/event-stream`).
  - **Text Mode**: Returns token chunks as `event: token` events containing JSON payloads.
  - **Audio Mode**: Connects to the Gemini audio model websocket and streams PCM bytes encoded as base64 alongside text transcription events.
  - **Completion Event**: Yields `event: done` with statistics.

#### `GET /chats/sessions/{session_id}`
Fetches guest session metrics (consumed tokens and message count).

#### `GET /chats/{chat_id}/{subject_id}`
Retrieves historical conversation logs for a chat session.

---

## Environment Configuration
The project is configured via environment variables. Create a `.env` file in the root directory:

```env
# Gemini Credentials
GEMINI_API_KEY=your_gemini_api_key

# AWS Credentials (For file storage integration)
AWS_ACCESS_KEY=your_aws_access_key
AWS_SECRET_KEY=your_aws_secret_key
AWS_REGION=ap-south-1
AWS_S3_BUCKET=prep-pilot-docs

# Redis Settings
REDIS_HOST=redis
REDIS_PORT=6379

# PostgreSQL Credentials
POSTGRES_USER=admin
POSTGRES_PASSWORD=password
POSTGRES_DB=prep_pilot
DATABASE_URL=postgresql+asyncpg://admin:password@postgres:5432/prep_pilot
```

---

## Local Setup & Deployment

### Run using Docker Compose (Recommended)
Make sure you have Docker and Docker Compose installed.

1. Clone this repository.
2. Setup your `.env` file in the root.
3. Boot the environment:
   ```bash
   docker-compose up --build
   ```
This will build and start:
- **postgres**: Exposes port `5432` with volume mapping for persistence.
- **redis**: Exposes port `6379`.
- **api**: Exposes the FastAPI application at `http://localhost:8000`.

### Manual Development Setup
1. Create a virtual environment and install requirements:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Make sure you have Redis and PostgreSQL running locally. Update `REDIS_HOST` and `DATABASE_URL` in `.env` to match your local setup (e.g., `REDIS_HOST=127.0.0.1` and `DATABASE_URL=postgresql+asyncpg://admin:password@localhost:5432/prep_pilot`).
3. Run the FastAPI development server:
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
4. Access API documentation at `http://127.0.0.1:8000/docs`.
