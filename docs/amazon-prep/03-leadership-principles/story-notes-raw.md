# Raw Story Notes — Interactive Sessions

Working document. Will be refined into polished STAR stories.

---

## Story: Evaluation Framework (LLM Judge)

**Context:** Joined Walmart International Personalization team. No offline evaluation pipeline existed. Team was shipping models straight to A/B with only anecdotal evidence and sparse engagement summaries. Culture of diving deep and ownership did not exist.

**Consequences of no eval:**
- Consistent failures of model launches during A/B
- Underperforming heuristic baselines
- Underperforming third-party baseline models (embarrassing)
- At least 3 known failed launches before Nick joined, possibly more
- When there's no existing carousel and you ship something, of course it's GMV+ for an emerging market — but when you need to do v2 and have no idea how to evaluate, you're stuck

**What Nick built:**
- Immediately recognized as existential threat upon joining
- Created MVPs quickly (Bias for Action angle)
- Demoed to manager, who was immediately sold
- Required mandate from manager to get others to adopt
- Same LLM-as-judge architecture as RL work, but different rubrics per use case
- 6 rubrics for different carousel types (similar items, complementary items, user-item engagement, etc.)
- All validated against engagement data — scores monotonically predicted engagement rate
- Iterated and specialized rubrics (generic user-item rubric → specialized complementary items rubric)

**Interesting detail — strategic rubric decisions:**
- Complementary rubric rates similar/alternative items low even though users clicked on them
- This is a strategic decision — engagement is confounding, the goal of complementary carousel is complements, not alternatives
- Shows judgment about what "quality" means beyond raw engagement

**Post-framework results:**
- 4 main launches Nick was part of: Recommended For You (user embeddings), Intent-Based Recommendation, Continue Your Shopping, Arbitration Engine
- All models shipped post-evaluation framework were positive on A/B (no more surprises)

**Team adoption:**
- Teammates were not self-motivated to adopt; required mandate from manager
- Tempered framing: "The framework became the standard evaluation step before any A/B launch"

**Candidate LPs:** Highest Standards, Ownership, Bias for Action, Dive Deep

---

## Story: 10+ Model Architecture Comparison (User Embeddings)

**Context:** For user embedding personalized retrieval, team had only tested one architecture with no evaluation method.

**What Nick built:**
- 10+ model types: collaborative filtering, heuristic baseline, SASRec, ComiRec (DR and SA), and others
- Full hyperparameter sweeps
- Tables of empirical evaluation
- Golden dataset for comparison

**Outcome:**
- Showed that relevance, engagement, Pareto front optimization, and diversity are all axes to explore
- Demonstrated specialization of each model along these axes
- Dictated which candidates to advance to A/B

**Framing concern:** Don't want to highlight how immature the systems were or complain about lazy colleagues. Frame as "I believed we needed rigorous empirical comparison before committing to an architecture" — about YOUR standards.

**Winner:** ComiRec-SA — good retrieval for engaged items, good diversity.

**Embedding detail:** Each item had an embedding fed into ComiRec's attention head (user embedding is generated). Tested 5 sets of embeddings: pretrained text encoders, fine-tuned text encoders, image embeddings, and combinations. Text+image had highest possible performance but wasn't practical for runtime implementation. Interesting tradeoff story.

**Candidate LPs:** Highest Standards, Dive Deep, Deliver Results, Learn & Be Curious

---

## Story: End-to-End Observability (Dashboards, Drift, RCA)

**Context:** Nick's job is ML scientist — build new features. But realized you can't know what works without full observability.

**What Nick built:**
- Pre-flight evaluations with LLM judges (before A/B)
- ML drift dashboards (during production)
- Revenue dashboards to measure after product launched
- End-to-end: build → evaluate → launch → monitor → RCA

**What dashboards caught:**
- Drift in input data
- Step changes in model performance/revenue
- Changes across the board

**Candidate LPs:** Highest Standards, Ownership, Dive Deep, Deliver Results

---

## Story: Eval Viewer (Internal Model Comparison Tool)

**Context:** Price awareness miss on generative retrieval revealed that non-technical stakeholders (PMs) needed visibility into model outputs. Nick built a tool nobody asked for.

**What Nick built:**
- Internal web app: SQLite + FastAPI + React (built with coding agents in ~1 month)
- Side-by-side columns showing model 1 / model 2 / model 3 for same candidate item or user
- Included image data, prices, LLM judgments, engagement data
- Built it first for himself, then stood it up on internal endpoint for PM communication
- To pull new index data: kick off serverless Spark jobs for new items (no direct item image endpoint, only GCS)

