# Architecture Decision Records (ADR) & Design Log

This document records the architectural and design decisions made during the development of the **Support Ticket Triage Assistant**, outlining the options considered, the choices made, and the underlying trade-offs.

---

### Decision 1: Backend Framework & Language
- **Choice:** Python 3.11 with FastAPI.
- **Alternatives Considered:** Node.js (Express / NestJS), Go (Gin).
- **Rationale:** 
  - FastAPI provides high-performance async execution, native OpenAPI documentation, and deep integration with Pydantic for strict data validation.
  - Python has the most mature ecosystem for AI/LLM integration, tokenization, and vector manipulation.
- **Trade-offs:** Slightly higher memory footprint than Go, but developer velocity and AI library ecosystem make Python the optimal choice for this role.

---

### Decision 2: Local AI Inference Provider & Model Selection
- **Choice:** Ollama running `qwen2.5:1.5b` for chat/triage and `nomic-embed-text` for embeddings.
- **Alternatives Considered:** `llama3.2:3b`, Local Transformers/Torch in backend container, OpenAI/Claude API.
- **Rationale:** 
  - Free requirement & zero-API-key reviewer requirement: The reviewer must run the system without any external accounts or costs.
  - `qwen2.5:1.5b` has remarkable structured JSON output adherence while running comfortably on standard laptop CPUs (under 2GB RAM usage).
  - Ollama is isolated in its own Docker container, keeping the backend container lean and fast to build.
- **Trade-offs:** CPU inference takes 2–5 seconds per request. Mitigated by clear frontend loading spinners and resilient timeouts.

---

### Decision 3: Swappable LLM Architecture
- **Choice:** Provider pattern / Factory interface (`LLMProvider` abstract base class with `OllamaProvider` and `GroqProvider` / `GeminiProvider`).
- **Alternatives Considered:** Hardcoding Ollama HTTP calls directly in business logic.
- **Rationale:** 
  - Meets the requirement: "Make the LLM provider swappable through configuration".
  - Allows seamless switching via `LLM_PROVIDER=ollama` or `LLM_PROVIDER=groq` in `.env` without modifying a single line of application code.
- **Trade-offs:** Requires an abstraction layer and interface maintenance.

---

### Decision 4: Knowledge Base & Vector Retrieval Approach
- **Choice:** In-memory vector index with Cosine Similarity (Numpy) pre-computed on startup from 8–10 Markdown articles.
- **Alternatives Considered:** Pinecone / Weaviate (cloud), Qdrant / pgvector (PostgreSQL extension).
- **Rationale:** 
  - With a small sample knowledge base of 8–10 articles, dedicated vector database containers add unnecessary overhead and startup latency.
  - In-memory cosine similarity is instantaneous, has zero external service dependencies, and is 100% deterministic and easy to unit test.
- **Trade-offs:** Does not scale out-of-the-box to 100,000+ documents (which would require pgvector or Qdrant). Documented under Known Limitations.

---

### Decision 5: Database & Persistence
- **Choice:** PostgreSQL 16 via Docker with SQL initialization script / Alembic.
- **Alternatives Considered:** SQLite, MongoDB.
- **Rationale:** 
  - PostgreSQL is production standard, supports JSONB for unstructured extracted entities, and satisfies the requirement for a containerized database.
- **Trade-offs:** Requires a container healthcheck before the backend can boot.

---

### Decision 6: Testing Strategy in CI
- **Choice:** Pytest with mocked LLM calls using `unittest.mock`.
- **Alternatives Considered:** Running Ollama inside GitHub Actions runner.
- **Rationale:** 
  - Pulling models inside GitHub Actions runners consumes 5+ minutes and frequently runs out of memory or hits rate limits.
  - Assessment requirement explicitly states: *"Tests must not call a real LLM; mock it."*
  - Mocking allows 100% coverage of JSON edge cases, parsing failures, retry logic, and fallback branches in under 5 seconds.
