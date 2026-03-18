# Today's Prep Session (3-5 hours)

Target: Walk into the interview able to defend every resume line and hold your own on breadth.

---

## Hour 1: Resume Defense — Recommendation & RL (the two highest-risk areas)

- [ ] Read Q1-8 (Recommendation & Retrieval) out loud. Answer each without looking.
- [ ] Check answers. Star any where you blanked on a specific number or architecture detail.
- [ ] Re-do starred questions until you can hit: architecture → why this approach → training data → eval metric → failure modes → the 46% number and its caveats
- [ ] Read Q9-16 (LLM-as-Judge & RL) out loud. This is the vulnerable section.
- [ ] Nail the honest framing: "iterative supervised improvement with an LLM evaluator in the loop" — not classical RL, but effective and principled. Say it out loud 3 times.
- [ ] Be able to explain state/action/reward/policy without hesitation
- [ ] Be able to answer "was this real RL?" cleanly in under 60 seconds

**Done when**: You can explain the reco system end-to-end in 3 minutes AND give a crisp, honest answer about the RL framing without flinching.

---

## Hour 2: Resume Defense — Safety, Ranking, Infra (the proof-of-scale areas)

- [ ] Read Q17-22 (Safety & Monitoring) out loud. Answer each.
- [ ] Be able to name: what was filtered, how drift was defined, what triggered rollback, how CA/MX differed
- [ ] Read Q23-27 (Ranking & Search) out loud. Answer each.
- [ ] Memorize cold: +0.192 NDCG, 15-20 bps per launch, $100M+, 8 models, DistilBERT→BERT→GTE progression
- [ ] Be able to explain why offline NDCG gains don't always translate to online GMV
- [ ] Read Q28-30 (Infra & Synthego). Answer each.
- [ ] Have a clean 90-second answer for "what carries over from genomics to production ML"

**Done when**: Someone could ask you any of Q17-30 and you'd give a structured, specific answer with real numbers.

---

## Hour 3: Science Breadth — Core ML (the "are you a real scientist" test)

- [ ] Read all 20 science breadth questions. Mark the 5 you feel weakest on.
- [ ] For your 5 weakest: read the answer, close it, re-answer out loud. Repeat until solid.
- [ ] For the remaining 15: skim answers, confirm you could hit the key points
- [ ] Cold drill — answer these without looking:
  - [ ] "Compare logistic regression, GBTs, and neural nets for ranking" (Q1)
  - [ ] "Explain k-means from first principles, when does it fail" (Q2)
  - [ ] "Design an experiment to test LLM queries vs simpler heuristic" (Q4)
  - [ ] "What is calibration and how do you measure it" (Q7)

**Done when**: You could answer any science breadth question with theory + practical example + failure mode, not just a textbook definition.

---

## Hour 4: Leadership Principles — Build Your Story Bank

- [ ] Read all 16 LP questions
- [ ] For each one, confirm you have a real story (not a generic answer)
- [ ] Practice the top 6 most likely LPs out loud in STAR format:
  - [ ] Customer Obsession
  - [ ] Ownership
  - [ ] Dive Deep
  - [ ] Deliver Results
  - [ ] Have Backbone; Disagree and Commit
  - [ ] Invent and Simplify
- [ ] Each STAR story should be under 2 minutes spoken. Time yourself.
- [ ] Make sure you're using different projects across stories (not all reco system)

**Done when**: You have 6 distinct, timed STAR stories you can deliver without notes.

---

## Hour 5 (if time): Integration & Pressure Test

- [ ] Pick 3 random questions from across all sections. Answer cold, timed (2 min each).
- [ ] Practice one full "walk me through your most impactful project" answer (3 min max)
- [ ] Practice one "tell me about a time you failed" answer (2 min, STAR format)
- [ ] Review the Key Numbers table in README.md — can you recite all 9 numbers cold?
- [ ] Final pass: re-read any starred/weak questions from earlier hours

**Done when**: You feel like someone could throw any question at you and you'd have a structured starting point, not a blank stare.

---

## Emergency Cheat Sheet (if you only have 1 hour)

Focus on these 10 questions only — they cover the highest-risk areas:
1. Q1 (end-to-end reco architecture)
2. Q9 (what is RL with LLM-as-judge)
3. Q16 (is this real RL — the honest answer)
4. Q23 (why cross-encoders improved NDCG)
5. Q7 (what does 46% actually mean)
6. Science Q1 (compare LR vs GBT vs NN)
7. Science Q4 (experiment design)
8. LP: Customer Obsession
9. LP: Ownership
10. LP: Dive Deep
