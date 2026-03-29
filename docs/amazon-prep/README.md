# Amazon Onsite Interview — Deep Review

Prep material for a 5-slot Amazon Applied Scientist onsite loop. Two target roles: **Prime Video Search Science** (Personalization & Discovery) and **Alexa ASCI** (Responsible AI / Content Safety).

## Interview Structure

| Slot | Technical Focus | Leadership Principles |
|------|----------------|----------------------|
| #1 | Behavioral-only | Ownership + Have Backbone; Disagree & Commit + Bias for Action |
| #2 | Coding | Insist on Highest Standards + Deliver Results |
| #3 | ML Depth (Rec/Retrieval) | Invent & Simplify + Dive Deep |
| #4 | ML Breadth | Learn & Be Curious + Earn Trust |
| #5 | ML Application (real-world) | Think Big + Are Right, A Lot |

**11 LPs tested. Each needs 2+ STAR stories. Total target: ~22-25 polished stories.**

## Sections

### 00 — Role Analysis
Why each role, how your experience maps, questions to ask interviewers.

### 01 — Resume Defense (30 questions)
Every major resume claim with a polished, defensible answer. Covers: recommendation & retrieval, LLM-as-judge & RL, content safety, search ranking, ML infrastructure, and Synthego.

### 02 — Science Breadth (30 questions)
Graduate-depth ML fundamentals including LLM/conversational AI topics. Original 20 questions + 10 new from recruiter's sample list.

### 03 — Leadership Principles (~27 stories)
Expanded from 16 to ~27 STAR stories. Primary + backup for each tested LP. Includes slot mapping and story bank for quick reference.

### 04 — RL Techniques (deep dive)
REINFORCE, PPO, GRPO, DPO, rejection sampling, RLAIF. Tradeoff matrix, decision tree, interview sound bites.

### 05 — ML Depth: Recommendation & Retrieval
60-minute deep-dive prep. Two-tower retrieval, embeddings, ANN search, cold start, multi-objective ranking, cross-encoder vs bi-encoder.

### 06 — ML Application: System Design
Two end-to-end system designs:
- Prime Video recommendation system
- Alexa trust & safety evaluation system

### 07 — Coding
NLP-flavored coding problems matching recruiter examples. Token budget packing, intent confidence aggregation, and more.

## How to Use

1. Open `questions.md` for any section
2. Answer each question out loud or in your head
3. Check your answer against `answers.md`
4. Star or highlight any question where your answer was weak — revisit those first

## Key Numbers to Memorize

| Metric | Value | Context |
|--------|-------|---------|
| Relevance improvement | 46% | Intent-based reco vs co-purchase baseline |
| GMV lift per model | 15-20 bps | Each of 8 search model launches |
| Annual impact | $100M+ | Per search model release |
| NDCG improvement | +0.192 | Cross-encoder vs previous ranker |
| Eval speedup | 10x | FAISS GPU-accelerated framework |
| Languages | 3 | EN/FR/ES across US/CA/MX |
| Model launches | 8 | Flagship search models shipped |
| Direct reports | 3 | Junior to senior level |
| Publication | CIKM 2024 | First-author, relevance filtering for EBR |

## Study Plan

See `ONSITE-STUDY-PLAN.md` for the day-by-day review schedule.
