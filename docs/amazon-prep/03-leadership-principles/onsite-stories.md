# Amazon Onsite — LP Stories (9 Confirmed)

Each LP has a primary and backup story in STAR format. No story is reused across LPs.

## Review Status

| # | LP | Primary Story | Status |
|---|-----|--------------|--------|
| 1 | GenAI Fluency | Generative Retrieval Pipeline | VALIDATED |
| 2 | Insist on Highest Standards | LLM-as-Judge Evaluation Framework | VALIDATED |
| 3 | Bias for Action | Post-A/B Metrics Dashboard | VALIDATED |
| 4 | Ownership | Redesigning the DS/MLOps Operating Model | DRAFT |
| 5 | Earn Trust | Embedding Pipeline Bug — Owning a Mistake | VALIDATED |
| 6 | Have Backbone; Disagree & Commit | LLM-Based vs Pure Embedding Architecture Debate | VALIDATED |
| 7 | Learn & Be Curious | Papers to Production (DeepRetrieval, ComiRec, Choppy) | VALIDATED |
| 8 | Dive Deep | Similar Items Pipeline — Full Stack Investigation | VALIDATED |
| 9 | Deliver Results | EBR Model Iteration Campaign + CIKM 2024 | VALIDATED |

**VALIDATED** = reviewed with Nick in interactive session, based on real details.

---

## 1. GenAI Fluency — VALIDATED

### Primary: Generative Retrieval Pipeline

**Situation:** At Walmart, our international personalization team faced a fundamental cold-start challenge. In mature markets like the US, over 90% of catalog items had never been purchased — the catalog was massively underexplored. In emerging markets like Mexico, the problem was even more extreme: virtually no engagement data existed, meaning nearly 100% of items had zero signal. Traditional collaborative filtering was a non-starter — you can't recommend based on co-purchase patterns when purchase data doesn't exist. Leadership had identified GenAI as a strategic priority, but there was no concrete architecture for how to apply it to recommendation at scale.

**Task:** I needed to design a GenAI-powered recommendation architecture that could generate personalized recommendations for any item or user — including cold-start scenarios — across all three North American markets (US, CA, MX).

**Action:** I designed a generative retrieval pipeline: for each anchor (user or item), an LLM generates shopping intents and semantic queries, which then feed into our existing search infrastructure (Solr, FAISS) to retrieve a ranked list of recommendations. This was a fundamentally different approach from collaborative filtering — instead of learning from past purchase patterns, we were generating the reasoning about what a user might want next. The system runs as an offline batch signal with daily delta updates across 3M anchor items, prioritizing the most popular items for freshness.

I also shipped a second GenAI feature, Item Compare, where an LLM generates use cases and highlights for ~300K items in high-traffic categories across CA and MX, letting customers compare products side-by-side — a capability that didn't exist before.

After launch, our PM flagged that results weren't price-aware — a critical gap for our cost-conscious customers. I executed a two-phase fix: a reranking hotfix in 2 weeks to inject price sensitivity, then a 6-week effort to retrain the retrieval model on price-aware queries for a permanent solution.

Separately, I evaluated GenAI for search bar query expansion. We prototyped it, but the combination of latency, cost, and degrading relevance lift as user queries shifted toward grocery made it unviable. We killed it based on the data.

**Result:** The generative retrieval pipeline serves all three NA markets, providing personalized recommendations with full catalog coverage — including items with zero purchase history. Item Compare launched in CA/MX. The query expansion kill saved ongoing cost with no relevance loss. The key insight: GenAI's biggest value in recommendation isn't replacing traditional ML — it's solving problems traditional ML fundamentally can't, like cold start at scale.

### Backup: <!-- TO FILL -->

### Question Angles:
- "Tell me about a time you applied generative AI to solve a real business problem."
- "How do you evaluate whether a GenAI approach is the right solution vs traditional ML?"
- "Tell me about a time you had to manage the risks or limitations of a GenAI system."

---

## 2. Insist on the Highest Standards — VALIDATED

### Primary: LLM-as-Judge Evaluation Framework

**Situation:** When I joined Walmart's International Personalization team, the team was iterating fast on models but lacked a scalable way to predict A/B outcomes offline. Models were going straight to live traffic with engagement summaries as the primary signal, and the feedback loop was slow — a failed A/B test meant weeks of lost experimentation time. Several recent launches had underperformed, and the team recognized the gap but hadn't had bandwidth to build a systematic evaluation layer while simultaneously shipping features across three markets.

