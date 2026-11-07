# Slide Outline (maximum 12 slides)

**Owner:** Partner 3. Contributions: Partner 1 (slides 3, 4, 6), Partner 2 (slide 5 screenshots).
**Final file:** `presentation/final_pitch.pdf` (PDF or PPTX accepted by the judges; maximum 12 slides).
**Time:** 5 minutes total, including the live demo. That is about 25 seconds per slide, so keep text minimal.

The judging guide lists **nine mandatory topics** (marked ★ below with the guide's numbering). All nine must be present. Slides 3, 5 and 12 are additions that support the RAG technical score (30 points) and the evaluation tie-breaker.

| # | Slide | Mandatory topic | Required content and evidence | Owner | TODO |
|---|---|---|---|---|---|
| 1 | Problem | ★1 Problem & its size | Who suffers, how; ONE sourced statistic; "625-page Arabic catalog" fact | P3 | Source the statistic |
| 2 | Solution & RAG architecture | ★2 Solution & RAG architecture | Simple pipeline diagram: PDFs → chunks → multilingual embeddings → FAISS → retrieval → LLM with citations → UI. Why RAG instead of a plain chatbot | P1 + P3 | Draw from `docs/ARCHITECTURE.md` §1 |
| 3 | What makes our RAG trustworthy | (supports criterion 1) | Page-exact citations, two-layer refusal, version conflict (158 vs 138), RTL number-reversal bug we caught with golden checks | P1 | Keep to 3 bullets + 1 visual |
| 4 | Live demo | ★3 Practical demo | Screenshots or video link; example questions and answers with their source | P2 + P3 | Screenshots of the 3 demo questions |
| 5 | Evaluation | (supports criterion 1, evaluation item + tie-breaker) | ≥ 10 questions, Precision@K, Hit@K, refusal accuracy, faithfulness; one failure and its fix | P3 + P1 | Copy numbers only from the saved report |
| 6 | Market analysis | ★4 Market analysis | TAM / SAM / SOM with sources and formulas | P3 | |
| 7 | Revenue model & pricing | ★5 Revenue model & pricing | Who pays, how much, unit economics (CAC, LTV, margin) — estimates labeled | P3 | |
| 8 | Costs & financial projections | ★6 Costs & projections | Operating cost per month (API cost per answer measured), 12–36 month projection, break-even | P3 | |
| 9 | Marketing plan | ★7 Marketing plan | Persona, channels, approximate budget, KPIs, 90-day plan | P3 | |
| 10 | Competitors & differentiation | ★8 Competitors & differentiation | Alternatives table (catalog, advisors, WhatsApp groups, general chatbots) and our advantage | P3 | |
| 11 | Team & next steps | ★9 Team & next steps | Roles (P1 RAG, P2 full-stack, P3 QA & business) and what happens after the hackathon; the ask (pilot) | all | |
| 12 | Thank you / Q&A | — | Repo link, QR code to the demo, one-line message | P2 | Optional; drop it if you run out of time |

## Design rules

- Same template throughout, large fonts, at most ~25 words per slide except tables.
- Every number on slides 1 and 6–9 carries a small source line or the word "Assumption".
- English slides; Arabic only inside demo screenshots.
- Rehearse with a stopwatch: stop at 5:00.
