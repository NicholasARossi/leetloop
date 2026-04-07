#!/usr/bin/env python3
"""Seed onsite_prep_questions from the amazon-prep markdown files.

Usage:
    cd api && python scripts/seed_onsite_prep.py

Idempotent: upserts all questions using (category, subcategory, prompt_text) as the
natural key. Existing rows are updated in place — no data is deleted.
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ─── Rubric dimension definitions per category ────────────────────────────

LP_RUBRIC = [
    {"name": "star_structure", "label": "STAR Structure", "description": "Situation, Task, Action, Result — each clearly present"},
    {"name": "specificity", "label": "Specificity", "description": "Concrete numbers, dates, team sizes — not vague"},
    {"name": "i_vs_we", "label": "\"I\" vs \"We\"", "description": "Personal contributions clear, not hiding behind team"},
    {"name": "lp_signal", "label": "LP Signal", "description": "Answer clearly demonstrates the target principle"},
    {"name": "timing", "label": "Timing", "description": "4-5 minutes, paced well, not rushing or rambling"},
    {"name": "impact", "label": "Impact", "description": "Result is quantified and meaningful"},
]

BREADTH_RUBRIC = [
    {"name": "definition", "label": "Definition", "description": "Correct, precise definition of the concept"},
    {"name": "intuition", "label": "Intuition", "description": "Explains WHY it works, not just WHAT it is"},
    {"name": "failure_modes", "label": "Failure Modes", "description": "Knows when and how the method breaks"},
    {"name": "practical_connection", "label": "Practical Connection", "description": "Connects theory to real-world application"},
    {"name": "timing", "label": "Timing", "description": "Well-paced within 2 minutes"},
    {"name": "completeness", "label": "Completeness", "description": "Covers the full scope of the question"},
]

DEPTH_RUBRIC = [
    {"name": "architecture_clarity", "label": "Architecture Clarity", "description": "Interviewer could draw the system from description"},
    {"name": "technical_depth", "label": "Technical Depth", "description": "Goes beyond 'I used X' — configs, params, failure handling"},
    {"name": "design_decisions", "label": "Design Decisions", "description": "Explains WHY, compares alternatives"},
    {"name": "honest_framing", "label": "Honest Framing", "description": "Calibrated about what they built, doesn't overstate"},
    {"name": "timing", "label": "Timing", "description": "Well-paced within 2 minutes"},
    {"name": "metrics_impact", "label": "Metrics & Impact", "description": "Quantified results with before/after"},
]

DESIGN_RUBRIC = [
    {"name": "problem_framing", "label": "Problem Framing", "description": "Clarifies scope and constraints before diving in"},
    {"name": "architecture", "label": "Architecture", "description": "Sound multi-component system design with data flow"},
    {"name": "data_training", "label": "Data & Training", "description": "Addresses ML lifecycle: data, features, training, validation"},
    {"name": "evaluation", "label": "Evaluation", "description": "Offline/online metrics, A/B testing, guardrails"},
    {"name": "production", "label": "Production", "description": "Deployment, monitoring, drift detection, scaling"},
    {"name": "timing_structure", "label": "Timing & Structure", "description": "Well-structured walkthrough, good time allocation"},
]

# ─── Breakdown phase templates (7 phases with per-phase rubric dimensions) ──

BREAKDOWN_PHASE_TEMPLATES = [
    {
        "name": "Clarify Requirements",
        "prompt": "Define the problem scope, constraints, users, and success metrics before designing anything.",
        "duration_seconds": 180,
        "key_areas": [
            "User types and scale",
            "Latency and throughput constraints",
            "Key success metrics",
            "Regulatory or compliance considerations",
        ],
        "rubric_dimensions": [
            {"name": "scope_clarity", "label": "Scope Clarity", "description": "Clearly defines what's in and out of scope"},
            {"name": "constraint_identification", "label": "Constraint Identification", "description": "Identifies key constraints: latency, scale, compliance"},
        ],
    },
    {
        "name": "Metrics",
        "prompt": "Define the offline and online metrics you'll use to measure success. Discuss tradeoffs between metrics.",
        "duration_seconds": 210,
        "key_areas": [
            "Primary offline metric and why",
            "Online/business metric alignment",
            "Metric tradeoffs (precision vs recall, engagement vs quality)",
            "Guardrail metrics",
        ],
        "rubric_dimensions": [
            {"name": "metric_selection", "label": "Metric Selection", "description": "Chooses appropriate offline and online metrics"},
            {"name": "metric_tradeoffs", "label": "Metric Tradeoffs", "description": "Discusses tensions between competing metrics"},
            {"name": "business_alignment", "label": "Business Alignment", "description": "Connects technical metrics to business outcomes"},
        ],
    },
    {
        "name": "High-Level Architecture",
        "prompt": "Draw the system architecture: major components, data flow, and how they connect.",
        "duration_seconds": 210,
        "key_areas": [
            "End-to-end pipeline from input to output",
            "Key components and their responsibilities",
            "Data flow between components",
            "API boundaries and interfaces",
        ],
        "rubric_dimensions": [
            {"name": "component_design", "label": "Component Design", "description": "Identifies the right components with clear responsibilities"},
            {"name": "data_flow_clarity", "label": "Data Flow Clarity", "description": "Clear data flow that could be whiteboarded"},
        ],
    },
    {
        "name": "Data & Features",
        "prompt": "Describe your data strategy: sources, labeling, feature engineering, and data quality.",
        "duration_seconds": 360,
        "key_areas": [
            "Data sources and collection strategy",
            "Feature engineering approach",
            "Labeling strategy (explicit, implicit, synthetic)",
            "Data quality, bias, and freshness",
        ],
        "rubric_dimensions": [
            {"name": "data_strategy", "label": "Data Strategy", "description": "Sound approach to data collection, labeling, and quality"},
            {"name": "feature_engineering", "label": "Feature Engineering", "description": "Thoughtful feature design connected to the problem"},
            {"name": "data_quality", "label": "Data Quality", "description": "Addresses bias, freshness, and distribution issues"},
        ],
    },
    {
        "name": "Model Design",
        "prompt": "Choose your model architecture, training strategy, and justify your choices against alternatives.",
        "duration_seconds": 360,
        "key_areas": [
            "Model architecture choice and justification",
            "Training signal and loss function",
            "Alternatives considered and why rejected",
            "Hyperparameter strategy and validation",
        ],
        "rubric_dimensions": [
            {"name": "model_choice_justification", "label": "Model Choice", "description": "Justifies model selection with concrete tradeoffs"},
            {"name": "training_strategy", "label": "Training Strategy", "description": "Sound training signal, loss function, and validation approach"},
            {"name": "technical_depth", "label": "Technical Depth", "description": "Goes beyond surface-level — discusses configs, edge cases"},
        ],
    },
    {
        "name": "Serving & Scale",
        "prompt": "How do you deploy and serve this system? Cover latency, scaling, and failure handling.",
        "duration_seconds": 240,
        "key_areas": [
            "Serving architecture (batch vs real-time)",
            "Latency budget breakdown per component",
            "Scaling strategy (horizontal, caching, sharding)",
            "Failure modes and fallbacks",
        ],
        "rubric_dimensions": [
            {"name": "serving_architecture", "label": "Serving Architecture", "description": "Production-ready serving design with clear latency budget"},
            {"name": "latency_awareness", "label": "Latency Awareness", "description": "Understands latency constraints and optimizations"},
            {"name": "scalability", "label": "Scalability", "description": "Addresses scaling challenges with concrete solutions"},
        ],
    },
    {
        "name": "Evaluation & Monitoring",
        "prompt": "How do you evaluate before launch and monitor in production? Cover testing, A/B, and drift.",
        "duration_seconds": 180,
        "key_areas": [
            "Offline evaluation strategy",
            "A/B testing and launch gating",
            "Production monitoring and alerting",
            "Drift detection and iteration plan",
        ],
        "rubric_dimensions": [
            {"name": "eval_strategy", "label": "Evaluation Strategy", "description": "Comprehensive offline + online evaluation plan"},
            {"name": "monitoring_plan", "label": "Monitoring Plan", "description": "Production monitoring with drift detection and alerts"},
            {"name": "iteration_approach", "label": "Iteration Approach", "description": "Clear plan for iterating based on production feedback"},
        ],
    },
]

# ─── Question definitions ─────────────────────────────────────────────────

questions = []
sort_order = 0

# ── LP Stories (from onsite-stories.md — 9 validated stories, 1 prompt each) ──

lp_stories = [
    ("GenAI Fluency",
     "Tell me about a time you applied generative AI to solve a real business problem.",
     "Generative Retrieval Pipeline — LLM generates shopping intents and queries for cold-start items across 3 NA markets"),
    ("Insist on Highest Standards",
     "Tell me about a time you pushed back on shipping something because it didn't meet your quality bar.",
     "Intent-Based Index Cannibalization Pushback — blocked PM copy-paste launch, showed cannibalization with LLM judge, built vector entropy orthogonality metric to guide fix"),
    ("Bias for Action",
     "Tell me about a time you had to make a decision and move forward quickly without all the data.",
     "Post-A/B Metrics Dashboard — built full analytics dashboard in a weekend instead of waiting on analytics team's roadmap"),
    ("Ownership",
     "Tell me about a time you took ownership of something outside your scope.",
     "Embedding Infrastructure — assigned to ML features but international team had no shared embedding platform. Built end-to-end infra (text + user embeddings, compute, store, serve, monitor) that became team-wide standard for all rec pipelines."),
    ("Earn Trust",
     "Tell me about a time you made a mistake.",
     "Embedding Pipeline Bug — owned mistake immediately, ran blameless post-mortem, drafted org-wide shareout"),
    ("Have Backbone; Disagree & Commit",
     "Tell me about a time you disagreed with your manager or team on a technical direction.",
     "DS/MLOps Operating Model — disagreed with handoff workflow, MLOps pushed back on scope erosion, reached consensus through joint design reviews and reframed ownership boundaries."),
    ("Learn & Be Curious",
     "Tell me about a time you had to learn a completely new domain or skill set.",
     "Papers to Production — implemented DeepRetrieval, ComiRec, SASRec, Choppy from research papers"),
    ("Dive Deep",
     "Tell me about a time you found a root cause that others had missed.",
     "Similar Items Pipeline — reviewed production, found image embeddings added complexity with no quality benefit"),
    ("Deliver Results",
     "Tell me about the most impactful project you've delivered in measurable business results.",
     "EBR Model Iteration — series of improvements each delivering ~10bps GMV (~$100M annual each). Published at CIKM 2024."),
]

for lp_name, prompt_text, context_hint in lp_stories:
    questions.append({
        "category": "lp",
        "subcategory": lp_name,
        "prompt_text": prompt_text,
        "context_hint": context_hint,
        "rubric_dimensions": LP_RUBRIC,
        "target_duration_seconds": 270,
        "sort_order": sort_order,
    })
    sort_order += 1

# ── ML Breadth (20 questions from questions.md) ──

breadth_questions = [
    ("Supervised Learning", "Compare logistic regression, gradient boosted trees, and neural networks for a practical ranking or classification problem. When would you choose each, and what are the failure modes?", "Logistic regression, XGBoost, NNs, model selection criteria, failure modes"),
    ("Supervised Learning", "Explain the bias-variance tradeoff. How does it manifest differently in linear models, tree ensembles, and deep networks? How do L1, L2, and early stopping each address it?", "Bias-variance tradeoff, regularization, L1/L2, early stopping"),
    ("Supervised Learning", "Walk through how gradient boosted trees work. Why do they dominate tabular ML benchmarks, and where do they fall short compared to neural approaches?", "GBTs, XGBoost, tabular ML, sequential boosting, neural alternatives"),
    ("Clustering & DR", "Explain k-means from first principles. When does it fail, and what alternatives would you choose?", "K-means, centroid initialization, failure with non-convex clusters, alternatives"),
    ("Clustering & DR", "What is the difference between PCA and autoencoders as dimensionality reduction tools? When would you prefer one over the other?", "PCA, autoencoders, linear vs nonlinear, reconstruction loss"),
    ("Clustering & DR", "Compare hierarchical clustering and Gaussian mixture models to k-means. What assumptions does each make?", "Hierarchical clustering, GMMs, EM algorithm, cluster shape assumptions"),
    ("Embeddings", "What makes a good embedding space for retrieval? How would you evaluate whether an embedding model has learned useful representations?", "Embedding quality, retrieval metrics, embedding evaluation, similarity structure"),
    ("Embeddings", "Explain metric learning and contrastive loss. What is the role of negative sampling?", "Metric learning, contrastive loss, triplet loss, hard negatives, InfoNCE"),
    ("Embeddings", "How do CNNs, RNNs, and Transformers differ as feature extractors? Why have Transformers displaced the other two in most NLP tasks?", "CNN, RNN, Transformer, attention mechanism, inductive biases"),
    ("Learning-to-Rank", "Explain the pointwise, pairwise, and listwise approaches to learning-to-rank. What are the tradeoffs?", "LTR, pointwise, pairwise (RankNet), listwise (LambdaMART), NDCG optimization"),
    ("Learning-to-Rank", "What is the exploration-exploitation tradeoff, and where does it show up in recommendation or search?", "Exploration-exploitation, bandit algorithms, Thompson sampling, cold-start"),
    ("Recommender Systems", "Compare content-based filtering, collaborative filtering, and hybrid approaches. What cold-start problems does each face?", "Content-based, collaborative filtering, hybrid, cold-start, matrix factorization"),
    ("Calibration", "What is calibration, why does it matter, and how would you measure it?", "Calibration, reliability diagrams, Platt scaling, isotonic regression, ECE"),
    ("Calibration", "How do you choose an operating threshold for a binary classifier in production? What changes when costs are asymmetric?", "Threshold selection, precision-recall curve, cost-sensitive classification"),
    ("Experimental Design", "How would you design an experiment to decide whether an LLM-generated query system is genuinely better than a simpler heuristic?", "A/B testing, LLM evaluation, statistical significance, guardrail metrics"),
    ("Experimental Design", "Why can offline ranking gains fail to translate into online gains? Give concrete examples.", "Offline-online gap, position bias, feedback loops, Simpson's paradox"),
    ("Causal Reasoning", "What is counterfactual reasoning, and why is it important for evaluating recommendation systems?", "Counterfactual evaluation, position bias, inverse propensity weighting, causal inference"),
    ("Evaluation Metrics", "Compare precision, recall, ROC-AUC, PR-AUC, NDCG, MAP, and MRR. When is each appropriate?", "Classification metrics, ranking metrics, threshold-dependent vs threshold-free"),
    ("Evaluation Metrics", "You have a model with high ROC-AUC but poor real-world performance. Diagnose what might be going wrong.", "ROC-AUC limitations, class imbalance, calibration issues, distribution shift"),
    ("Data Quality", "How would you detect and mitigate data leakage in a recommendation pipeline? What about distribution shift, concept drift, and class imbalance?", "Data leakage, distribution shift, concept drift, class imbalance, production robustness"),
]

for subcat, prompt_text, context_hint in breadth_questions:
    questions.append({
        "category": "breadth",
        "subcategory": subcat,
        "prompt_text": prompt_text,
        "context_hint": context_hint,
        "rubric_dimensions": BREADTH_RUBRIC,
        "target_duration_seconds": 120,
        "sort_order": sort_order,
    })
    sort_order += 1

# ── ML Depth (15 questions about YOUR projects — RL, LLM-as-judge, retrieval) ──

depth_questions = [
    ("RL Pipeline", "Walk me through your RL training pipeline end-to-end. What was the reward signal, and why did you choose PPO over alternatives?", "3B model, query generation, retrieval reward + LLM judge, PPO vs GRPO vs DPO"),
    ("RL Pipeline", "Explain your reward signal design. Why a composite of retrieval metrics and LLM judge? What are the risks?", "Dual reward: 40% recall, 30% LLM diversity, 30% relevance. Reward hacking mitigations."),
    ("RL Pipeline", "What is GRPO and how does it differ from PPO? When would you choose one over the other?", "GRPO: no critic, group statistics baseline. PPO: critic network, clipping. Memory vs compute tradeoff."),
    ("RL Pipeline", "How do you prevent reward hacking in your RL system?", "3 mitigations: dual reward, human eval samples, KL penalty. Judge bias detection."),
    ("LLM-as-Judge", "How does your LLM-as-judge evaluation framework work? How did you validate it?", "6 rubrics per carousel type, validated against engagement data, backtested against 2 failed launches"),
    ("LLM-as-Judge", "How do you ensure your LLM judge is calibrated? What if it disagrees with human evaluators?", "Score monotonically predicts engagement. Cohen's kappa for judge-human agreement."),
    ("Retrieval Architecture", "Explain your two-tower retrieval architecture. How do you handle the embedding-to-retrieval pipeline?", "Two-tower for candidate generation, cross-encoder for reranking, FAISS for ANN search"),
    ("Retrieval Architecture", "Walk me through your cross-encoder reranking approach. What was the NDCG improvement and how did you measure it?", "+0.192 NDCG, 50K query test set across 3 markets, p99 latency with two-stage architecture"),
    ("Retrieval Architecture", "How do you handle cold-start items in your recommendation system?", "Generative retrieval: LLM generates shopping intents, feeds into search infrastructure. Covers 100% of catalog."),
    ("Production Systems", "How do you deploy and monitor your ML models in production?", "Airflow orchestration, Spark processing, PyTorch Lightning GPU inference, monitoring for stale embeddings"),
    ("Production Systems", "Tell me about a production failure you diagnosed. What was the root cause?", "Similar items pipeline: image embeddings added complexity without quality benefit. LLM-judge evaluation proved it."),
    ("Content Safety", "Describe your content safety architecture. How do you handle locale-specific compliance?", "3-layer architecture: rule-based, ML classifier, LLM judge. Separate thresholds for US/CA/MX."),
    ("Generative Retrieval", "How does your generative retrieval pipeline differ from traditional collaborative filtering?", "LLM generates reasoning about intent vs learning from co-purchase patterns. Text queries as intermediary."),
    ("Generative Retrieval", "Why did you choose to generate natural language queries as an intermediary rather than staying in embedding space?", "LLM world knowledge for diversity (gaming chair + gaming mouse), interpretability, modular components"),
    ("Research to Production", "How do you evaluate whether a research paper is worth implementing? Walk me through your process.", "Read paper, implement from scratch, benchmark against existing. 10+ architectures compared. ComiRec-SA won."),
]

for subcat, prompt_text, context_hint in depth_questions:
    questions.append({
        "category": "depth",
        "subcategory": subcat,
        "prompt_text": prompt_text,
        "context_hint": context_hint,
        "rubric_dimensions": DEPTH_RUBRIC,
        "target_duration_seconds": 120,
        "sort_order": sort_order,
    })
    sort_order += 1

# ── System Design (6 prompts, each with 5 phases + 4 structured probes) ──
# target_duration_seconds = 1500 (25 min) per question

design_questions = [
    {
        "subcategory": "Alexa ASCI",
        "prompt_text": "Design a trust & safety evaluation system for Alexa+ LLM responses.",
        "context_hint": "Scope: safety taxonomy, multi-layer filtering, LLM-as-judge for safety scoring, real-time vs batch evaluation, drift monitoring, locale-specific compliance, rollback triggers. Your edge: 3-layer content safety at Walmart, locale compliance (CA/MX), drift detection.",
        "phases": [
            {
                "name": "Requirements & Scope",
                "prompt": "Clarify the scope: what types of Alexa+ responses are in scope, who are the users (children vs adults), what are the latency constraints, and what regulatory frameworks apply.",
                "duration_seconds": 180,
                "key_areas": [
                    "Response types: factual answers, creative generation, task completion, multi-turn",
                    "User demographics: children (COPPA) vs adults — drastically different thresholds",
                    "Latency budget: can safety add 200ms? Or must it be near-zero?",
                    "Regulatory: COPPA, FTC guidelines, EU AI Act for global rollout",
                ],
            },
            {
                "name": "Safety Taxonomy",
                "prompt": "Define the taxonomy of what you're detecting. Organize by severity tier and describe what falls into each tier.",
                "duration_seconds": 180,
                "key_areas": [
                    "Tier 1 (block immediately): harmful content, PII leakage, CSAM, dangerous instructions",
                    "Tier 2 (flag for review): medical/legal advice, misinformation on high-stakes topics, culturally sensitive content",
                    "Tier 3 (monitor & learn): bias patterns, subtle stereotyping, quality degradation, off-topic",
                    "Locale-specific tiers: what's Tier 1 in Germany may be Tier 2 in the US",
                ],
            },
            {
                "name": "Architecture: 3-Layer Pipeline",
                "prompt": "Walk through the full architecture. Explain the three-layer pipeline, the latency budget for each layer, and the key design decision around pre- vs post-generation evaluation.",
                "duration_seconds": 420,
                "key_areas": [
                    "Layer 1 (microseconds): rule-based blocklists, regex PII patterns, hard-block known dangerous query-response pairs",
                    "Layer 2 (10-20ms): lightweight ML classifier (distilled BERT) — outputs safety probability per risk category",
                    "Layer 3 (100-200ms): LLM safety judge for ambiguous zone between auto-pass and auto-block thresholds",
                    "Pre-generation (streaming token filter) vs post-generation (complete response) — hybrid approach",
                    "Only route 2-5% of traffic to Layer 3 to manage cost",
                ],
            },
            {
                "name": "Evaluation & Red-Teaming",
                "prompt": "How do you evaluate this system? Describe offline test suite construction, adversarial red-teaming, and how you handle the false positive / false negative tradeoff.",
                "duration_seconds": 300,
                "key_areas": [
                    "Offline test suites: known-unsafe and known-safe examples per risk category",
                    "Adversarial red-teaming: designed to bypass each individual layer",
                    "False positive cost: safe content blocked erodes trust and Alexa engagement",
                    "False negative cost: harmful content delivered — reputational and regulatory risk",
                    "Human review queue for borderline cases — ground truth labeling loop",
                ],
            },
            {
                "name": "Production, Drift & Compliance",
                "prompt": "How does this system behave in production? Cover drift detection, locale compliance rollout, and rollback triggers.",
                "duration_seconds": 300,
                "key_areas": [
                    "Drift monitoring: safety flag rate by category, false positive rate — alert on sudden shifts",
                    "LLM updates change failure modes — safety system must re-evaluate when underlying model changes",
                    "Locale compliance: separate taxonomy versions per region, phased rollout with region-specific red-teaming",
                    "Rollback trigger: if Tier 1 miss rate spikes above threshold, auto-rollback to previous pipeline version",
                    "Cache pre-computed safety scores for common query-response pairs to reduce Layer 3 cost",
                ],
            },
        ],
        "structured_probes": [
            "Walk me through how you'd handle a novel jailbreak that bypasses your ML classifier but passes your rule-based filter. How does it get caught, and how do you prevent the next one?",
            "Your LLM safety judge is flagging 40% of responses as borderline. How do you diagnose whether it's miscalibrated versus genuinely high-risk traffic? What do you do differently in each case?",
            "Alexa+ is launching in Germany under the EU AI Act. What specific changes do you make to your safety taxonomy and compliance layer that you wouldn't need for a US-only launch?",
            "After 6 months you discover your safety system blocks legitimate responses for users querying in minority languages at twice the rate of English. How do you detect this and what's your fix?",
        ],
    },
    {
        "subcategory": "Alexa RAG",
        "prompt_text": "Design a retrieval-augmented generation (RAG) system to ground Alexa+ LLM responses in factual knowledge.",
        "context_hint": "Scope: knowledge ingestion pipeline, hybrid retrieval (dense + sparse), reranking, grounding and faithfulness, knowledge freshness, query routing. Your edge: cross-encoder reranking, FAISS GPU eval, LLM-as-judge for faithfulness.",
        "phases": [
            {
                "name": "Requirements & Scope",
                "prompt": "Clarify the requirements: what knowledge domains does Alexa need to ground? What are the latency constraints for a voice assistant? How much hallucination is tolerable, and is the knowledge static or dynamic?",
                "duration_seconds": 180,
                "key_areas": [
                    "Knowledge domains: Amazon product catalog, general world knowledge, real-time data (weather, news)",
                    "Latency: voice assistant end-to-end must be <1s — RAG retrieval budget is 100-150ms",
                    "Hallucination tolerance: zero for factual product info; higher for creative/conversational responses",
                    "Static knowledge (indexed once) vs dynamic (updated frequently) vs real-time (live API calls)",
                ],
            },
            {
                "name": "Knowledge Ingestion & Indexing",
                "prompt": "Describe the pipeline to ingest, chunk, embed, and index the knowledge base. What chunking strategy do you use and why?",
                "duration_seconds": 300,
                "key_areas": [
                    "Document pipeline: crawl/ingest → clean → chunk → embed → index",
                    "Chunking strategy: semantic chunking over fixed-size windows to preserve context boundaries",
                    "Embedding model: domain-tuned bi-encoder (e.g., E5-large or fine-tuned on Amazon QA pairs)",
                    "Index: FAISS HNSW for dense retrieval + Elasticsearch/BM25 for sparse",
                    "Metadata filtering: source domain, freshness timestamp, locale",
                ],
            },
            {
                "name": "Retrieval Architecture",
                "prompt": "Walk through the retrieval pipeline in detail. Cover hybrid retrieval, the two-stage approach, and how you handle voice-specific query challenges.",
                "duration_seconds": 420,
                "key_areas": [
                    "Stage 1: hybrid retrieval — dense ANN (FAISS) + sparse BM25 merged via Reciprocal Rank Fusion",
                    "Stage 2: cross-encoder reranker scores top-50 candidates jointly with query — selects top-5 passages",
                    "Voice query rewriting: ASR transcripts contain errors — query normalization and expansion before retrieval",
                    "Multi-hop queries: decompose into sub-queries, retrieve per-hop, merge context",
                    "Passage selection: if top passage score < threshold, fall back to parametric LLM knowledge",
                ],
            },
            {
                "name": "Grounding & Faithfulness",
                "prompt": "How do you ensure the LLM stays faithful to the retrieved context? Describe your grounding strategy, citation approach, and what happens when retrieval fails.",
                "duration_seconds": 300,
                "key_areas": [
                    "Grounding prompt: retrieved passages prepended with explicit instruction to only use provided context",
                    "Citation: LLM outputs claim-level source IDs; system appends source attribution in response",
                    "Faithfulness scoring: lightweight judge model checks response against passages — flags unsupported claims",
                    "Refusal strategy: if faithfulness score < threshold, respond with 'I don't have reliable information on that'",
                    "Confidence calibration: surface uncertainty language proportional to retrieval confidence score",
                ],
            },
            {
                "name": "Production, Freshness & Monitoring",
                "prompt": "How do you keep the knowledge base fresh? How do you route queries, and what do you monitor in production?",
                "duration_seconds": 300,
                "key_areas": [
                    "Freshness pipeline: incremental index updates for changed documents, full re-index weekly",
                    "Change detection: hash-based fingerprinting of source documents — only re-embed on change",
                    "Query routing at inference: if query confidence score high + latency budget tight → parametric LLM; otherwise → RAG",
                    "Monitoring: retrieval hit rate, faithfulness score distribution, hallucination rate (via judge), latency p50/p99",
                    "Multi-turn context: carry retrieved passages across turns for follow-up questions in same session",
                ],
            },
        ],
        "structured_probes": [
            "Your retrieval returns highly relevant passages but the LLM still hallucinates specific numbers and dates from those passages. Walk me through why this happens and how you fix it.",
            "An Alexa product spec changes — the device now has 4GB RAM not 2GB. How does your system detect that the indexed knowledge is stale and ensure the update propagates before users get wrong answers?",
            "A user asks: 'Is the director of that show I liked also directing any Amazon Prime Originals?' How does your retrieval pipeline handle this multi-hop query that requires bridging two knowledge domains?",
            "How do you decide at query time whether to route through RAG or rely purely on the LLM's parametric knowledge? Give me the exact logic and thresholds you'd use.",
        ],
    },
    {
        "subcategory": "Prime Video Personalization",
        "prompt_text": "Design a personalized recommendation system for Prime Video's homepage and post-play experience.",
        "context_hint": "Scope: candidate generation (two-tower), ranking (cross-encoder), multi-objective optimization, cold-start, A/B testing, online/offline eval gap. Your edge: two-tower retrieval, cross-encoder reranking (+0.192 NDCG), FAISS GPU eval, 8 model launches, multilingual.",
        "phases": [
            {
                "name": "Requirements & Success Metrics",
                "prompt": "Clarify the surfaces, success metrics, and constraints. What does 'good' look like, and how do you measure it?",
                "duration_seconds": 180,
                "key_areas": [
                    "Surfaces: homepage hero, genre rows, post-play autoplay, 'More like this' — different optimization targets per surface",
                    "Primary metric: watch-through rate (fraction of video actually watched) — clicks are cheap",
                    "Secondary metrics: session length, cross-genre exploration rate, subscription renewal as north star",
                    "Scale: 200M+ users, 10K+ titles, real-time personalization required",
                ],
            },
            {
                "name": "High-Level Architecture",
                "prompt": "Walk through the overall system architecture from user request to final ranked list. Name the stages and what each one does.",
                "duration_seconds": 240,
                "key_areas": [
                    "Candidate generation (two-tower ANN) → ranking (cross-encoder) → multi-objective blending → serving",
                    "Candidate gen: retrieves top-500 from catalog of 10K+ titles in <20ms",
                    "Ranking: cross-encoder scores each candidate jointly with user context — top-20 selected",
                    "Multi-objective blending: engagement + diversity + freshness + exploration signals combined",
                    "Serving: results cached per user with 1-hour TTL, invalidated on new watch event",
                ],
            },
            {
                "name": "Candidate Generation: Two-Tower",
                "prompt": "Deep dive into the two-tower model. Walk through the user tower, content tower, training strategy, and how you serve it at scale.",
                "duration_seconds": 420,
                "key_areas": [
                    "User tower: watch sequence (recent titles, genres, completion rates), temporal features, device/time-of-day context",
                    "Content tower: genre, cast, synopsis embedding, multimodal visual embedding from trailer keyframes (CLIP)",
                    "Shared 128-dim embedding space trained with InfoNCE loss on (user, watched_video) positives",
                    "FAISS HNSW index updated hourly; ANN search returns top-500 candidates in <20ms",
                    "Hard negative mining: include titles the user skipped or abandoned — critical for quality",
                ],
            },
            {
                "name": "Ranking & Multi-Objective Optimization",
                "prompt": "Explain the ranking stage and how you balance multiple objectives. How do you prevent engagement-only optimization from creating filter bubbles?",
                "duration_seconds": 360,
                "key_areas": [
                    "Cross-encoder features: retrieval score, temporal (time since last watched this genre), social signals, business signals (Prime Original boost)",
                    "Multi-objective: final_score = w1*engagement + w2*diversity_bonus + w3*freshness_bonus + w4*explore_bonus",
                    "Diversity bonus: rewards genres the user hasn't watched in >30 days",
                    "Exploration (Thompson sampling): promotes titles the model is uncertain about — decays as data accumulates",
                    "Weights tuned per surface via online experiments — homepage needs more diversity than post-play",
                ],
            },
            {
                "name": "Cold-Start, A/B Testing & Production",
                "prompt": "How do you handle new users and new titles? Describe your A/B testing setup and production monitoring.",
                "duration_seconds": 300,
                "key_areas": [
                    "New user cold-start: popularity-based recommendations segmented by acquisition channel → personalized after 5-10 views",
                    "New title cold-start: content tower produces embeddings from metadata alone; 2-week exploration boost that decays",
                    "A/B testing: holdout groups with pre-registered hypotheses; ship only if watch-through rate + retention both improve",
                    "Offline-online gap: offline NDCG predicts ranking quality but not business outcome — use both",
                    "Monitoring: embedding staleness alerts, recommendation diversity metrics, watch-through rate by user cohort",
                ],
            },
        ],
        "structured_probes": [
            "A new Prime Original launches with zero engagement data. How does your system decide how prominently to feature it on the homepage, and how do you prevent it from flooding recommendations for users who wouldn't like it?",
            "After 6 months you notice users are stuck in genre filter bubbles — someone who watched one thriller now only sees thrillers. Your engagement metrics look fine. How do you detect and fix this?",
            "A user binge-watches an entire season in one sitting. How do you update their recommendations in real-time during that session — what triggers the update and what changes in the model?",
            "How would you evaluate this recommendation system offline before a production launch? What's your primary offline metric, what does it miss, and how do you bridge the offline-online gap?",
        ],
    },
    {
        "subcategory": "Amazon Search",
        "prompt_text": "Design the ML ranking system for Amazon product search at scale.",
        "context_hint": "Scope: query understanding, hybrid retrieval (BM25 + dense), learning-to-rank, personalization layer, ad integration, A/B testing, latency budget. Your edge: two-tower retrieval, cross-encoder reranking, NDCG optimization, multilingual query handling.",
        "phases": [
            {
                "name": "Requirements & Scope",
                "prompt": "Clarify the query types, success metrics, scale, and personalization requirements before designing anything.",
                "duration_seconds": 180,
                "key_areas": [
                    "Query types: text (80%), voice (15%), image (5%) — different preprocessing pipelines",
                    "Success metrics: add-to-cart rate and purchase rate, not click-through (clicks are cheap)",
                    "Scale: billions of products, millions of QPS, 100ms p99 latency SLA",
                    "Personalization: must account for user's purchase history, browsing behavior, geographic context",
                ],
            },
            {
                "name": "System Architecture Overview",
                "prompt": "Walk through the full pipeline from query to ranked results. Name every stage, what it does, and its latency budget.",
                "duration_seconds": 240,
                "key_areas": [
                    "Query understanding (10ms): spelling correction, query normalization, intent classification, entity extraction",
                    "Candidate retrieval (20ms): hybrid BM25 + dense bi-encoder → top-1000 candidates via ANN",
                    "L1 ranking (30ms): lightweight LTR model scores top-1000, selects top-100",
                    "L2 ranking (30ms): heavy cross-encoder with full feature set scores top-100, selects top-30",
                    "Post-ranking (10ms): ad injection, diversity enforcement, business rule application → final results",
                ],
            },
            {
                "name": "Retrieval: Hybrid Sparse + Dense",
                "prompt": "Deep dive into the retrieval layer. Explain hybrid retrieval, how you handle product embeddings, and what makes this hard at Amazon's scale.",
                "duration_seconds": 360,
                "key_areas": [
                    "BM25 (Elasticsearch): exact match, handles rare/tail queries well, fast but no semantic understanding",
                    "Dense bi-encoder: product embedding from title + description + category + structured attributes (price range, brand)",
                    "Hybrid fusion: Reciprocal Rank Fusion merges BM25 and dense candidates — better than either alone",
                    "Query expansion: synonym expansion, spelling correction before retrieval — 'iphone charger' → 'iPhone USB-C cable'",
                    "Scale challenge: index of 500M+ products; FAISS HNSW with GPU serving, shard by category for latency",
                ],
            },
            {
                "name": "Learning-to-Rank & Personalization",
                "prompt": "Explain your ranking model architecture, training signal, feature set, and how personalization is injected.",
                "duration_seconds": 420,
                "key_areas": [
                    "Training signal: (query, product, label) triples — label = purchase (3), add-to-cart (2), click (1), impression (0)",
                    "L1 model: GBDT (XGBoost) — fast, interpretable, handles sparse features well",
                    "L2 model: cross-encoder transformer — jointly encodes query + product title/description for deep text matching",
                    "Feature groups: text match (BM25 score, semantic sim), behavioral (CTR, purchase rate by query-product pair), product quality (rating, review count, freshness), seller (fulfillment speed, return rate)",
                    "Personalization: user embedding from purchase/browse history concatenated to L2 features; real-time session signals (what they viewed in last 30 min)",
                ],
            },
            {
                "name": "Production, Ads & Monitoring",
                "prompt": "How do you integrate sponsored listings without degrading organic quality? What do you monitor, and how do you ensure fairness across sellers?",
                "duration_seconds": 300,
                "key_areas": [
                    "Ad integration: sponsored products must pass a relevance threshold before insertion — prevents pure pay-to-play",
                    "Ad placement: slots 1, 5, 9 reserved for sponsored products that pass relevance gate; organic results fill remaining slots",
                    "Fairness monitoring: track purchase rate and add-to-cart rate by seller tier — alert if small sellers systematically disadvantaged",
                    "Latency monitoring: p50/p95/p99 per pipeline stage — isolate which stage is causing spikes",
                    "Experiment framework: pre-registered metrics, holdout groups, ship only if purchase rate + fairness metrics both hold",
                ],
            },
        ],
        "structured_probes": [
            "A search for 'apple' returns mostly Apple Electronics but the user meant the fruit. Walk me through exactly how your query understanding layer detects and resolves this ambiguity.",
            "How do you integrate sponsored product listings into the ranking pipeline without tanking organic search quality? Walk me through the exact flow and what guardrails prevent pay-to-play from dominating results.",
            "Your p99 search latency spikes from 80ms to 800ms during a flash sale. Walk me through your systematic debugging process and the immediate mitigation steps you'd take.",
            "After 6 months you discover your L2 ranking model systematically favors established brands over small sellers at equal quality. How do you detect this, root-cause it, and fix it without breaking relevance?",
        ],
    },
    {
        "subcategory": "Amazon Retail Cold Start",
        "prompt_text": "Design an ML system to recommend complementary products for brand-new catalog items with no interaction history.",
        "context_hint": "Scope: cold-start retrieval and ranking, content-based vs generative approaches, hallucination control, evaluation before online traffic, feedback loops as data arrives. Your edge: generative retrieval, two-tower retrieval, cross-encoder reranking, LLM-generated shopping intents.",
        "phases": [
            {
                "name": "Requirements & Success Metrics",
                "prompt": "Clarify the business problem, surfaces, and success metrics. What counts as a good complementary recommendation for a brand-new item?",
                "duration_seconds": 180,
                "key_areas": [
                    "Surfaces: PDP carousels, add-to-cart upsell, email follow-ups, search refinement",
                    "Primary metric: attach rate or add-to-cart lift, not click-through alone",
                    "Cold-start constraint: zero co-view / co-purchase history for the new item",
                    "Guardrails: low irrelevance rate, diversity across categories, seller / price appropriateness",
                ],
            },
            {
                "name": "Candidate Generation Strategy",
                "prompt": "How do you generate candidates when collaborative signals do not exist yet? Compare content-based retrieval, taxonomy rules, and generative retrieval.",
                "duration_seconds": 300,
                "key_areas": [
                    "Content-based candidates from item title, brand, category, structured attributes, and catalog graph neighbors",
                    "Taxonomy / rules baseline for high-precision complements in known verticals",
                    "Generative retrieval path: LLM generates shopping intents or synthetic queries from item attributes",
                    "Hybrid candidate pool merged from rules + dense retrieval + generated-query retrieval",
                    "Metadata quality checks to avoid generating nonsense from bad catalog attributes",
                ],
            },
            {
                "name": "Ranking & Model Architecture",
                "prompt": "Walk through the ranking stage. What models and features would you use when the anchor item is new but candidate items have historical data?",
                "duration_seconds": 420,
                "key_areas": [
                    "Two-tower or embedding retrieval for recall, cross-encoder or LTR model for reranking",
                    "Anchor item features: title, category, price band, brand, textual attributes, image embedding",
                    "Candidate features: historical quality, conversion, return rate, inventory, shipping speed",
                    "Pairwise compatibility features: category complementarity, price-range compatibility, brand / use-case coherence",
                    "Uncertainty-aware ranking: penalize high-variance generated intents until validated",
                ],
            },
            {
                "name": "Evaluation & Launch Gating",
                "prompt": "How would you evaluate this before sending traffic? Cover offline evaluation, human review, and online experimentation.",
                "duration_seconds": 300,
                "key_areas": [
                    "Offline set from historical item launches replayed as synthetic cold-start examples",
                    "Metrics: precision@k / NDCG plus attach-rate prediction and diversity",
                    "Human evaluation or LLM-as-judge for semantic complementarity and irrelevance detection",
                    "Launch gating with conservative buckets first: only high-confidence categories or traffic slices",
                    "A/B test success requires attach-rate lift without harming main-item conversion",
                ],
            },
            {
                "name": "Production Feedback Loop",
                "prompt": "Once the item accumulates interactions, how does the system transition from pure cold-start logic to normal recommendation logic?",
                "duration_seconds": 300,
                "key_areas": [
                    "Progressive handoff from cold-start features to collaborative signals as data arrives",
                    "Bandit or exploration policy to gather signal without flooding low-quality candidates",
                    "Monitoring: hallucinated intents, sparse-category failures, seller bias, stale metadata",
                    "Rollback strategy if generated intents create irrelevant or unsafe recommendations",
                    "Retraining cadence and feature-store updates as new item interaction data accumulates",
                ],
            },
        ],
        "structured_probes": [
            "Your LLM generates the query 'gaming setup accessories' for a desk lamp, and retrieval returns mostly irrelevant electronics. How do you detect that failure and prevent it from reaching users?",
            "A new item has poor metadata: missing brand, sparse attributes, and a generic title. What fallback path does your system use, and how do you avoid complete cold-start failure?",
            "How do you decide when an item has enough real interaction data to stop relying on generated intents and switch to collaborative signals?",
            "Your online test improves attach rate but also increases product returns because the complements are semantically related but not actually compatible. How do you diagnose and fix that?",
        ],
    },
    {
        "subcategory": "LLM Judge Evaluation Platform",
        "prompt_text": "Design an ML evaluation system that uses LLM-as-judge to assess the quality of LLM-generated recommendations or responses before launch.",
        "context_hint": "Scope: rubric design, calibration, judge-human agreement, offline-online correlation, cost control, drift, and launch gating. Your edge: LLM-as-judge evaluation, rubric design, backtesting against failed launches, offline-to-online validation.",
        "phases": [
            {
                "name": "Requirements & Quality Taxonomy",
                "prompt": "Clarify what outputs are being judged, what quality dimensions matter, and how the evaluation will be used in launch decisions.",
                "duration_seconds": 180,
                "key_areas": [
                    "Outputs: recommendation lists, generated queries, summaries, conversational answers",
                    "Quality dimensions: relevance, diversity, novelty, safety, faithfulness, business-rule compliance",
                    "Decision use case: regression testing, model selection, launch approval, drift detection",
                    "Need for structured rubric per product surface rather than one universal judge prompt",
                ],
            },
            {
                "name": "Judge Architecture & Rubrics",
                "prompt": "Describe the judge system itself. How do you structure rubrics, prompts, and outputs so the judge is reliable and actionable?",
                "duration_seconds": 300,
                "key_areas": [
                    "Surface-specific rubrics with dimension-level 1-5 scoring and rationale",
                    "Structured JSON outputs for per-dimension score, overall score, and explanation",
                    "Context packaging: anchor item / user intent / candidate outputs / metadata",
                    "Ensembling options: multiple judge prompts or models to reduce variance on high-stakes cases",
                    "Cost controls: judge only sampled traffic or candidate launch sets, not all production requests",
                ],
            },
            {
                "name": "Calibration & Human Validation",
                "prompt": "How do you know the judge is measuring something real rather than matching prompt patterns? Cover calibration against humans and disagreement handling.",
                "duration_seconds": 420,
                "key_areas": [
                    "Human-labeled gold set per surface and locale with clear annotation guidelines",
                    "Agreement metrics: weighted kappa / Spearman / pairwise win-rate vs human preference",
                    "Calibrate thresholds so a score maps to decision classes: ship, investigate, block",
                    "Disagreement workflow: route edge cases to human review and refine the rubric",
                    "Bias checks by locale, language, and product category to catch systematic judge skew",
                ],
            },
            {
                "name": "Offline-Online Correlation & Launch Gates",
                "prompt": "How does this evaluation platform connect to real business outcomes? Explain how you validate that offline judge scores predict online success.",
                "duration_seconds": 300,
                "key_areas": [
                    "Backtest against prior launches with known winners / losers to measure predictive power",
                    "Correlate judge metrics with CTR, conversion, attach rate, retention, or complaint rate depending on surface",
                    "Use judge scores as launch gate input, not sole decision-maker, alongside business guardrails",
                    "Detect reward hacking: models optimizing to the judge without improving real user outcomes",
                    "Maintain holdout human review even after the judge looks strong",
                ],
            },
            {
                "name": "Production Monitoring & Drift",
                "prompt": "Once deployed, how do you monitor the evaluation platform itself? Cover drift, cost, and incident response.",
                "duration_seconds": 300,
                "key_areas": [
                    "Judge drift monitoring: score distribution shifts after base model or prompt updates",
                    "Periodic refresh of gold sets and re-calibration after product changes",
                    "Cost and latency budgeting with tiered evaluation depth for high-risk launches",
                    "Fallback path if judge quality degrades: revert to human review or simpler heuristics",
                    "Auditability: store rubric version, judge prompt version, and evidence for launch decisions",
                ],
            },
        ],
        "structured_probes": [
            "Your judge gives high scores to a model that later fails badly in A/B testing. Walk me through the possible failure modes and how you would recalibrate the platform.",
            "Human reviewers in Germany consistently disagree with the judge while US reviewers agree. How do you determine whether the issue is locale bias, annotation inconsistency, or prompt design?",
            "A team starts optimizing directly against your judge score and offline results improve, but customer complaints rise. How do you detect this reward-hacking dynamic and respond?",
            "How do you decide which launches need the expensive full judge rubric versus a cheaper heuristic or sampled evaluation path?",
        ],
    },
]

def _add_breakdown_phases(design_q: dict) -> dict:
    """Add breakdown phase rubric dimensions to a design question's phases.

    Maps the existing 5-phase Stand & Deliver phases into a 7-phase breakdown
    using the BREAKDOWN_PHASE_TEMPLATES for rubric dimensions. The existing
    phase names/prompts/key_areas are preserved; breakdown rubric dims are added.
    """
    # Build breakdown_phases from the template, merging question-specific key_areas
    breakdown_phases = []
    existing_phases = design_q.get("phases", [])

    for i, template in enumerate(BREAKDOWN_PHASE_TEMPLATES):
        phase = dict(template)
        # If there's a matching existing phase by index, use its key_areas
        if i < len(existing_phases):
            phase["key_areas"] = existing_phases[i].get("key_areas", template["key_areas"])
            # Use existing prompt if it's more specific
            if existing_phases[i].get("prompt"):
                phase["prompt"] = existing_phases[i]["prompt"]
            if existing_phases[i].get("name"):
                phase["name"] = existing_phases[i]["name"]
            if existing_phases[i].get("duration_seconds"):
                phase["duration_seconds"] = existing_phases[i]["duration_seconds"]
        breakdown_phases.append(phase)

    design_q["breakdown_phases"] = breakdown_phases
    return design_q


for q in design_questions:
    q = _add_breakdown_phases(q)
    questions.append({
        "category": "design",
        "subcategory": q["subcategory"],
        "prompt_text": q["prompt_text"],
        "context_hint": q["context_hint"],
        "rubric_dimensions": DESIGN_RUBRIC,
        "target_duration_seconds": 1500,
        "sort_order": sort_order,
        "phases": q["phases"],  # Original 5-phase Stand & Deliver phases
        "breakdown_phases": q["breakdown_phases"],  # 7-phase breakdown with rubric dims
        "structured_probes": q["structured_probes"],
    })
    sort_order += 1


def main():
    # Upsert all questions — existing rows updated in place, new rows inserted.
    # Uses (category, prompt_text) as the natural key (unique index).
    # NEVER deletes existing data.
    print(f"Upserting {len(questions)} questions...")

    for i, q in enumerate(questions):
        supabase.table("onsite_prep_questions").upsert(
            q,
            on_conflict="category,prompt_text",
        ).execute()
        if (i + 1) % 10 == 0 or i == len(questions) - 1:
            print(f"  Upserted {i + 1}/{len(questions)}")

    # Verify
    result = supabase.table("onsite_prep_questions").select("category", count="exact").execute()
    print(f"\nTotal questions in DB: {result.count}")

    # Count by category
    for cat in ["lp", "breadth", "depth", "design"]:
        result = supabase.table("onsite_prep_questions").select("id", count="exact").eq("category", cat).execute()
        print(f"  {cat}: {result.count}")

    print("\nDone! (upsert — no data was deleted)")


if __name__ == "__main__":
    main()
