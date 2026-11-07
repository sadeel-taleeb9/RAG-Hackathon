# Demo Script and Judge Q&A

**Owner:** Partner 3 (script, rehearsal, backup assets). Partner 2 runs the laptop. Partner 1 answers technical questions.

## Judging session format (from the judging guide)

- **10 minutes per team:** 5 presentation, 4 questions, 1 changeover.
- Each panel has a technical judge, a business/marketing judge, and preferably an industry judge. Each scores independently; the final score is the average.
- **Surprise test:** judges prepare 3 questions for the problem beforehand, **one of them out of scope**, and ask them directly to the live system. Expect an unfamiliar academic question.
- Going over time: warning, then the presentation is stopped.
- "Practical evidence" (3 points): the system must work on real questions and show the source. A recorded video counts as much as a live demo; having neither = 0.

## Before the session (checklist)

- [ ] Demo laptop: index built, embedding model already downloaded (works without internet for retrieval; the LLM still needs internet).
- [ ] `.env` on the demo laptop has `RAG_MODE=real` and a working key; spare key from a second provider written in a password manager (not in Git).
- [ ] Browser zoom 125%, dark/light mode readable on the projector, notifications off.
- [ ] Backup: 2–3 minute screen recording + screenshots (in `presentation/`), opened in a tab.
- [ ] Phone hotspot ready in case the venue Wi-Fi fails.

## Live demo (≈ 90 seconds inside the 5-minute pitch)

| # | Type | Question to type | What to point out |
|---|---|---|---|
| 1 | English, answer with source | How many credit hours are required to graduate in Computer Engineering? | 138, cites the 2026 study plan page 1; mention the old catalog says 158 → version handling |
| 2 | Arabic, table question | ما هو المتطلب السابق لمساق مشروع التخرج ENCS5300؟ | Arabic answer, RTL, course codes exact, source page 3 |
| 3 | Out of scope → refusal | How much is the tuition fee per credit hour? | Explicit refusal instead of a made-up number |

Recommended by the judging guide for the optional video: 3 real questions, one answered with a source and one out-of-scope question that is refused.

TODO(PARTNER 3): replace these with the three questions that worked best in the final evaluation run, and keep two spare questions.

## Judge question bank (from the judging guide) — prepared answers

| # | Question | Who answers | Prepared answer (fill in) |
|---|---|---|---|
| 1 | Why this chunking strategy? What happens if you change size or overlap? | P1 | Page-bounded, line-aware, ~900 chars; see `docs/ARCHITECTURE.md` §3. TODO: give a measured effect if you tried another size |
| 2 | Which embedding model and why? How does it handle Arabic? | P1 | multilingual-e5-small: Arabic + English, cross-lingual, CPU. TODO: one example of an English question matching an Arabic passage |
| 3 | What does the system do for something not in the documents? (live test) | P2 types, P1 explains | Threshold → refusal without LLM cost; LLM `INSUFFICIENT_EVIDENCE` as second layer |
| 4 | How did you measure quality? What is the worst question it failed and why? | P3 | Numbers from `docs/EVALUATION.md` §3; worst failure from §6 |
| 5 | How does the system handle conflicting or outdated information? | P1 | Version metadata in the manifest; 158 vs 138 example |
| 6 | How much does one answer cost? How does cost change at 10,000 users? | P3 | Measured tokens × price; refusals cost 0 LLM tokens. TODO numbers |
| 7 | Where did the market numbers come from? What is the weakest assumption in your financial plan? | P3 | Sources in the business plan; name the weakest assumption yourselves |
| 8 | What did you write yourselves and what did AI generate? Explain this part of the code. | each owner | Be honest and specific (see README "AI usage disclosure"); each partner can explain their own files |
| 9 | How do you protect sensitive data in the system? | P2 | Keys in `.env`, no student data indexed, escaped output, no question logging by default |
| 10 | Who are the first three customers you will contact after the competition, and what will you tell them? | P3 | From `docs/MARKETING_PLAN.md` §4 |

## If something breaks during the demo

| Problem | Say | Do |
|---|---|---|
| LLM API error / rate limit | "This is the technical-error path: it is reported as a system error, never as an answer." | Switch to the spare key, or play the backup video |
| Wi-Fi down | — | Phone hotspot; otherwise the backup video |
| Wrong answer | "Here is the cited page — this is why we show sources." Open the page. | Note it as a failure case for the evaluation slide |