**Task:** I needed to establish an evaluation standard so the team could predict whether a model would succeed before committing live traffic to it.

**Action:** I built an LLM-as-judge evaluation framework with 6 specialized rubrics — one per carousel type (similar items, complementary items, user-item engagement, etc.). Each rubric was validated against engagement data, with scores monotonically predicting engagement rate. A key design decision was keeping rubrics aligned with each carousel's purpose, not just raw engagement. For example, the complementary items rubric rates similar/alternative items low even when users click on them — because if every carousel optimizes the same engagement signal, they converge on the same items and cannibalize each other. Defining distinct objectives per carousel achieves diversity across the full page, a global optimum rather than a local one.

I backtested the framework against two previous launches that had failed in A/B — the LLM judge correctly identified both as relevance-negative. I put together a deck showing this evidence, presented it to my manager, and he mandated adoption across the team.

**Result:** All four model launches shipped after the evaluation framework — Recommended For You, Intent-Based Recommendation, Continue Your Shopping, and the Arbitration Engine — were positive on A/B, each delivering 10-15 bps GMV lift. No more surprises. The framework became the standard evaluation step before any launch on the team.

### Backup: <!-- TO FILL -->

### Question Angles:
- "Tell me about a time you pushed back on shipping something because it didn't meet your quality bar."
- "Tell me about a time you raised the bar for your team."
- "Tell me about a time your standards were too high and it caused problems."

---

## 3. Bias for Action — VALIDATED

### Primary: Post-A/B Metrics Dashboard

**Situation:** At Walmart, the team's post-A/B analysis relied on Adobe dashboards managed by the analytics team. The dashboards were tabular only — no graphs, no way to cleanly view GMV lift over time, no ability to break down results by step in the user journey or by module. There was no clean way to do head-to-head A/B comparison. We were making launch decisions based on incomplete data views. The analytics team had their own roadmap and priorities across multiple orgs — our ML-specific visualization needs weren't their top priority, and reasonably so.

**Task:** I needed a way to properly evaluate whether our model launches were working — not just top-line metrics, but granular breakdowns that would tell me where gains were coming from and where regressions were hiding.

**Action:** Rather than waiting on another team's roadmap, I built a full metrics dashboard from scratch. It tracked revenue per customer, click-through rate broken down by step in the user journey and by module, with filtering by A/B experiment key for head-to-head comparison. I built it for myself first, then shared it with the team. This was squarely the analytics team's domain, not mine — my job was ML science — but I had a specific need and the skills to address it quickly.

**Result:** The dashboard became the team's primary tool for evaluating launches. It gave us granular visibility — we could see exactly which user journey steps were driving lift and which were flat. This directly informed model iteration decisions and helped us diagnose issues that the tabular Adobe reports would have missed. Building it myself turned what would have been months of cross-team coordination into a weekend project.

### Backup: <!-- TO FILL -->

### Question Angles:
- "Tell me about a time you made a decision quickly without all the data."
- "Tell me about a time you took a calculated risk that paid off."
- "Tell me about a time you acted too quickly and had to course-correct."

---

## 4. Ownership — VALIDATED

### Primary: Redesigning the DS/MLOps Operating Model

**Situation:** On Walmart's International Personalization team, there was a structural split between data scientists who built models and MLOps engineers who brought them to production. On the US search team I'd come from, there was no such distinction — scientists owned everything end-to-end, which meant no gaps in ownership. On the international team, the workflow was: DS builds a prototype in isolation, hands off a finished artifact, and MLOps reverse-engineers production pipeline code from it. This created two systematic failure modes. First, MLOps would introduce bugs during the translation — they lacked context on design decisions, so subtle things broke. Second, MLOps couldn't focus on their actual core job — uptime, KTLO, refactoring existing signals — because they were buried in rewrite work for new launches. The problem wasn't people, it was the workflow.

**Task:** I needed to change how DS and MLOps collaborated so that new models could ship reliably without drowning the MLOps team in translation work. This wasn't about one pipeline — the same failure mode was repeating across the similar items index, the embedding pipelines, and other signals.

**Action:** I started by demonstrating the end-to-end model on my own projects — writing production pipeline code myself in Airflow with Spark and PyTorch Lightning, carrying it through to production as a single code owner. Once I had concrete evidence that the pattern worked, I proposed a process change to the team: DS owns the pipeline code from day one, not prototype code that gets rewritten. I introduced three elements. First, a joint design review early — DS and MLOps align on pipeline architecture, GPU provisioning, and data volumes before anyone writes code, not after the prototype is locked in. Second, a single design doc that both sides contribute to — a shared source of truth so context isn't lost in handoff. Third, a validation contract upfront — agreed-upon success criteria like inference throughput targets, data freshness expectations, and monitoring plans, so "production-ready" has a shared definition before the project starts. DS tests end-to-end and gets sign-off. MLOps reviews code and focuses on what they're actually good at: reliability, monitoring, infrastructure, and improving existing signals.

