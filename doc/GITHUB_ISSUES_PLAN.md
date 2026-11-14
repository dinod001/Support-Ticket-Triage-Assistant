# GitHub Issues Plan & Template (Aqlior Assessment)

Before writing production code, copy and paste these issues into your **GitHub Repository > Issues tab**.  
This demonstrates team planning, prioritization, and satisfies the 15% marks for **Organization and Workflow**.

---

### Issue 1: [Core] Project Architecture, Decision Log & Environment Configuration
- **Label:** `core`
- **Description:**
  Establish foundational setup:
  - Add `.gitignore` to prevent secret leakage.
  - Add `.env.example` defining database and Ollama configurations.
  - Setup Architecture decision log in `docs/DECISIONS.md`.
- **Acceptance Criteria:**
  - [x] `.gitignore` and `.env.example` committed.
  - [x] Initial documentation committed to repository.

---

### Issue 2: [Core] Sample Knowledge Base Help Articles (8-10 Topics)
- **Label:** `core`
- **Description:**
  Create 8 to 10 concise Markdown help articles for the support team under `backend/app/knowledge_base/`.
  Topics: Refunds, shipping times, password resets, account deletion, damaged items, cancellations, billing plans, and payment methods.
- **Acceptance Criteria:**
  - [ ] 8-10 markdown files created with clear titles and policies.

---

### Issue 3: [Core] PostgreSQL Database Schema & SQLAlchemy Models
- **Label:** `core`
- **Description:**
  Implement relational database persistence:
  - `tickets` table (title, description, customer_email, status, category, priority, sentiment, summary, entities JSONB, draft_reply, cited_articles).
  - `llm_logs` table (ticket_id, call_type, model_name, latency_ms, success, error_message).
- **Acceptance Criteria:**
  - [ ] Models and database engine configured with automatic table initialization on boot.

---

### Issue 4: [Core] Swappable LLM Provider & Centralized Prompt Module
- **Label:** `core`
- **Description:**
  Implement provider pattern (`BaseLLMProvider`) supporting Ollama (default local) and Groq/Gemini (optional).
  Centralize all prompt templates in `backend/app/prompts/` rather than scattering through code.
- **Acceptance Criteria:**
  - [ ] Provider switchable via `LLM_PROVIDER` in environment variables.
  - [ ] Dedicated prompt files for Triage and RAG drafting.

---

### Issue 5: [Core] AI Triage Engine with Structured JSON, Retry & Fallback
- **Label:** `core`
- **Description:**
  Extract `category`, `priority`, `sentiment`, `summary`, and `entities` using strict JSON schema validation (Pydantic).
  If invalid: retry once. If retry fails: set `category = "needs manual triage"` without crashing.
- **Acceptance Criteria:**
  - [ ] Valid JSON parses into Pydantic model.
  - [ ] Invalid JSON triggers 1 retry.
  - [ ] Persistent failures gracefully fall back to "needs manual triage".

---

### Issue 6: [Core] Knowledge Base Embedding & RAG Reply Drafting
- **Label:** `core`
- **Description:**
  Compute embeddings for the 8-10 help articles. Retrieve the most relevant article for an incoming ticket using cosine similarity.
  Draft a helpful reply citing the source article title. If no article matches, provide an honest fallback without hallucinating policies.
- **Acceptance Criteria:**
  - [ ] Embeddings generated on startup.
  - [ ] Top matching article cited in draft reply.
  - [ ] Low-similarity inquiries trigger honest disclaimer.

---

### Issue 7: [Core] FastAPI REST API Endpoints & Request Orchestration
- **Label:** `core`
- **Description:**
  Create REST API routes:
  - `POST /api/tickets`: Create ticket, execute triage & RAG, persist to DB, log latency.
  - `GET /api/tickets`: List tickets with filters (`status`, `category`, `priority`).
  - `GET /api/tickets/{id}`: Detailed view.
  - `PATCH /api/tickets/{id}`: Update status and edited reply.
- **Acceptance Criteria:**
  - [ ] Input validation and proper HTTP error codes.
  - [ ] Swagger docs accessible at `/docs`.

---

### Issue 8: [Core] React Frontend (Ticket Form, Filtered List & Detail Reviewer)
- **Label:** `core`
- **Description:**
  Build React (Vite + Tailwind CSS) client with 3 views:
  1. Ticket submission form with visible loading/spinner state.
  2. Ticket list with status/category/priority filter dropdowns.
  3. Detail page showing AI triage cards, editable draft reply textarea, and save button.
- **Acceptance Criteria:**
  - [ ] Clear loading and error states during AI processing.
  - [ ] Fully functional filtering and reply editing.

---

### Issue 9: [Core] Docker Compose Setup with Service Healthchecks
- **Label:** `core`
- **Description:**
  Provide single-command startup: `docker compose up --build`.
  Orchestrate postgres, ollama (with auto-pull script for `qwen2.5:1.5b` and `nomic-embed-text`), backend, and frontend with strict healthcheck dependencies.
- **Acceptance Criteria:**
  - [ ] Starts deterministically on a clean machine without manual intervention.

---

### Issue 10: [Core] Unit Tests (Mocked LLM) & GitHub Actions CI/CD
- **Label:** `core`
- **Description:**
  Implement Pytest suite mocking all LLM calls:
  - Triage parsing, validation, and invalid-JSON fallback.
  - API creation and filter listing test.
  - Retrieval matching test.
  Setup GitHub Actions CI on PRs and CD on merge to `main` (GHCR push).
- **Acceptance Criteria:**
  - [ ] Tests execute in < 10 seconds without calling real LLM.
  - [ ] CI workflow runs green on pull requests.

---

### Issue 11: [Stretch] Streaming Draft Reply & Evaluation Script
- **Label:** `stretch`
- **Description:**
  (Nice-to-have) Stream draft replies token-by-token to the frontend and create a 10-ticket evaluation benchmark reporting triage accuracy.
- **Acceptance Criteria:**
  - [ ] Streaming SSE endpoint or accuracy script implemented if time permits.
