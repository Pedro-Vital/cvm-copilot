# Client brief — Ipê Capital

## The client

**Ipê Capital** is an independent equity research firm based in São Paulo with ~40 analysts. They sell deep equity research to institutional clients (fundos de investimento, gestoras, fundos de pensão) under annual subscriptions (R$300 mil – R$3 milhões+ per client), plus custom commissioned research and analyst calls.

They don't manage money themselves. Their product is research and access to their analysts.

## How Ipê Capital makes money

- Analysts each cover ~15 B3-listed companies in a specific industry (mineração, bancos, energia, bens de capital, etc.)
- They produce written research reports, financial models, and stock-level recommendations
- Asset-management clients pay for the reports and for the right to call the analyst with questions
- Reputation is everything — a single bad call dents the franchise

## How they add value

- Their clients (gestores de fundos) don't have the bandwidth to read every DFP, earnings call transcript, and industry filing for the companies they invest in
- Ipê Capital's analysts have already done that reading and turned it into actionable summaries
- The value is *condensation*: turning hundreds of pages of demonstrações financeiras into a one-page thesis the gestor can act on

## The problem

Every Ipê Capital analyst spends roughly **half of every week** doing source-document intake — opening DFPs, scanning the notas explicativas for the sections they care about (receita por segmento, provisões, resultado financeiro), copy-pasting passages, comparing exercício atual vs. anterior. Only after that intake work can they produce any original analysis.

The intake work is:

- Boring
- Necessary (you can't analyze what you haven't read)
- Repetitive across analysts (multiple analysts read the same Vale DFP every temporada de resultados)
- The biggest single drag on analyst output

Hiring more analysts doesn't fix it — the intake bottleneck scales linearly with coverage. They want to fix the bottleneck.

## What they want

An internal chatbot — call it **CVM Copilot** — where any Ipê Capital analyst can:

- Ask questions in plain Portuguese about any filing in Ipê Capital's curated corpus
- Get a sourced answer that cites the specific filing and the specific page
- Trust the answer enough to base downstream analysis on it
- Use it from a browser, logged in with their Ipê Capital email address
- See their own past conversations

## Example analyst questions

The current sample corpus contains **DFP** (Demonstrações Financeiras Padronizadas) filings for Vale, Petrobras, Itaú Unibanco, Banco do Brasil, and WEG across fiscal years 2021–2025. The bot should be able to handle questions like these with cited answers and underlying passages:

1. Como evoluiu a receita líquida da Vale por segmento (minério de ferro, níquel, cobre etc.) entre 2021 e 2025, segundo as notas explicativas das DFPs?
2. Para a Petrobras, como se compararam a margem EBITDA e o lucro líquido entre 2021 e 2025, e quais fatores as notas explicativas apontam como principais responsáveis pelas variações?
3. Como evoluíram a carteira de crédito e a inadimplência (PDD) do Itaú Unibanco e do Banco do Brasil entre 2021 e 2025, conforme divulgado nas notas explicativas das DFPs?
4. Quais foram os principais itens de despesas operacionais da WEG entre 2021 e 2025, e como cresceram em relação à receita líquida no mesmo período?
5. Compare o CAPEX e os investimentos divulgados nas demonstrações de fluxo de caixa da Vale e da Petrobras entre 2021 e 2025 — o que isso sugere sobre o ritmo de investimento de cada uma?
6. Para o Banco do Brasil, como evoluíram o patrimônio líquido e os dividendos/JCP distribuídos, segundo a DMPL, entre 2021 e 2025?
7. Quais contingências e provisões (cíveis, tributárias, trabalhistas) a Petrobras divulgou em suas notas explicativas entre 2021 e 2025, e como o valor total provisionado mudou?
8. Para a Vale, como as notas explicativas descreveram operações com partes relacionadas e instrumentos financeiros derivativos entre 2021 e 2025?
9. Para cada uma das cinco empresas, resuma a composição do resultado financeiro (receitas e despesas financeiras) na DRE mais recente e identifique mudanças relevantes em relação ao exercício anterior.
10. Se um analista perguntar se as DFPs comprovam que a WEG melhorou sua eficiência operacional entre 2021 e 2025, quais evidências existem no corpus, e onde o assistente deve se recusar a inferir além do que está nas demonstrações?

Note: these are deliberately scoped to what a DFP actually contains — standardized financial statements and notas explicativas. Narrative questions about strategy, risk-factor language, or competitive positioning belong to the Formulário de Referência (FRE), which is out of scope for this version of the corpus (see the FRE note in the constraints below).

## What "trust" means here

This is a research firm. Their entire business is being right. The bot must:

- **Never invent facts.** If the answer isn't in the corpus, it says so.
- **Always cite.** Every claim links to the source filing + page.
- **Show the underlying passage** so the analyst can verify in one click.

A wrong but confident answer is worse than no answer. Hallucinations kill the product.

## Constraints

- Corpus: **DFP filings** for a curated set of B3-listed companies, 2021–2025. The **Formulário de Referência (FRE)** — which carries the narrative business/risk-factor/MD&A-style content — is explicitly out of scope for this version; it's a candidate for a future corpus expansion, not this one.
- Source: CVM (dados públicos, `dados.cvm.gov.br` and CVM's filing-search system)
- Users: ~40 Ipê Capital analysts, plus a few sócios
- Login: Ipê Capital email addresses (no SSO required)
- Hosting: must run on a small/medium cloud footprint; Ipê Capital has no infra team

## Out of scope (explicitly)

- Trading recommendations or stock picks
- External data sources (no news, no social, no alternative data)
- Anything generating analysis not grounded in the corpus
- Multi-tenant / multi-client. This is Ipê Capital-internal only.
- Billing, plans, paywalls
- Mobile app
- ITR (quarterly filings) and FRE (narrative annual filing) — deferred to a later version once DFP-only retrieval quality is validated

## Definition of done

The analyst pilot group (5 senior analysts) tries it for a week and reports it saves them at least 3 hours per analyst per week. If yes, Ipê Capital rolls it out firm-wide.