There was natural tension because redefining the handoff boundary felt like scope erosion to the MLOps side. I framed it differently: this wasn't taking scope from MLOps, it was removing translation work that was drowning them so they could focus on higher-value work. The projects that went through this process validated the approach — design reviews caught issues like GPU provisioning mismatches in week one instead of week eight.

**Result:** The projects that went through the unified design review process had zero handoff failures. The pattern — scientist owns the pipeline, MLOps owns reliability — became the team's default for new launches. It worked because it respected what each side was actually good at: scientists had the model context to write correct pipeline code, MLOps had the production expertise to ensure uptime and infrastructure quality. MLOps capacity freed up from rewrite work went back into KTLO and refactoring existing signals that needed attention.

### Backup: Built All Data Pipelines for Another Team (L5 execution version)

**Situation:** On Walmart's International Personalization team, the DE team was loaded with competing priorities across multiple orgs — our personalization pipelines were one of many workstreams they supported. Model artifacts would be ready and then sit for weeks waiting on pipeline work. As the team scaled from one market to three, the gap between model development velocity and production deployment capacity kept widening. Some pipelines had been prototyped by data scientists in notebooks as stopgaps, but those weren't production-grade — embeddings could go weeks without refresh.

**Task:** I needed to get our models into production. Waiting on the data engineering team's timeline — which was constrained by their own legitimate priorities — would have meant features sitting on the shelf for months.

**Action:** I built all of the data pipelines myself. I had experience from my previous role on US search where I'd built similar infrastructure, so I knew the stack. I designed the pipelines in Airflow with Spark for data processing and PyTorch Lightning for GPU inference, separating out the compute-intensive model inference from the data transformation steps. I carried each pipeline from development through to production as the single code owner. The DE team remained responsible for code review, so it worked politically — I wasn't stepping on toes, I was unblocking myself.

**Result:** Every model I built shipped to production without being blocked by the resourcing constraint. The pipelines ran reliably across all three markets. The pattern I established — scientist owns the full pipeline, DE reviews — became the team's default operating model. It worked because it played to each team's strengths: scientists had the model context, DE had the production standards.

### Question Angles:
- "Tell me about a time you took ownership of something outside your scope."
- "Tell me about a time you saw a problem and fixed it without being asked."
- "Tell me about a time an initiative you owned failed."

---

## 5. Earn Trust — VALIDATED

### Primary: Embedding Pipeline Bug — Owning a Mistake

**Situation:** Earlier in my time at Walmart, I built an embedding pipeline for our search retrieval system. The pipeline computed MD5 hashes to determine which items needed re-embedding. I had a bug: when a catalog attribute key changed — for example, a product title was updated — items already in the index wouldn't get new embeddings because the hash logic didn't account for the attribute change. The bug went through code review and made it to production.

**Task:** Three weeks later, a colleague was doing a root cause analysis on a separate evaluation issue. While diving deep into my pipeline, they discovered the stale embedding bug. It wasn't causing the degradation they were investigating, but they flagged it. Less than 1% of items were affected, but at scale with dense retrieval, incorrect embeddings matter — search results were degraded for those items.

**Action:** I owned the mistake immediately. I ran a blameless post-mortem within the team and drafted shareout emails to the wider org explaining what happened, the impact, and the fix. I didn't downplay it or blame the code reviewers who had also missed it. The deeper issue was that I had a "fire and forget" approach to shipped features — I built it, deployed it, and moved on without monitoring for exactly this class of silent degradation.

**Result:** The team didn't hold it against me — mistakes happen, especially with a junior engineer learning production systems. But the experience fundamentally changed how I work. I learned that ownership doesn't end at launch. After this, I built monitoring into every pipeline I shipped and established the habit of continuous observation post-release. I also gained deep trust for the colleague who found the bug — they earned my respect by diving deep into someone else's code without hesitation.

### Backup: <!-- TO FILL -->

### Question Angles:
- "Tell me about a time you delivered difficult feedback."
- "Tell me about a time you had to rebuild trust after a mistake."
- "Tell me about a time you were vocally self-critical."

---

