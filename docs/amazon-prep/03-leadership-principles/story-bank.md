# Story Bank — Full Inventory

All STAR stories with LP tags. Organized by project/domain for easy reference.

**Target: 9 confirmed LPs x 2 stories each = 18 stories minimum.**
**Current: 15 stories written. ~9 assigned as primaries. Need ~9 backups.**

---

## CONFIRMED LP ASSIGNMENTS

### Primary Stories (from existing answers.md)

| LP | Primary Story | Source |
|----|--------------|--------|
| Insist on Highest Standards | Spanish long-tail regression block (9-day delay) | Walmart Search |
| Bias for Action | Content safety threshold incident (Friday fix) | Walmart Safety |
| GenAI Fluency | **NEEDS NEW STORY** | — |
| Ownership | A/B test bucketing fix (French-Canadian) | Walmart Search |
| Earn Trust | Query rewriting module feedback (private, data-driven) | Walmart Search |
| Have Backbone | GPT-4 vs Llama 70B dual-model pushback | Walmart RL |
| Learn & Be Curious | Bench scientist → production ML (Synthego) | Synthego |
| Dive Deep | Cross-encoder mobile latency root cause | Walmart Search |
| Deliver Results | 8 model launches, $100M+ campaign | Walmart Search |

### Backup Stories Needed

| LP | Backup Story | Status |
|----|-------------|--------|
| Insist on Highest Standards | <!-- TO FILL --> | needed |
| Bias for Action | <!-- TO FILL --> | needed |
| GenAI Fluency | <!-- TO FILL --> | needed |
| Ownership | <!-- TO FILL --> | needed |
| Earn Trust | <!-- TO FILL --> | needed |
| Have Backbone | <!-- TO FILL --> | needed |
| Learn & Be Curious | <!-- TO FILL --> | needed |
| Dive Deep | <!-- TO FILL --> | needed |
| Deliver Results | <!-- TO FILL --> | needed |

---

## STORY INVENTORY BY PROJECT

### Walmart — Intent-Based Recommendation System

**Story: Hybrid Two-Tower + Async LLM Architecture**
- **Currently assigned to:** (available — was Customer Obsession + Think Big)
- **Summary:** Proposed and built intent-based reco using LLM queries + two-tower retrieval. Balanced ambition with latency constraints. 46% relevance improvement.
- **Key metrics:** 46% relevance improvement, 3 language markets, 200ms p95 latency ceiling
- **Good for:** GenAI Fluency, Think Big, Customer Obsession, Invent & Simplify

**Story: LLM-as-Judge for RL Training Loop**
- **Currently assigned to:** (available — was Are Right A Lot)
- **Summary:** Advocated for LLM-as-judge over human annotation. Pilot showed 0.85+ correlation. 10x faster iteration. Adopted by 2 other teams.
- **Key metrics:** $15K/cycle savings, 2 weeks → hours, 0.85+ correlation
- **Good for:** GenAI Fluency, Are Right A Lot, Invent & Simplify

---

### Walmart — Search Ranking Models

**Story: Cross-Encoder Latency Root Cause**
- **Currently assigned to:** Dive Deep (primary)
- **Summary:** Found mobile tokenization bottleneck causing 20% fallback to baseline. Fixed p99 from 50ms to 40ms. Saved entire model launch.
- **Key metrics:** +0.192 NDCG, 19 bps GMV lift, $100M+ annual impact

**Story: Spanish Long-Tail Regression Block**
- **Currently assigned to:** Insist on Highest Standards (primary)
- **Summary:** Blocked model launch due to 4% Spanish long-tail degradation despite aggregate improvement. Fixed in 9 days. Established per-locale eval standard.
- **Key metrics:** 30% of MX search volume affected, 9-day delay, $100M+ impact preserved

**Story: 8 Model Launches Campaign**
- **Currently assigned to:** Deliver Results (primary)
- **Summary:** 18-month campaign: DistilBERT → BERT → GTE. 8 flagship launches, each 15-20 bps. CIKM 2024 publication.
- **Key metrics:** 8 launches, 15-20 bps each, $100M+ per release, CIKM 2024

**Story: FAISS GPU Evaluation Framework**
- **Currently assigned to:** (available — was Invent & Simplify)
- **Summary:** Built GPU-accelerated evaluation reducing model launch eval from days to hours. Became org standard.
- **Key metrics:** 10x speedup, 2-3 days → 4 hours, enabled 8 launches

