# Architecture Decision Records (ADR) & Design Log
**Project:** Support Ticket Triage Assistant  
**Assessment:** Aqlior Associate AI Engineer Take-Home  
**Candidate:** Dinod (`dinod001`)

This document records the foundational architectural decisions made during the development of the **Support Ticket Triage Assistant**, outlining the options considered, the choices made, and the underlying engineering trade-offs.

---

### Decision 1: Backend Framework & Language
- **Choice:** Python 3.11 with FastAPI (Async ASGI).
- **Alternatives Considered:** Node.js (Express / NestJS), Go (Gin), Django.
- **Rationale:** 
  - FastAPI provides native async/await concurrency, automatic OpenAPI (Swagger) documentation, and deep integration with Pydantic for strict schema validation.
  - Python possesses the richest ecosystem for AI/LLM integration, tokenization, embeddings, and vector similarity calculation.
- **Trade-offs:** Slightly higher memory footprint than Go, but developer velocity and AI library ecosystem make Python the optimal choice for an AI engineer assessment.

---

### Decision 2: Local AI Inference Provider & Model Selection
- **Choice:** Ollama running `qwen2.5:1.5b` (Q4_K_M quantized) for chat/triage and `nomic-embed-text` for vector embeddings.
- **Alternatives Considered:** `llama3.2:3b`, `mistral:7b`, Local HuggingFace Transformers in backend container, OpenAI/Claude API.
- **Rationale:** 
  - **Zero Cost & Zero API Key:** The reviewer must run the system with `docker compose up --build` without requiring external paid accounts or personal API keys.
  - `qwen2.5:1.5b` delivers outstanding structured JSON adherence while running smoothly on standard laptop CPUs (consuming under 1.5 GB RAM).
  - Isolating Ollama in its own container keeps the backend container build lean and fast.
- **Trade-offs:** CPU inference on laptop hardware takes 2–4 seconds per call. Mitigated by UI loading state indicators and `asyncio.gather` parallelization.

---

### Decision 3: Swappable LLM Architecture (Provider Factory Pattern)
- **Choice:** Abstract Base Class (`BaseLLMProvider`) with concrete implementations: `OllamaProvider`, `GroqProvider`, and `MockLLMProvider`.
- **Alternatives Considered:** Directly hardcoding Ollama HTTP endpoints inside business logic.
- **Rationale:** 
  - Meets the explicit core requirement: *"Make the LLM provider swappable through configuration, so the app is not tied to one vendor."*
  - Enables instant switching via `LLM_PROVIDER=ollama` or `LLM_PROVIDER=groq` in `.env` without modifying a single line of application code.
- **Trade-offs:** Requires an abstraction layer and interface maintenance, but eliminates vendor lock-in.

---

### Decision 4: Knowledge Base Vector Retrieval & Storage
- **Choice:** Section-level semantic chunking with ChromaDB vector store + In-memory Cosine Similarity fallback.
- **Alternatives Considered:** External vector DBs (Pinecone, Qdrant), PostgreSQL `pgvector` extension.
- **Rationale:** 
  - For a focused knowledge base of 9 help articles, in-process ChromaDB with persistent storage in `backend/chroma_data/` and in-memory cosine fallback provides sub-millisecond retrieval without adding another heavy container dependency.
  - Generates zero cloud costs and works seamlessly offline.
- **Trade-offs:** In-memory indices do not scale out-of-the-box to millions of documents. In production, this would be migrated to `pgvector` or Qdrant.

---

### Decision 5: Concurrency Optimization via `asyncio.gather`
- **Choice:** Concurrently execute AI Triage (`execute_triage`) and RAG Draft Generation (`generate_draft_reply`) using `asyncio.gather`.
- **Alternatives Considered:** Sequential execution (`await triage` followed by `await rag`).
- **Rationale:** 
  - Neither task depends on the output of the other; both only require the incoming ticket's `title` and `description`.
  - Running both LLM calls in parallel cuts the total request latency by **50%**.
- **Trade-offs:** Requires non-blocking async HTTP clients (`httpx.AsyncClient`) throughout the stack.

---

### Decision 6: Relational Database & Persistence
- **Choice:** PostgreSQL 16 via Docker with SQLAlchemy ORM and automatic schema initialization (`init_db()`).
- **Alternatives Considered:** SQLite, MongoDB, DynamoDB.
- **Rationale:** 
  - PostgreSQL is the production standard for transactional workloads and supports `JSONB` for unstructured extracted entities (order numbers, tracking IDs).
  - Automatically creates tables on server boot via FastAPI lifespan without requiring manual migration commands from the reviewer.
- **Trade-offs:** Requires container healthchecks (`pg_isready`) before the backend can connect.

---

### Decision 7: CI/CD Testing Strategy (Mocked LLM)
- **Choice:** Pytest test suite utilizing `MockLLMProvider` with deterministic in-memory fixtures.
- **Alternatives Considered:** Calling real Ollama / Groq inside GitHub Actions runners.
- **Rationale:** 
  - Meets the requirement: *"CI with GitHub Actions on every pull request... Tests must not call a real LLM; mock it."*
  - All 13 unit and integration tests execute in under 4 seconds in CI with 100% deterministic reproducibility and zero API costs.
- **Trade-offs:** Real model hallucinations are not caught in CI unit tests; mitigated by the separate `evaluate.py` benchmark harness.

---

### Decision 8: Server-Sent Events (SSE) Streaming (Stretch Goal)
- **Choice:** FastAPI `StreamingResponse` with `text/event-stream` and Nginx `proxy_buffering off;`.
- **Alternatives Considered:** WebSockets, Polling.
- **Rationale:** 
  - SSE is unidirectional and significantly simpler than WebSockets for LLM token streaming.
  - Native browser `EventSource` support with minimal overhead.
- **Trade-offs:** Requires configuring Nginx to disable response buffering so tokens emit in real time.

---

### Decision 9: RAG Evaluation Strategy (Ragas Framework)
- **Choice:** Standalone benchmark script `backend/evaluate.py` with 10 ground-truth tickets, with architectural alignment to the Ragas evaluation framework.
- **Rationale:** 
  - Provides instant metrics on category accuracy, citation relevance, and latency.
  - In production, Ragas metrics (**Faithfulness, Answer Relevance, Context Precision, Context Recall**) provide quantitative guards against hallucinations before deploying prompt updates.