## 6. Have Backbone; Disagree & Commit — VALIDATED

### Primary: LLM-Based vs Pure Embedding Architecture Debate

**Situation:** For our generative retrieval pipeline at Walmart, I designed an architecture that uses natural language as an intermediary: item attributes go into an LLM which generates text queries, those queries feed into a text encoder for dense retrieval, and the results are evaluated by an LLM judge. Peers on the team thought this was bizarre — why generate natural language text as a middle step when you could stay entirely in embedding space?

**Task:** I anticipated this opposition. The alternative architecture was a pure embedding approach: item embeddings feed into a ComiRec retrieval model trained on LLM-generated relevance labels, with multiple embedding probes for diversity, followed by dense retrieval and reranking. It was faster, cheaper, and avoided the "bizarre" text generation step. I needed to defend why the LLM-based architecture was superior for our use case.

**Action:** Before the debate even happened, I built both architectures and trained them. When peers raised concerns during our weekly experimental shareout, I presented comparative results. Architecture 1 (LLM-based) outperformed on both diversity and relevance because it leveraged the LLM's world knowledge directly — a one-shot dense retrieval model only gets a clustering of similar items, but for complementary signal you need genuine diversity (gaming chair and gaming mouse are both good complements for gaming keyboard). I also showed that interpretability was better — the generated queries are human-readable versus opaque embedding probes. And the speed objection didn't apply because this was an offline batch signal, not real-time serving. Finally, the LLM-based pipeline produced modular components — the query generation and retrieval models could be reused separately on other projects. The label data I generated was used by other teams for hard negatives in similar items retrieval.

**Result:** People were surprised I'd preempted the objection by building both. The data made the case. We shipped the LLM-based architecture, and I continued pushing this development loop despite ongoing pressure to "just do SFT." The generated label data became a shared asset across multiple team projects.

### Backup: <!-- TO FILL -->

### Question Angles:
- "Tell me about a time you disagreed with a senior leader."
- "Tell me about a time you committed to a decision you disagreed with."
- "Tell me about a time the team went against your recommendation and you had to support it."

---

## 7. Learn & Be Curious — VALIDATED

### Primary: Papers to Production — Implementing Cutting-Edge Research

**Situation:** At Walmart, the personalization and search teams were building recommendation and retrieval systems that needed to perform at scale across three markets. The team had been heads-down shipping product for two years straight — they'd built a working system across three markets, which was a real achievement. But there was a gap between what the research community was publishing and what we were deploying. Existing approaches hadn't been rigorously compared against newer methods, and there hadn't been bandwidth to close that loop while simultaneously keeping the lights on across US, CA, and MX.

**Task:** I wanted to push the technical frontier of what we could build by going directly to the research literature, implementing promising methods, and empirically comparing them against our existing approaches.

**Action:** I systematically read papers and implemented them from scratch for production use. I implemented DeepRetrieval's approach to RL-based query generation — LoRA fine-tuning Llama 3.2 with PPO and GRPO using explicit reward functions. This required building substantial infrastructure: I optimized vLLM for inference at scale, taking throughput from about 1 inference per second to 10 through KV cache tuning, batch size optimization, and tensor parallelism across 8 GPUs. I built a custom SQLite caching layer for the RL reward loop that scaled to billions of pairwise predictions — this cache data was then reusable for SFT on other models. I implemented ComiRec (both DR and SA variants) for sequential recommendation with diversity, SASRec, and Choppy for ranked list truncation. In total I compared 10+ architectures with full hyperparameter sweeps. I'm currently implementing uncertainty-based active learning in the RL training loop — measuring conflicting signals about the model's understanding of specific items to actively explore the space where the model is least confident.

**Result:** ComiRec-SA won the architecture comparison for user-item retrieval — strong retrieval for engaged items with good diversity. The RL-trained query generation model powers the generative retrieval pipeline serving all three NA markets. The billions of cached pairwise predictions became a shared data asset for SFT across multiple team projects. Each paper I implemented expanded the team's technical toolkit and raised the bar for what we considered "good enough."

### Backup: <!-- TO FILL -->

### Question Angles:
- "Tell me about a time you learned a new domain or skill rapidly."
- "Tell me about a time your curiosity led to a breakthrough."
- "Tell me about a recent technology you explored on your own."

---

## 8. Dive Deep — VALIDATED

### Primary: Similar Items Pipeline — Full Stack Investigation

