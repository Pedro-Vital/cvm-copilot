# CVM Copilot

An internal AI chatbot that lets analysts query a corpus of documents in plain English (or Portuguese) and get sourced, citable answers.

> 🇧🇷 This project is an independent adaptation of
> [Document Copilot](https://github.com/daveebbelaar/document-copilot), originally built around
> SEC filings. This version adapts the concept to the Brazilian
> context, using CVM DFP filings as its initial corpus.

## The client

**Ipê Capital** — fictional independent investment research firm based in São Paulo. Their analysts spend half their week reading DFPs (Demonstrações Financeiras Padronizadas) before they can produce any original analysis. CVM Copilot eats that intake work so they can skip straight to insight.

Full brief: [docs/client-brief.md](docs/client-brief.md)

## Stack

| Layer              | Choice                                               |
| ------------------ | ---------------------------------------------------- |
| Backend            | Python + FastAPI                                     |
| Frontend           | Vite + React SPA + TypeScript                        |
| Database           | Supabase Postgres (users, chats, documents, chunks)  |
| Migrations         | SQLAlchemy models + Alembic                          |
| Retrieval          | Supabase `pgvector` + Postgres full-text search      |
| Auth               | Supabase Auth (email only)                           |
| LLM + embeddings   | OpenAI                                               |

## Repo layout

```text
cvm-copilot/
├── CLAUDE.md           # agent instructions (read first)
├── README.md           # this file
├── data/               # local corpus + manifest
├── docs/
│   └── client-brief.md # the client one-pager
├── backend/            # FastAPI service
└── frontend/           # React SPA (Vite)
```

## Prerequisites

Install these before setting up `backend/` or `frontend/`:

| Tool | Version | Used for | Install |
| ---- | ------- | -------- | ------- |
| [Python](https://www.python.org/downloads/) | 3.12+ | Backend runtime | OS package manager or python.org |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | latest | Backend deps + `data/convert_to_markdown.py` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| [Node.js](https://nodejs.org/) | 20+ (LTS) | Frontend toolchain | nodejs.org or `nvm install --lts` |
| [pnpm](https://pnpm.io/installation) | latest | Frontend package manager | `corepack enable && corepack prepare pnpm@latest --activate` |

You also need accounts/keys for external services once the app is wired up. Start with [docs/guides/supabase-setup.md](docs/guides/supabase-setup.md) (account + project), then create an [OpenAI API key](https://platform.openai.com/api-keys) when the LLM layer is wired up.

## Running locally

You need a Supabase project ([guide](docs/guides/supabase-setup.md)) and an OpenAI API key.
The backend and frontend each run in their own terminal.

**1. Backend env** — copy the template and fill in Supabase (Dashboard → Project Settings →
API / Database) and OpenAI values:

```bash
cd backend
uv sync
cp .env.example .env
```

| Variable | Notes |
| -------- | ----- |
| `SUPABASE_URL`, `SUPABASE_ANON_KEY` | Project Settings → API |
| `SUPABASE_SERVICE_ROLE_KEY` | Project Settings → API. Backend only — never put it in the frontend |
| `DATABASE_URL` | The **direct** connection (`db.<ref>.supabase.co:5432`), not the pooler. URL-encode the password |
| `OPENAI_API_KEY` | Chat model + embeddings |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins; `http://localhost:5173` for local dev |
| `LOG_LEVEL` | Optional. `INFO` by default |

**2. Database schema** (first run, and after pulling new migrations):

```bash
cd backend
uv run alembic upgrade head
```

**3. Corpus** — download the prepared corpus (the DFP PDFs and their finished Docling
conversion) from the [shared Google Drive folder][corpus-drive] and put its two folders at
`data/downloads/` and `data/markdown/`. That skips the manual CVM download and the slow
conversion. Then load it into Supabase once:

```bash
cd backend
uv run python -m ingest.load_corpus   # chunks + embeds (OpenAI) the 25 filings
```

Without it every answer comes back as "evidência insuficiente". See
[Loading and updating the corpus](#loading-and-updating-the-corpus) for how the corpus is built.

**4. Run the backend** (http://localhost:8000):

```bash
cd backend
uv run uvicorn app.main:app --reload
curl http://localhost:8000/health   # {"status":"ok"}
```

**5. Frontend env + run** (http://localhost:5173):

```bash
cd frontend
pnpm install
cp .env.example .env   # VITE_API_BASE_URL=http://localhost:8000, VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY
pnpm dev
```

Open http://localhost:5173, sign up with an email, and ask one of the
[example questions](docs/client-brief.md#example-analyst-questions).

**Checks:**

```bash
cd backend && uv run pytest -m "not integration" && uv run ruff check .
cd frontend && pnpm tsc --noEmit && pnpm lint
cd backend && uv run python -m scripts.smoke_assistant 1 10   # live agent against the real corpus (costs OpenAI tokens)
```

More detail: [Supabase](docs/guides/supabase-setup.md) · [Backend](docs/guides/backend-setup.md) ·
[Frontend](docs/guides/frontend-setup.md)

### Logs

The backend logs one structured event per step of a chat turn. Every event from the same turn
shares a `turn_id` (the assistant message id), so you can pull up one failed answer end to end:

| Event | When |
| ----- | ---- |
| `turn_started` | Question received (`thread_id`, `user_id`, `history_messages`) |
| `agent_tool` | Each `search_filings` / `read_*` call (`results`, `duration_ms`) |
| `grounding_rejected` | A draft answer's citations failed validation and went back to the model (`attempt`, `errors`) |
| `agent_run_done` | Validated answer (`requests`, `tool_calls`, tokens, `citations`, `duration_ms`) |
| `turn_done` | Stream finished (`first_text_ms` = wait before answer text appears, `duration_ms`) |
| `grounding_failed` / `agent_usage_limit_exceeded` / `retrieval_failed` / `agent_run_failed` | The turn failed closed; the analyst saw an error |

## Loading and updating the corpus

The corpus pipeline has three one-off steps, all run from the repo root. Each step is
idempotent, so re-running after adding filings only processes the new ones.

> **Just running the project?** Skip steps 1–2: the [shared Google Drive folder][corpus-drive]
> has `downloads/` (the 25 DFP PDFs) and `markdown/` (the complete Docling
> conversion). Copy both into `data/` and go straight to step 3.

[corpus-drive]: https://drive.google.com/drive/folders/18Ul21h84S0D7eADyeVtZS5mc79YI8lwc?usp=sharing

1. **Download** — the DFP PDFs are downloaded by hand into `data/downloads/<year>/` and
   recorded in `data/downloads/manifest.json` (see [Sample CVM data](#sample-cvm-data)).
2. **Convert** — Docling turns each PDF into Markdown + a DoclingDocument JSON under
   `data/markdown/` (slow: minutes per filing on CPU; a GPU helps):

   ```bash
   uv run --project backend data/convert_to_markdown.py
   ```

3. **Load** — chunk, embed (OpenAI), and write `source_documents` + `document_chunks` to
   whatever database `backend/.env` points at:

   ```bash
   cd backend
   uv run python -m ingest.load_corpus
   ```

   Filings are keyed on `ticker + fiscal_year + form`. Already-loaded filings are skipped;
   a filing left half-loaded by a crashed run (a document row with no chunks) is deleted and
   redone.

**Adding a filing** (e.g. a new fiscal year): download the PDF, add its manifest entry, then
re-run steps 2 and 3.

**Replacing a filing** (e.g. a corrected conversion): the loader won't overwrite an existing
filing. Delete its `source_documents` row in Supabase first, then re-run step 3. The delete
cascades to its chunks *and* to the `message_citations` rows that point at them: past answers
still show their citation chips and quoted excerpts (those live in the stored message), but
opening the source panel for them returns "not found".

## Sample CVM data

Unlike SEC EDGAR, CVM doesn't expose a simple per-filing API to script against, so the sample
corpus is built by manual download instead of a crawler (to skip all of this, use the
[prepared corpus][corpus-drive]):

1. Pick a small set of B3-listed companies and fiscal years — this project's sample set is
   ITUB4 (Itaú Unibanco), MGLU3 (Magazine Luiza), SUZB3 (Suzano), VALE3 (Vale), and WEGE3 (WEG)
   for 2021–2025.
2. For each company-year, download the filed **DFP** PDF from CVM's filing-search system (search
   by company name or CNPJ, filter to DFP, pick the fiscal year) into `data/downloads/<year>/`.
3. Record each filing in `data/downloads/manifest.json`, following this shape:

   ```json
   {
     "source": "CVM",
     "form": "DFP",
     "filings": [
       {
         "ticker": "VALE3",
         "cnpj": "33.592.510/0001-54",
         "company_name": "Vale S.A.",
         "codigo_cvm": "4170",
         "form": "DFP",
         "reference_period": "2024-12-31",
         "fiscal_year": 2024,
         "local_path": "2024/vale3_dfp_2024-12-31.pdf",
         "source_url": "..."
       }
     ]
   }
   ```

   `codigo_cvm` is the company's permanent CVM identifier (stable across years, like a US CIK).
   For this fixed corpus, `ticker + fiscal_year` is unique, so that pair is the ingestion
   dedup key. CVM also assigns a `numero_protocolo` to each individual submission (the same
   role `accession_number` plays for SEC filings), but it's left out of this version — pulling
   it requires a manual per-filing lookup on CVM's site. It's worth adding back in a future
   version, since it becomes the only reliable per-version key once *retificações* (restated
   DFP resubmissions) enter the corpus.

4. Convert downloaded PDFs to Markdown:

   ```bash
   uv run --project backend data/convert_to_markdown.py
   ```

   This calls Docling's `DocumentConverter` directly on each PDF (the same library and API used
   for HTML in the original project — no separate PDF toolchain needed) and writes normalized
   Markdown plus a converted `manifest.json` under `data/markdown/`.

Downloaded files are gitignored; the `data/` folder itself stays in git for notes and the
manifest schema.
