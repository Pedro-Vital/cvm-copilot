# CVM Copilot — implementation checklist

Work top to bottom. Each phase unlocks the next. Check items off as you go.

## Where to start: backend, frontend, or both?

**Start with foundation, then backend-led vertical slices.**

| Order | Why |
| ----- | --- |
| 1. Supabase + sample corpus | Everything persists here; you need a project and a DFP corpus to test against. |
| 2. Backend schema + migrations | Auth, chat, retrieval, and citations all depend on the data model. |
| 3. Thin vertical slices | Wire auth, then a stubbed chat stream, then real RAG — each slice touches frontend + backend together. |
| 4. Frontend in parallel (lightly) | Scaffold the SPA early, but don't build citation UI or chat polish until the backend can return real grounded answers. |

The critical path is **data model → ingestion → retrieval → LLM → citations**. The frontend is mostly a streaming chat shell with auth and citation display — it shouldn't get far ahead of working APIs.

---

## Phase 0 — Prerequisites & foundation

- [ ] Install toolchain: Python 3.12+, `uv`, Node 20+, `pnpm` (see [README](../README.md))
- [ ] Create Supabase project and collect credentials ([supabase-setup](guides/supabase-setup.md))
- [ ] Create OpenAI API key (needed from Phase 6 onward)
- [x] Pick the sample company set (ITUB4, MGLU3, SUZB3, VALE3, WEGE3, fiscal years 2021–2025) and manually download each DFP PDF from CVM's filing-search system into `data/downloads/<year>/` (see [README §Sample CVM data](../README.md#sample-cvm-data) — there is no `download.py`; CVM has no scriptable per-filing API and its search is reCAPTCHA-gated)
- [x] Record each filing in `data/downloads/manifest.json` (`ticker`, `cnpj`, `company_name`, `codigo_cvm`, `form`, `reference_period`, `fiscal_year`, `local_path`, `source_url`)
- [x] Confirm `data/downloads/manifest.json` lists all 25 filings (5 companies × 5 years) with real `source_url` values (no `FIXME_*` left)

---

## Phase 1 — Backend scaffold & database

Goal: a running FastAPI service with a migrated Supabase schema.

- [ ] Init backend deps and project layout ([backend-setup](guides/backend-setup.md))
- [ ] `app/config.py` — settings module, fail fast on missing env vars
- [ ] `app/main.py` — FastAPI app, CORS, health check (`GET /health`)
- [ ] SQLAlchemy models in `app/database/models.py`:
  - [ ] `profiles`
  - [ ] `source_documents`
  - [ ] `document_chunks` (embedding + generated `tsvector`)
  - [ ] `chat_threads`
  - [ ] `chat_messages`
  - [ ] `message_citations`
- [ ] Alembic init + first migration:
  - [ ] `create extension if not exists vector`
  - [ ] `vector(1536)` embedding column
  - [ ] generated `tsvector` column on chunks, using the `portuguese` text search configuration
  - [ ] HNSW index (vector) + GIN index (full-text)
  - [ ] RLS policies (analysts see only their own chats)
- [ ] `uv run alembic upgrade head` against Supabase direct connection (not the pooler URL)
- [ ] `app/database/supabase.py` — user-scoped and service-role clients
- [ ] Verify: `uv run uvicorn app.main:app --reload` → health check returns 200

---

## Phase 2 — Auth (full stack)

Goal: Ipê Capital analysts can sign in with their firm email; backend rejects unauthenticated requests.

**Backend**

- [ ] `app/auth/dependencies.py` — verify `Authorization: Bearer <supabase_jwt>`, expose `get_current_user`
- [ ] Reject missing/expired tokens with `401` before any chat or retrieval work

**Frontend**

- [ ] Scaffold Vite + React + TypeScript + Tailwind + shadcn ([frontend-setup](guides/frontend-setup.md))
- [ ] `src/lib/env.ts` — validate `VITE_API_BASE_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`
- [ ] `src/lib/supabase.ts` — browser Supabase client
- [ ] `src/lib/http.ts` + `src/lib/api.ts` — fetch wrapper with automatic bearer token
- [ ] Sign-in / sign-up pages (email only, no SSO)
- [ ] Protected routes — redirect unauthenticated users to login
- [ ] Verify: sign up, sign in, token reaches backend on a test authenticated endpoint

---

## Phase 3 — Chat shell (vertical slice, stubbed)

Goal: end-to-end chat UI streaming from FastAPI, no real retrieval yet.

**Backend**

- [ ] Chat thread CRUD: list threads, create thread, load message history
- [ ] `POST /chat/stream` — accepts AI SDK message format, streams a stubbed assistant reply
- [ ] Persist user + assistant messages to `chat_messages` after stream completes
- [ ] `403` when user accesses another user's thread

**Frontend**

- [ ] React Router: login, chat list, chat thread routes
- [ ] AI SDK chat primitives pointed at `POST /chat/stream` with Supabase bearer token
- [ ] Thread sidebar (past conversations)
- [ ] Basic message list + input + streaming indicator
- [ ] Verify: create thread, send message, see streamed stub response, reload and see history

---

## Phase 4 — Ingestion pipeline

Goal: the CVM DFP corpus is parsed, chunked, embedded, and stored in Supabase.