**Situation:** When I joined Walmart's International Personalization team, I started by reviewing what pipelines were actually running in production. The similar items pipeline had been built as a proof of concept and successfully launched in Mexico — that was the foundation that showed the approach worked. But as the team tried to scale it to all three markets, the architecture hit limits. It was provisioned on A100s for a text encoder that didn't need that much compute, was doing inference on Spark CPU workers instead of GPU, and had image embeddings added for secondary filtering that had never been evaluated for impact. The pipeline ran partially in Mexico but was failing in the other markets. There was also a structural challenge: data scientists built models and MLOps deployed them, and context was lost in that handoff — neither side felt fully accountable for end-to-end reliability.

**Task:** The team recognized the issues but was stretched across multiple workstreams. I believed a production pipeline shouldn't have persistent failures, and I had the cross-stack skills to investigate. I needed to understand what was actually wrong, fix it, and get it running in all three markets.

**Action:** I dug into every layer. First, I wrote an LLM-judge evaluation rubric specifically for similar items so I could actually measure quality — no such metric existed before. Then I used that rubric to systematically test assumptions: I removed the image embedding filtering and replaced it with a lighter-weight filter, and the rubric showed quality was equivalent — the image embeddings had been adding complexity with no measurable benefit. I rewrote the embedding generation code in PyTorch Lightning with native multi-GPU support, separating data processing from GPU inference tasks and running on V100s in parallel instead of the A100s they couldn't reliably provision. I carried the pipeline from rewrite through to production as a single code owner — closing the DS-to-MLOps handoff gap by owning both sides.

**Result:** The rewritten pipeline went from partially working in one market to running reliably across all three (US, CA, MX) with roughly 100x throughput improvement. The evaluation rubric gave the team a systematic way to navigate the design space — making evidence-based decisions about what to include or remove rather than relying on intuition about which components were contributing.

### Backup: <!-- TO FILL -->

### Question Angles:
- "Tell me about a time you found a root cause others missed."
- "Tell me about a time the data told a different story than expected."
- "Tell me about a time you had to go deep into unfamiliar code or systems."

---

## 9. Deliver Results — VALIDATED

### Primary: EBR Model Iteration Campaign + CIKM 2024

**Situation:** At Walmart, the US search embedding-based retrieval (EBR) system was the primary model powering product search. While the initial EBR deployment had improved relevance over traditional methods, there were significant gaps: training data noise causing relevance degradation, poor handling of misspelled queries, and no systematic approach to iterating on the model.

**Task:** I needed to deliver sustained, measurable improvements to the core search retrieval model — the system that powers all US product search.

**Action:** I led a series of iterative improvements to the EBR model over multiple launch cycles. Each iteration targeted a specific weakness: a relevance reward model trained on human feedback to filter noisy training data, hard negative mining to improve fine-grained discrimination, in-batch negatives for training efficiency, dual loss optimization, price-aware retrieval, typo-aware training for query robustness, and semi-positive generation for edge cases. Each launch went through offline evaluation, A/B testing, and phased rollout. I published the methodology as first author at CIKM 2024, documenting the relevance reward model and multi-objective learning approach.

**Result:** Across these launches, each iteration delivered approximately 10 bps GMV lift in A/B testing — at Walmart's search scale, each launch represents roughly $100M in annual impact. The cumulative improvements made EBR the foundation of Walmart's search relevance stack.

### Backup: <!-- TO FILL -->

### Question Angles:
- "Tell me about the most impactful project you delivered."
- "Tell me about a time you delivered results despite significant obstacles."
- "Tell me about a time you had to make tradeoffs to deliver on time."

---

## Backup Story Bank (unused validated stories)

These stories are available as backups for any LP. Each has been validated in interactive sessions.

| Story | Best Backup For |
|-------|----------------|
| Arbitration engine + near/far intent framework | Ownership, Dive Deep, GenAI Fluency |
| Eval viewer (internal model comparison tool) | Bias for Action, Highest Standards |
| Embedding pipeline rescue (stale Jupyter → Airflow) | Bias for Action, Ownership |
| 10+ model architecture comparison | Highest Standards, Dive Deep |
| End-to-end observability (dashboards, drift, RCA) | Ownership, Dive Deep |
| Embedding similarity cost reduction | Bias for Action |
| Chile migration + trust building | Earn Trust, Ownership |
| Direct report development — mixed results | Earn Trust |
| PM trust through tooling | Earn Trust |
| Team crisis — onboarding, docs, scope expansion | Ownership |
| Content safety threshold incident | Bias for Action (UNREVIEWED) |
| Query rewriting feedback | Earn Trust (UNREVIEWED) |
