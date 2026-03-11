# Oral System Design Grading Rubric — Draft

## Dimensions (5, each scored 1-10)

### 1. Technical Depth
How deep does the candidate go beyond "I'd use X"?

**Score anchors:**
- **2-3 (Surface):** Names technologies without justification. "I'd use Kafka." No discussion of why, configuration, or failure modes.
- **4-5 (Shallow):** Mentions technologies with basic rationale but doesn't explore edge cases or quantify. "I'd use Kafka because it handles high throughput" — but no partition strategy, no retention discussion, no numbers.
- **6-7 (Solid):** Discusses specific configurations, capacity estimates, or failure scenarios for at least some components. "We'd partition by user_id, set 7-day retention, and need roughly 50K events/sec based on 100M DAU with 500 interactions/day."
- **8-9 (Expert):** Proactively addresses failure modes, capacity planning with math, and implementation details that show real experience. Discusses what breaks at scale and how to mitigate.

### 2. Structure & Approach
Does the candidate have a framework, or are they stream-of-consciousness?

**Score anchors:**
- **2-3 (Chaotic):** Jumps between topics randomly. No clear sections. Hard to follow the thread of the argument. Starts implementing before scoping.
- **4-5 (Loose):** Has a general direction but backtracks frequently. Some logical flow but no explicit structure. "Oh wait, I should have mentioned..."
- **6-7 (Organized):** Clear sections (requirements → high-level design → deep dive). Signposts transitions. "Now let me talk about the storage layer." Covers the question scope without major tangents.
- **8-9 (Exemplary):** Opens with clarifying the scope/requirements, states assumptions explicitly, builds from high-level to detail systematically. Easy to follow even without visual aids.

### 3. Trade-off Reasoning
Does the candidate weigh alternatives, or just present one solution?

**Score anchors:**
- **2-3 (None):** Presents one solution as if it's the only option. No "alternatively" or "the tradeoff here is."
- **4-5 (Surface):** Mentions that alternatives exist but doesn't deeply compare. "You could also use Redis but I'd go with Memcached" — without explaining why.
- **6-7 (Thoughtful):** Explicitly compares 2+ options on specific criteria (latency, cost, consistency). "DynamoDB gives us single-digit ms reads at scale but limits our query patterns. Postgres gives flexibility but we'd need read replicas for this throughput."
- **8-9 (Rigorous):** Frames decisions as trade-off matrices. Discusses when their choice would be wrong. "If our access pattern shifts to more ad-hoc queries, we'd need to revisit this — probably move to a hybrid approach."

### 4. ML/Data Fluency (for MLE/DE tracks)
Does the candidate demonstrate working knowledge of ML systems and data pipelines?

**Score anchors:**
- **2-3 (Textbook):** Mentions ML concepts by name only. "We'd use collaborative filtering." No discussion of features, training, serving, or evaluation.
- **4-5 (Basic):** Understands the ML pipeline at a high level but stays abstract. Mentions training and serving but doesn't discuss feature engineering, model selection rationale, or online/offline evaluation.
- **6-7 (Practitioner):** Discusses specific feature types, model architectures with rationale, training/serving split, and at least one evaluation approach. Shows awareness of ML-specific challenges (data drift, cold start, training-serving skew).
- **8-9 (Expert):** Connects ML choices to business metrics. Discusses feature stores, experiment frameworks, model monitoring, and iteration cycles. Can articulate why one model type fits this problem better than alternatives with specific reasoning.

### 5. Communication Quality
Would an interviewer enjoy listening to this? Could they follow along?

**Score anchors:**
- **2-3 (Hard to follow):** Excessive filler words (um, uh, like). Long pauses. Contradicts self without correction. Interviewer would be lost.
- **4-5 (Passable):** Gets the point across but with significant filler, repetition, or tangents. Ideas are there but buried in verbal noise. Frequent self-corrections without signposting.
- **6-7 (Clear):** Mostly fluent with occasional filler. Key points land clearly. Uses transitions ("so for storage...", "moving to the serving layer..."). Self-corrects cleanly when needed.
- **8-9 (Polished):** Confident delivery. Minimal filler. Concise — doesn't over-explain simple points. Adjusts pace for complex vs simple topics. Sounds like they've explained this system before.

## Grading Rules

1. **CITE EVIDENCE.** For every dimension score, quote 1-2 specific phrases from the transcript that justify the score. Format: `"quote from transcript" — this shows [strength/weakness]`
2. **DIFFERENTIATE SCORES.** If all dimensions score within 1 point of each other, re-evaluate — it's extremely unlikely that a candidate is equally strong/weak across all dimensions.
3. **SCOPE TO THE QUESTION.** Only evaluate what the question asked. If the question is about data modeling, do NOT penalize for not covering A/B testing or real-time inference.
4. **DURATION MATTERS.** A 2-minute answer to a 5-minute question should be penalized under Structure (didn't cover enough ground). A 10-minute answer to a 3-minute question should be penalized under Communication (couldn't be concise).
5. **ORAL-SPECIFIC.** This is a spoken response, not written. Expect some natural filler — penalize patterns, not individual "um"s. Value confident delivery and clear signposting.