- [ ] `data/convert_to_markdown.py` — Docling `DocumentConverter` over each downloaded DFP PDF → normalized Markdown + converted manifest under `data/markdown/`
- [ ] `ingest/` scripts (or CLI entrypoint) for one-off corpus loading into Supabase
- [ ] Chunking strategy (size + overlap; store chunk index, page, section, ticker, `codigo_cvm`, form, fiscal year)
- [ ] Write `source_documents` rows with filing metadata from `manifest.json`
- [ ] Write `document_chunks` rows with text + metadata
- [ ] OpenAI embedding generation → store `vector(1536)` per chunk
- [ ] Generated `tsvector` (`portuguese` config) populated for full-text search
- [ ] Idempotent re-run (skip already-ingested documents, keyed on `ticker` + `fiscal_year` + `form` — this fixed corpus has one filing per key; a future version handling *retificações* would need CVM's `numero_protocolo` instead, since that's the only reliable per-version key)
- [ ] Unit tests: chunking logic, metadata extraction
- [ ] Run ingestion on full sample corpus (25 filings × 5 companies)
- [ ] Verify: chunks exist in Supabase; spot-check a known passage (e.g. Vale's receita por segmento table)

---

## Phase 5 — Retrieval

Goal: an analyst question returns ranked, relevant source passages.

- [ ] `retrieval/queries.py` — pgvector semantic search over `document_chunks`
- [ ] `retrieval/queries.py` — Postgres full-text search over `search_vector` (`portuguese` config)
- [ ] `retrieval/fusion.py` — Reciprocal Rank Fusion in Python
- [ ] `retrieval/retriever.py` — query → fused ranked passages + neighbor chunks
- [ ] Unit tests: fusion ranking, query assembly (mock DB)
- [ ] Integration test (optional, `@pytest.mark.integration`): real query against ingested corpus
- [ ] Verify: test queries from [client-brief](client-brief.md#example-analyst-questions) return relevant chunks (manual or scripted)

---

## Phase 6 — LLM agent & grounding

Goal: grounded answers with enforced citations — the core product contract.

- [ ] `assistant/instructions.md` — product contract (cite everything, refuse to invent, no stock picks, answer in Portuguese by default)
- [ ] PydanticAI agent with typed deps (`DocumentAgentDeps`) and output (`GroundedAnswer`)
- [ ] Agent tools: `search_filings`, `read_chunk`, `read_surrounding_chunks`
- [ ] `chat/orchestrator.py` — one turn: retrieve → agent → validate → stream → persist
- [ ] `grounding/validator.py` — every citation maps to a retrieved passage; fail closed on violation
- [ ] `chat/streaming.py` — AI SDK-compatible stream (text deltas + citation metadata parts)
- [ ] Persist `message_citations` linked to assistant messages
- [ ] Unit tests: citation validation, grounding enforcement, message conversion
- [ ] Verify against [client-brief example questions](client-brief.md#example-analyst-questions):
  - [ ] Answers cite specific filings and pages
  - [ ] Under-specified questions get an "evidência insuficiente" (not-enough-evidence) response
  - [ ] Question 10 (WEG operational efficiency) refuses to infer beyond what the DFPs state

---

## Phase 7 — Trust UI (citations & source passages)

Goal: analysts can verify every claim in one click — this is what makes the product usable.

- [ ] Citation chips/links on assistant messages (company, filing type, fiscal year, page/section)
- [ ] Source passage panel — show underlying excerpt for selected citation
- [ ] Empty states (no threads, no corpus match)
- [ ] Error states (auth expired, retrieval failure, grounding failure, network/CORS)
- [ ] Loading/streaming status during assistant run
- [ ] Verify: click a citation → see the exact passage from the DFP

---

## Phase 8 — Pilot readiness

Goal: 5 senior analysts can use it for a week and report ≥3 hours saved per analyst per week.

- [ ] README "Running locally" section — copy-paste commands for backend + frontend + env vars
- [ ] Seed or document how to ingest/update the corpus
- [ ] Smoke-test all 10 example questions from the client brief
- [ ] Confirm chat history persists across sessions
- [ ] Confirm ~40-analyst scale assumptions (no hardcoded single-user shortcuts)
- [ ] Basic structured logging on backend (`structlog`) for debugging failed turns
- [ ] Review latency: streaming starts within a few seconds for typical queries

---

## Phase 9 — Deployment (Railway)

- [ ] Railway: backend service (Uvicorn, env vars, `ALLOWED_ORIGINS`)
- [ ] Railway: frontend service (Vite build, `VITE_*` env vars at build time)
- [ ] Supabase: re-enable email confirmation for production if disabled during dev
- [ ] Run `alembic upgrade head` against production Supabase (direct connection)
- [ ] Run ingestion against production database
- [ ] End-to-end test on deployed URLs with a real Ipê Capital-style email account

---

## Quick reference

| Doc | Purpose |
| --- | ------- |
| [client-brief.md](client-brief.md) | What Ipê Capital needs and example analyst questions |
| [architecture.md](architecture.md) | System design, data model, streaming contract |
| [guides/supabase-setup.md](guides/supabase-setup.md) | Hosted Postgres + Auth |
| [guides/backend-setup.md](guides/backend-setup.md) | FastAPI + Alembic commands |
| [guides/frontend-setup.md](guides/frontend-setup.md) | Vite + React scaffold commands |