**Candidate LPs:** Bias for Action, Ownership, Insist on Highest Standards

---

## Story: Embedding Pipeline Rescue

**Context:** A feature was about to launch (and did launch) on broken infrastructure. A data scientist was running embeddings out-of-band from a Jupyter notebook/script. Some embeddings were up to a month stale, others had no plan to ever be refreshed. Since no one was evaluating performance, no one cared.

**What Nick did:**
- Saw stale embeddings as existential threat
- Built proper pipeline: Airflow + Spark + PyTorch Lightning for GPU inference
- Nobody asked him to do this

**Candidate LPs:** Bias for Action, Ownership, Insist on Highest Standards

---

## Story: Post-A/B Metrics Dashboard (Kronos replacement)

**Context:** Post-A/B analysis was done through Adobe dashboards by analytics team. Dashboards were tabular only — no graphs, no way to cleanly view GMV lift for A/B tests over time. Frankly sucked.

**What Nick built:**
- Full metrics dashboard: revenue per customer, click-through rate broken down by step in user journey, module, etc.
- Filter by A/B experiment key for head-to-head comparison
- All data viewable, proper visualizations
- Built without being asked — this was normally analytics team's job

**Candidate LPs:** Bias for Action, Ownership, Invent & Simplify, Deliver Results

---

## Story: Arbitration Engine + Near/Far Intent Framework

**Context:** Nick owned arbitration engine on cart page and PAC page — meta-optimization balancing carousel ordering. Owned more than supposed to because of people quitting. Was in team scope but not under his capacity.

**Product insight — near/far intent:**
- User generates two intents: near (recent history) and far (total history creating persona — e.g. "price-conscious time-sensitive shopper")
- Near intent optimized for short-term engagement
- Far intent captures elements like brand preferences
- Both affinity scores crossed with carousel embeddings for ranking
- Same framework applied to intent-based generative retrieval:
  - Example: baby yoda t-shirt → near intent = shorts/socks for same size person; far intent = other Star Wars affiliated stuff
- Meta goal: keep users on app through a loop of diverse experiences, continually introducing diversity

**Nick created:** time scales of intent (near and far) concept + evaluation frameworks to test them

**Candidate LPs:** Ownership, GenAI Fluency, Dive Deep, Think Big

---

## Story: Built All Data Pipelines for Another Team

**Context:** Data engineering formally someone else's job on international personalization. But it wasn't getting done. Nick had experience from US search where he built pipelines. Built ALL data pipelines for them because they didn't have the velocity.

**How it went down:** Model artifact would be ready, Nick would ping DE team repeatedly for 2+ weeks with no progress, then just build it himself. DE team still responsible for review, so politically OK.

**Stack:** Airflow + Spark + PyTorch Lightning for GPU inference

**Candidate LPs:** Ownership, Bias for Action, Deliver Results

---

## Story: LLM-Based vs Pure Embedding Architecture Debate

