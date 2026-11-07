# Business Plan

**Owner:** Partner 3.

> **Judging rule:** numbers, percentages and statistics must cite their source. Personal estimates are accepted only when labeled as assumptions. **Invented numbers lose 3–5 points** (judging guide, penalties section). In this file, every number is either `[Source: link, date accessed]` or `ASSUMPTION A#`.

Judging weight: Business plan & numbers = 15 points (market 5, revenue model & pricing 5, costs & projections 5).

## 1. Problem statement

TODO(PARTNER 3):
1. One sentence that names who suffers and how. Draft to adapt: *"Students lose time searching long Arabic PDFs (the 2024–2025 undergraduate catalog alone is 625 pages) for prerequisites and graduation rules, and academic departments answer the same questions every semester."* The 625 pages is a fact from our own data; cite it as such.
2. Add ONE external number that proves the size of the pain, with a source. Candidates to look for:
   - Number of undergraduate students at Birzeit University (university facts page / annual report).
   - Number of students in Palestinian higher education (Ministry of Higher Education statistical yearbook; Palestinian Central Bureau of Statistics, PCBS).
   - Advisor-to-student ratio, or how often students delay graduation because of registration mistakes (only if you find a credible source).
3. Optional primary evidence (allowed if honest): a 5-minute poll of students at the hackathon ("How long did you last spend finding a prerequisite?"). Report it as "informal poll, n = X, [date]".

## 2. Target users

TODO(PARTNER 3):
- Primary user: undergraduate students (start with Computer Engineering, then the rest of the faculty).
- Secondary users: academic advisors and department secretaries, who answer repeated questions.
- Buyer (who pays): the university (Deanship of Student Affairs / Registrar / IT). Students use it for free.

## 3. Value proposition

TODO(PARTNER 3): fill the template.
- For **[students]** who **[need fast, correct answers about plans and rules]**, Smart Academic Advisor is **[a bilingual assistant]** that **[answers in seconds with the exact document and page]**. Unlike **[reading the catalog or waiting for an advisor]**, it **[never guesses: it refuses when the documents do not contain the answer]**.
- Why RAG and not just an LLM (judging criterion 2, 5 points): a general chatbot does not know Birzeit's 2026 plan, invents credit hours, and cannot cite pages. Keyword search fails on Arabic morphology, Arabic–English mixing and colloquial questions.

## 4. Existing alternatives

TODO(PARTNER 3): table, honest strengths and weaknesses.

| Alternative | Strength | Weakness |
|---|---|---|
| Reading the PDF catalog | Official | 625 pages, Arabic only, slow, version confusion |
| Academic advisor / department office | Personal, authoritative | Office hours, queues at registration time |
| Student WhatsApp/Facebook groups | Fast | Often outdated or wrong, no source |
| General chatbots (e.g. ChatGPT) | Fluent | No access to current university documents; may hallucinate |
| University website search | Official | Keyword-only, no direct answers |

## 5. Competitive differentiation

TODO(PARTNER 3): 3 bullets max — verifiable citations (document + page), explicit refusal, Arabic/English/colloquial support, handles document versions (138 vs 158 credit hours example).

## 6. Market size (TAM / SAM / SOM)

TODO(PARTNER 3): define each level as a NUMBER OF STUDENTS or UNIVERSITIES first, then multiply by price. Show the formula on the slide.

| Level | Definition (example) | Number | Source / assumption | Value / year |
|---|---|---|---|---|
| TAM | All university students in Palestine (or a wider Arabic-speaking region, if sourced) | TODO | [Source] | TODO |
| SAM | Students at universities whose documents are mainly PDF-based in Arabic + English (first: Palestinian universities) | TODO | [Source] or ASSUMPTION | TODO |
| SOM | Birzeit + 1–2 more universities in 3 years | TODO | ASSUMPTION | TODO |

## 7. Revenue model and pricing

TODO(PARTNER 3):
- Model to evaluate: B2B annual license per university, priced per enrolled student per year, with a free pilot semester. Optionally a setup fee for document onboarding.
- Pricing must be justified: compare with (a) the cost of advisor/staff hours saved (ASSUMPTION: hours saved per semester × staff hourly cost [source for the salary level]) and (b) the price of other student-facing software, if you can find a public price.
- Unit economics (the guide asks for CAC, LTV and margin, "even as a declared estimate"):

| Metric | Formula | Value | Basis |
|---|---|---|---|
| Price per university / year | students × price per student | TODO | ASSUMPTION A1 |
| Gross margin | (revenue − LLM/API − hosting) / revenue | TODO | from §8 |
| CAC (per university) | sales time + pilot cost | TODO | ASSUMPTION A2 |
| LTV | annual gross profit × expected years retained | TODO | ASSUMPTION A3 |
| LTV / CAC | | TODO | |

## 8. Operating costs

TODO(PARTNER 3, with Partner 1's measured token counts — see docs/ARCHITECTURE.md §6):

| Cost item | Basis | Monthly cost |
|---|---|---|
| LLM API | measured tokens per answer × provider price [pricing page + date] × ASSUMPTION questions per month | TODO |
| Embeddings | runs locally on the server (no per-call cost); re-index only when documents change | ~0 |
| Hosting | one small cloud VM [provider price page] | TODO |
| Team | ASSUMPTION: part-time maintainer(s) | TODO |
| Total | | TODO |

## 9. Financial projections (12–36 months) and break-even

TODO(PARTNER 3): a simple table by quarter or by year. State every assumption.

| Period | Universities | Students covered | Revenue | Costs | Profit | Cumulative |
|---|---|---|---|---|---|---|
| Months 1–12 | TODO | | | | | |
| Months 13–24 | TODO | | | | | |
| Months 25–36 | TODO | | | | | |

Break-even: TODO (month when cumulative profit ≥ 0).

## 10. Risks and assumptions

TODO(PARTNER 3): keep the list of ALL assumptions in one place so judges see them (judges' question 7: "What is the weakest assumption in your financial plan?" — name it yourselves).

| ID | Assumption | Why we believe it | How we will test it | Weakest? |
|---|---|---|---|---|
| A1 | Price per student per year | TODO | Pilot negotiation | |
| A2 | CAC per university | TODO | | |
| A3 | Retention years | TODO | | |
| A4 | Questions per student per month | TODO | Pilot usage logs | |

Risks: answer errors on official rules (mitigation: citations + refusal + "verify with the Registrar" note); documents out of date (mitigation: version metadata, re-index process); university procurement is slow (mitigation: free pilot, student-led adoption); LLM price changes (mitigation: provider-agnostic design).

## 11. Ask and next steps

TODO(PARTNER 3): what you ask from the judges/university (for example: a pilot with one department next semester and access to the official, current documents).
