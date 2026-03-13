# MLE System Design Flow

## Goal

Keep system design separate from LeetCode while making MLE interview prep much more targeted.

The primary flow stays:

1. Dashboard is the main entry point.
2. User starts or resumes one oral session.
3. Session contains 3 audio-first questions.
4. User gets graded feedback after each answer.
5. Session summary highlights weak dimensions and missed concepts.
6. Future review cards become optional follow-up drills, not the main loop.

## Product Principles

- Audio is the primary input because it matches interview conditions.
- MLE topics should be modern and explicit: ranking, retrieval, LLM systems, RL, training infra, monitoring, safety, experimentation.
- Sessions should be topic-shaped, not always the same generic structure.
- Review cards should be secondary and concrete.

## Proposed Information Architecture

### Dashboard card

The dashboard card should answer:

- What topic am I practicing today?
- Am I starting fresh or resuming a session?
- Why does this topic matter?
- What happens after I click?

Suggested content:

- Active track: `Modern MLE System Design`
- Today's topic: `RLHF Policy Training`
- Session shape: `3 oral questions`, `12-15 min`, `audio graded`
- Secondary note: `2 follow-up drills unlocked from prior sessions`

Primary CTA:

- `Start today's oral session` or `Resume oral session`

Secondary CTA:

- `Preview session`

Tertiary area:

- `Bonus review cards`

## Session Flow

### 1. Dashboard

The user lands on the dashboard and sees:

- current MLE topic
- short topic rationale
- estimated time
- previous session status if one exists
- optional follow-up cards from earlier weak areas

### 2. Session Brief

Before recording starts, show:

- topic name
- interview framing
- what the 3 questions cover
- what strong answers usually include

For RL topics, question shapes can vary by topic. Example:

- Q1: reward design and data generation
- Q2: training loop and policy optimization
- Q3: serving, monitoring, rollback, and safety

### 3. Question Recording

Each question page should show:

- focused prompt
- 3-5 key concepts
- suggested time box
- record or upload audio

The UI should make it obvious this is one part of a 3-question interview block.

### 4. Per-question Feedback

After grading, show:

- overall score
- dimension scores
- strongest moment
- weakest moment
- missed concepts
- 2 follow-up interviewer questions

This is where the user learns what they missed while the answer is still fresh.

### 5. Session Summary

After all 3 questions:

- aggregate score
- top weak dimensions
- top missed concepts
- recommendation for next topic or next drill

This screen should also generate secondary review cards.

## Review Cards

Review cards should not replace the main oral session. They should be bonus targeted drills created from weak performance.

Bad review card:

- `RLHF Policy Training - Technical Depth`

Better review cards:

- `RLHF Policy Training - Reward Hacking Failure Modes`
- `RLHF Policy Training - GRPO vs PPO Tradeoffs`
- `RLHF Policy Training - Rollback Triggers for Online Policy Launch`

Each review card should contain:

- subskill label
- one focused drill prompt
- expected answer mode: `2-4 min audio`
- reason it was generated

## Subskill Taxonomy

Initial MLE taxonomy:

- Capacity estimation
- Data modeling
- Retrieval and ranking tradeoffs
- Training and serving split
- Evaluation and experimentation
- Monitoring and drift
- Reliability and rollback
- Cost and latency tradeoffs
- Safety and guardrails
- RL reward design
- RL training loop mechanics
- RL offline or online evaluation
- RL policy serving and exploration control

## Topic Families

The first MLE track should cover:

- Retrieval and ranking systems
- Recommender systems
- Ads systems
- Feature stores and data freshness
- Training pipelines and orchestration
- Online inference and model serving
- Experimentation platforms
- Monitoring, drift, and alerting
- LLM application systems
- LLM eval and safety
- Bandits and exploration systems
- RLHF and policy optimization systems
- Modern RL training infrastructure

## RL Topic Example

Topic: `RLHF Policy Training`

Suggested 3-question session:

1. Design the data and reward pipeline for collecting preference data and constructing training batches.
2. Walk through the training loop, including reward model updates, policy optimization, stability issues, and why you would choose PPO or GRPO.
3. Explain how you would serve the updated policy safely in production, monitor regressions, and define rollback triggers.

Possible follow-up review cards:

- `GRPO vs PPO tradeoffs under limited online feedback`
- `Reward hacking detection and mitigation`
- `Serving policy updates with rollback gates`

## Recommendation

For implementation, keep the existing one-session-three-questions model but evolve it in this order:

1. Make the dashboard card more explicit about what session the user is entering.
2. Make question generation topic-aware for MLE domains.
3. Make the session summary produce focused follow-up review cards.
4. Keep review cards optional until the main oral flow feels strong.