**Context:** For generative retrieval, Nick's architecture uses natural language as intermediary:
- Architecture 1 (Nick's): item attributes → LLM → text queries → text encoder → dense retrieval → results → LLM judge evaluation
- Architecture 2 (alternative Nick also built): item embedding → ComiRec retrieval trained on LLM labels → multiple embedding probes for diversity → dense retrieval → merge + rerank → LLM judge

**The disagreement:** Peers during weekly experimental shareout said it was "bizarre" to use natural language as an intermediary step. Expected just a normal two-tower model. Argued architecture 2 was faster, cheaper, full SFT in a fast loop.

**Nick's defense:**
- Speed/cost didn't matter — this is an offline batch signal, not real-time serving
- Architecture 1 outperformed on diversity AND relevance because it leveraged LLM world knowledge directly
- Interpretability was better — literal queries are human readable vs vibes of ComiRec probes
- Diversity problem: 1-shot dense retrieval only gets clustering of similar items. For complementary signal you need diversity (gaming chair + gaming mouse are both good complements for gaming keyboard)
- Modular externalities: query generation and retrieval models can be reused separately on other projects
- Circularity defense: Architecture 2 is trained on LLM judge labels AND evaluated by same judge (train/test split, but evaluation ceiling bounded by judge). Architecture 1 generates novel text evaluated through full retrieval pipeline — fundamentally different output modality.

**Key move:** Nick anticipated the opposition and proactively built BOTH architectures before the debate. Came to the argument with comparative data, not just opinion. People were surprised he had preempted this.

**The "commit" part:** Pushed the LLM-based development loop despite people saying "just do SFT."

**Shared value:** Label data generated by the pipeline is used by others for variety of use cases, including hard negatives for similar items retrieval.

**Candidate LPs:** Have Backbone, Invent & Simplify, Dive Deep, GenAI Fluency

---

## Story: Cutting-Edge Technical Depth (Learn & Be Curious candidate)

**Papers implemented from scratch for production:**
- DeepRetrieval (RL for query generation) — LoRA fine-tuning Llama 3.2, PPO/GRPO with explicit reward function
- ComiRec DR and SA (sequential recommendation with diversity)
- Choppy (ranked list truncation, SIGIR 2020)
- SASRec (sequential recommendation)
- Plus 10+ model architectures compared empirically

**RL infrastructure built:**
- Optimized vLLM for inference at scale: 1 inference/sec → 10 inference/sec (8 GPU single node)
- KV cache tuning, batch sizes, tensor parallelism
- Custom SQLite caching layer for RL reward loop — scaled to billions of pairwise predictions
- Cache data reused for SFT on other models

**Active learning (current work):**
- Uncertainty-based active exploration in RL training loop
- item → query → items back → scoring → feed back scores AND relative uncertainty for that item
- Conflicting understanding of model ability → actively explore the space
- Details TBD — need to probe further on how uncertainty is quantified

**Multimodal:**
- CLIP models used extensively
- Image embeddings tested in ComiRec (text+image had highest performance, impractical for runtime)

**Retrieval:**
- Sparse + dense hybrid retrieval
- LLM document expansion for items
- FAISS, HNSW, ScaNN all used

**Training:**
- INT8, FP16 mixed precision (incidental, not a story)
- LoRA fine-tuning
- Single node 8 GPU training

**Candidate LPs:** Learn & Be Curious, Dive Deep, GenAI Fluency

---

## Story: Chile Platform Migration

**Context:** Led the entire Chile team (~5 people) as the US counterpart for migration to unified backend — upsell and cross-sell paths (similar and complementary items). Ongoing.

**Candidate LPs:** Ownership, Deliver Results, Earn Trust

---

## Story: Team Crisis — Onboarding, Docs, Scope Expansion

**Context:** When Nick joined international personalization:
- No evaluation pipeline
- No data pipelines (or stale/broken ones)
- No internal documentation
- People quitting, expanding his scope
- Wrote all internal documentation
- Handled onboarding of everyone who joined after him
- Manages 4 reports: 2 junior, 2 senior. On org chart they're under his manager, but manager has never had a meeting with them besides onboarding. Nick runs everything.
- 2 people quit, Nick + another staff absorbed most of the work. Was assigned but doesn't feel bad about it.

**Candidate LPs:** Ownership, Highest Standards, Hire & Develop

---

## Story: Embedding Pipeline Bug — Owning a Mistake

**Context:** Early at Walmart (more junior), Nick built an embedding pipeline. Had a bug around MD5 hash computation — when a catalog attribute key changed (e.g. "title"), items already in the index wouldn't get updated embeddings. If item was still in index but title changed, embedding stayed stale.

**Timeline:** In production 3 weeks before discovery. Went through code review.

**Discovery:** Someone else found it while RCA-ing their own evaluation. The bug wasn't responsible for the degradation they were investigating, but they flagged it while diving deep in Nick's pipeline.

**Impact:** <1% of items had stale embeddings, but at scale this matters for dense retrieval where exact embedding correctness matters. Search results were degraded.

**Response:**
- Nick ran blameless post-mortem within the team
- Drafted shareout emails to wider team
- Owned the mistake openly

**Key learning:** "Ownership doesn't end at launch." Had a "fire and forget" approach before this. Main takeaway was continual observation of shipped features beyond release.

**Trust dynamic:** Team didn't harbor resentment. Nick gained trust FOR the person who RCA'd the result — "they earned my trust."

**Candidate LPs:** Earn Trust (vocally self-critical), Ownership, Learn & Be Curious

---

## Story: Direct Report Development — Mixed Results

**Context:** One report has zero ability to dive deep. Nick tried leading by example — doing some of their work to demonstrate how much better/more comprehensive it could be. Essentially guilt them into doing it better. They seem immune. Ongoing issue, room for improvement.

**Contrast:** Another direct report much more responsive. Nick motivated them by trusting them with big complicated scientific questions (a lot of RL work).

**Candidate LPs:** Earn Trust, Hire & Develop

---

## Story: Chile Migration Trust Building

**Context:** Political concerns from Chile team: "are you doing this migration just to lay us off?" Nick built trust by:
- Invited them to work on papers with him
- Gave them insight into all US codebase
- Showed transparency — "nothing to hide decreases worry"

**Candidate LPs:** Earn Trust, Ownership

---

## Story: PM Trust Through Tooling

**Context:** Nick doesn't fully trust PM judgment on ML decisions. But built tooling (eval viewer, metrics dashboards) to create transparency in ML development process and tighten feedback loop. This builds trust in both directions — PMs can see what's happening, Nick gets faster feedback on what matters to product.

**Candidate LPs:** Earn Trust, Bias for Action

---

## Story: Embedding Similarity Cost Reduction

**Context:** GenAI features had very expensive offline compute costs. Given SLA, mandate was to reduce costs.

**What Nick built:**
- Embedding-based similarity pass: if signal has been computed for one item, reuse it for similar items (green crocs and yellow crocs get same complementary signal)
- Evaluated through relevance judgment — looked great, saved compute

**Regret/learning:** Complicated additional process. Teammates don't understand it and have no interest in learning. When Nick leaves, it will be non-understandable. If he did it again, would invest more in documentation and knowledge transfer.

**Candidate LPs:** Bias for Action, Invent & Simplify, Frugality

---

## Updated Story-LP Flexibility Table (25 stories)

| # | Story | Candidate LPs | Validated? |
|---|-------|--------------|-----------|
| 1 | Generative retrieval pipeline | GenAI Fluency, Deliver Results | YES |
| 2 | Evaluation framework (LLM judge, 6 rubrics) | Highest Standards, Ownership, Bias for Action, Dive Deep | YES |
| 3 | 10+ model architecture comparison (ComiRec etc.) | Highest Standards, Dive Deep, Deliver Results, Learn & Be Curious | YES |
| 4 | End-to-end observability (dashboards, drift, RCA) | Highest Standards, Ownership, Dive Deep, Deliver Results | YES |
| 5 | Eval viewer (internal model comparison tool) | Bias for Action, Ownership, Highest Standards | YES |
| 6 | Embedding pipeline rescue (stale Jupyter → Airflow) | Bias for Action, Ownership, Highest Standards | YES |
| 7 | Post-A/B metrics dashboard (replaced Adobe/Kronos) | Bias for Action, Ownership, Deliver Results | YES |
| 8 | Embedding similarity cost reduction | Bias for Action, Invent & Simplify | YES |
| 9 | Arbitration engine + near/far intent framework | Ownership, Dive Deep, GenAI Fluency | YES |
| 10 | Built all data pipelines for another team | Ownership, Bias for Action, Deliver Results | YES |
| 11 | LLM-based vs pure embedding architecture debate | Have Backbone, Dive Deep, GenAI Fluency | YES |
| 12 | Cutting-edge tech depth (papers → production) | Learn & Be Curious, Dive Deep, GenAI Fluency | YES (partial) |
| 13 | Chile migration + trust building | Ownership, Earn Trust, Deliver Results | YES |
| 14 | Embedding pipeline bug — owning a mistake | Earn Trust, Ownership | YES |
| 15 | Direct report development — mixed results | Earn Trust, Hire & Develop | YES |
| 16 | PM trust through tooling | Earn Trust, Bias for Action | YES |
| 17 | Team crisis — onboarding, docs, scope expansion | Ownership, Highest Standards | YES |
| 18 | A/B bucketing fix | Ownership, Dive Deep | UNREVIEWED |
| 19 | Query rewriting feedback (private, senior eng) | Earn Trust | UNREVIEWED |
| 20 | Cross-encoder latency root cause | Dive Deep, Ownership | UNREVIEWED |
| 21 | 8 model launches campaign | Deliver Results | UNREVIEWED |
| 22 | Bench scientist → prod ML (Synthego) | Learn & Be Curious | UNREVIEWED |
| 23 | Item Compare (CA/MX) | GenAI Fluency, Deliver Results | UNREVIEWED |
| 24 | Content safety threshold incident | Bias for Action | UNREVIEWED |
| 25 | Microscopy classifier (Synthego) | Deliver Results, Bias for Action | UNREVIEWED |
