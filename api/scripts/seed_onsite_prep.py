#!/usr/bin/env python3
"""Seed onsite_prep_questions from the amazon-prep markdown files.

Usage:
    cd api && python scripts/seed_onsite_prep.py

Idempotent: deletes all existing questions and re-inserts.
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
     "Redesigning the DS/MLOps Operating Model — changed handoff workflow so DS owns pipeline code, MLOps owns reliability. Joint design reviews, shared design docs, validation contracts."),
    ("Earn Trust",
     "Describe a time you had to deliver difficult or unpopular feedback to a stakeholder.",
     "Embedding Pipeline Bug — owned mistake immediately, ran blameless post-mortem, drafted org-wide shareout"),
    ("Have Backbone; Disagree & Commit",
     "Tell me about a time you disagreed with your manager or team on a technical direction.",
     "LLM-based vs pure embedding architecture. Built both preemptively, presented comparative results."),
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

# ── System Design (2 prompts) ──

design_questions = [
    ("Alexa ASCI", "Design a trust & safety evaluation system for Alexa+ LLM responses.",
     "Scope: safety taxonomy, multi-layer filtering, LLM-as-judge for safety scoring, real-time vs batch evaluation, drift monitoring, locale-specific compliance, rollback triggers. Your edge: 3-layer content safety at Walmart, locale compliance (CA/MX), drift detection."),
    ("Prime Video Search", "Improve video discovery for Prime Video through personalized search & recommendation.",
     "Scope: candidate generation (two-tower), ranking (cross-encoder), embedding strategy, cold-start, multi-objective optimization, A/B testing, online/offline eval gap. Your edge: two-tower retrieval, cross-encoder reranking (+0.192 NDCG), FAISS GPU eval, 8 model launches, multilingual."),
]

for subcat, prompt_text, context_hint in design_questions:
    questions.append({
        "category": "design",
        "subcategory": subcat,
        "prompt_text": prompt_text,
        "context_hint": context_hint,
        "rubric_dimensions": DESIGN_RUBRIC,
        "target_duration_seconds": 480,
        "sort_order": sort_order,
    })
    sort_order += 1


def main():
    # Delete existing questions (idempotent)
    print("Deleting existing onsite_prep_questions...")
    supabase.table("onsite_prep_questions").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

    # Insert all questions
    print(f"Inserting {len(questions)} questions...")

    # Insert in batches of 20
    for i in range(0, len(questions), 20):
        batch = questions[i:i+20]
        supabase.table("onsite_prep_questions").insert(batch).execute()
        print(f"  Inserted {min(i+20, len(questions))}/{len(questions)}")

    # Verify
    result = supabase.table("onsite_prep_questions").select("category", count="exact").execute()
    print(f"\nTotal questions in DB: {result.count}")

    # Count by category
    for cat in ["lp", "breadth", "depth", "design"]:
        result = supabase.table("onsite_prep_questions").select("id", count="exact").eq("category", cat).execute()
        print(f"  {cat}: {result.count}")

    print("\nDone!")


if __name__ == "__main__":
    main()
