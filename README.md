# CVM Copilot

An internal AI chatbot that lets analysts query a corpus of documents in plain English (or Portuguese) and get sourced, citable answers.

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
| Hosting            | Railway                                              |
| LLM + embeddings   | OpenAI                                               |

## Repo layout

```text
cvm-copilot/
├── CLAUDE.md           # agent instructions (read first)
├── README.md           # this file
├── data/               # local corpus + manifest (payloads gitignored)
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

To be added during the build. Setup guides:

- [Supabase](docs/guides/supabase-setup.md) — account, hosted project (dashboard or CLI)
- [Backend](docs/guides/backend-setup.md)
- [Frontend](docs/guides/frontend-setup.md)

## Sample CVM data

Unlike SEC EDGAR, CVM doesn't expose a simple per-filing API to script against, so the sample
corpus is built by manual download instead of a crawler:

1. Pick a small set of B3-listed companies and fiscal years (e.g. VALE3, PETR4, ITUB4, BBAS3,
   WEGE3 for 2021–2025).
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
         "numero_protocolo": "...",
         "local_path": "2024/vale3_dfp_2024-12-31.pdf",
         "source_url": "..."
       }
     ]
   }
   ```

   `codigo_cvm` is the company's permanent CVM identifier (stable across years, like a US CIK).
   `numero_protocolo` identifies this specific filed document — use it as the uniqueness key for
   ingestion, the same role `accession_number` plays for SEC filings.

4. Convert downloaded PDFs to Markdown:

   ```bash
   uv run data/convert_to_markdown.py
   ```

   This calls Docling's `DocumentConverter` directly on each PDF (the same library and API used
   for HTML in the original project — no separate PDF toolchain needed) and writes normalized
   Markdown plus a converted `manifest.json` under `data/markdown/`.

Downloaded files are gitignored; the `data/` folder itself stays in git for notes and the
manifest schema.