**Story: A/B Test Bucketing Fix (French-Canadian)**
- **Currently assigned to:** Ownership (primary)
- **Summary:** Audited cross-team A/B framework to find locale-specific bucketing bug. Saved model that appeared to fail.
- **Key metrics:** 17 bps GMV lift revealed after fix

---

### Walmart — Content Safety

**Story: Production Safety Threshold Incident**
- **Currently assigned to:** Bias for Action (primary)
- **Summary:** Friday afternoon content safety incident — model drift flagging legitimate Canadian products. Quick threshold adjustment, full fix Monday.
- **Key metrics:** Restored visibility in 1 hour, prevented weekend revenue loss

**Story: Multi-Layer Safety Architecture**
- **Currently assigned to:** (available — was Success & Scale)
- **Summary:** Designed 3-layer content safety (input filtering → output analysis → drift detection) with locale-specific compliance for CA and MX.
- **Key metrics:** <2% false positive rate, passed CA and MX compliance audits
- **Good for:** GenAI Fluency, Ownership, Deliver Results

---

### Walmart — Team Leadership

**Story: Developing Junior DS to Model Launch Owner**
- **Currently assigned to:** (available — was Hire & Develop)
- **Summary:** Structured growth plan for junior DS. Paired on BERT project, then gave ownership. She led a launch (18 bps) within 8 months.
- **Key metrics:** 18 bps GMV lift on her launch, VP recognition, now mentoring intern

**Story: Practice Run Slots + Presentation Rotation**
- **Currently assigned to:** (available — was Best Employer)
- **Summary:** Created low-stakes practice sessions and quarterly presentation rotation. Top quartile engagement scores.
- **Key metrics:** All 3 reports presented to org, top quartile engagement

**Story: Query Rewriting Module Feedback**
- **Currently assigned to:** Earn Trust (primary)
- **Summary:** Private, data-driven feedback to senior engineer about intent drift in greedy decoding. Proposed relevance gate. Co-authored tech brief.
- **Key metrics:** 12% of rewrites caught by gate

---

### Walmart — Cost Optimization

**Story: Dual-Model LLM Strategy (GPT-4 vs Llama 70B)**
- **Currently assigned to:** Have Backbone (primary)
- **Summary:** Pushed back on Director's GPT-4 standardization with cost data. Won approval for dual-model approach.
- **Key metrics:** $200K annual savings, $45K → $2K per training run, 3 days → 4 hours

---

### Synthego — Early Career

**Story: Bench Scientist to Production ML Engineer**
- **Currently assigned to:** Learn & Be Curious (primary)
- **Summary:** PhD biologist → production ML in 4 months through structured self-learning and pair programming.
- **Key metrics:** Independent in 4 months, tech lead by year 2

**Story: Microscopy Classifier on Spot Instance**
- **Currently assigned to:** (available — was Frugality)
- **Summary:** Built 94% accurate CV classifier with 2K images on a single AWS spot instance. Total dev cost <$200.
- **Key metrics:** 94% accuracy, <$200 total cost, <$100/month production

---

## UNASSIGNED STORIES (available for backup slots)

| Story | Best Fit LPs |
|-------|-------------|
| Hybrid Two-Tower + Async LLM | GenAI Fluency, Ownership |
| LLM-as-Judge for RL Loop | GenAI Fluency, Have Backbone |
| FAISS GPU Eval Framework | Deliver Results, Bias for Action |
| Multi-Layer Safety Architecture | GenAI Fluency, Ownership |
| Junior DS Development | Earn Trust, Learn & Be Curious |
| Practice Run Slots | Earn Trust |
| Microscopy Classifier | Bias for Action, Deliver Results |

---

## STORIES STILL NEEDED (from interactive sessions)

We need ~4-6 new stories to fill remaining backup slots. Candidates to mine:
- [ ] A GenAI-specific story for GenAI Fluency primary
- [ ] A "dove deep into unfamiliar system" backup for Dive Deep
- [ ] A "delivered despite obstacles" backup for Deliver Results
- [ ] A "learned new tech rapidly" backup for Learn & Be Curious
- [ ] Any other stories that surface during mining sessions
