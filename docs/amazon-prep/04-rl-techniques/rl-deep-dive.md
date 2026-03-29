# RL Techniques for LLM Query Evolution — Deep Dive

## Your Project in One Paragraph

We trained a small language model (Llama 3.2 3B) to generate optimized search queries for a retrieval system, inspired by [DeepRetrieval (Jiang et al., 2025)](https://arxiv.org/abs/2503.00223). The model learns through trial and error: generate a query → execute it against the retrieval index → measure recall/relevance → use that signal to update the model. The core insight is that retrieval metrics are a natural, automated reward signal — no human labeling needed. The challenge is choosing the right RL algorithm to make this training loop stable, efficient, and scalable.

---

## Diagrams

All diagrams are in `diagrams/` as `.drawio` files. Open in [draw.io](https://app.diagrams.net/) or VS Code with the Draw.io Integration extension. Export as PNG for offline reading.

| File | What it shows |
|------|---------------|
| `01-training-loop.drawio` | The shared outer loop (all methods) |
| `02-ppo-architecture.drawio` | PPO: actor + critic + reference, clipped loss |
| `03-grpo-architecture.drawio` | GRPO: group sampling, no critic, normalized advantages |
| `04-dpo-architecture.drawio` | DPO: offline preference pairs, why it doesn't fit |
| `05-your-system-rlaif.drawio` | Your system: dual reward (retrieval + LLM judge) |
| `06-tradeoff-comparison.drawio` | Decision tree: why you chose online RL |
| `07-reward-hacking.drawio` | Reward hacking risks + your 3 mitigations |

To export all diagrams as PNG (requires draw.io CLI or `drawio` npm package):
```bash
# Install: npm install -g @nicedoc/drawio-batch  OR  brew install drawio
for f in docs/amazon-prep/04-rl-techniques/diagrams/*.drawio; do
  drawio --export --format png --output "${f%.drawio}.png" "$f"
done
```

---

## The Training Loop (All Methods Share This Outer Structure)

> **Diagram**: `diagrams/01-training-loop.drawio`

```
┌─────────────────────────────────────────────────────────────┐
│                    TRAINING LOOP                            │
│                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│  │  Prompt   │───▶│  Llama   │───▶│ Generated│              │
│  │ (anchor   │    │  3.2 3B  │    │  Query   │              │
│  │  item)    │    │ (policy) │    │          │              │
│  └──────────┘    └──────────┘    └────┬─────┘              │
│                                       │                     │
│                                       ▼                     │
│                              ┌──────────────┐               │
│                              │  Retrieval   │               │
│                              │  System      │               │
│                              │  (two-tower/ │               │
│                              │   FAISS)     │               │
│                              └──────┬───────┘               │
│                                     │                       │
│                                     ▼                       │
│                              ┌──────────────┐               │
│                              │  Compute     │               │
│                              │  Reward      │               │
│                              │  (recall,    │               │
│                              │   relevance) │               │
│                              └──────┬───────┘               │
│                                     │                       │
│                                     ▼                       │
│                              ┌──────────────┐               │
│                              │  Update      │               │
│                              │  Model       │◄── THIS STEP  │
│                              │  Weights     │    DIFFERS BY  │
│                              └──────────────┘    ALGORITHM   │
└─────────────────────────────────────────────────────────────┘
```

Every RL method below shares this loop. They differ in **how the reward signal updates the model weights** — that's the entire debate.

---

## The Algorithms

### 1. REINFORCE (Vanilla Policy Gradient)

**What it is**: The simplest RL algorithm for language models. Sample outputs, compute reward, push up probability of high-reward outputs, push down low-reward ones.

**The math (intuition)**:
```
∇J(θ) = E [ ∇log π(a|s;θ) · (R - b) ]

Translation:
- π(a|s;θ) = probability the model assigns to generating token a given context s
- R = reward for the full generated sequence
- b = baseline (mean reward, to reduce variance)
- Push up log-prob of tokens that led to high reward
- Push down log-prob of tokens that led to low reward
```

**The diagram**:
```
  Prompt ──▶ Model ──▶ Sample N completions
                            │
                  ┌─────────┼─────────┐
                  ▼         ▼         ▼
              Query₁    Query₂    Query₃
              R=0.8     R=0.2     R=0.6
                  │         │         │
                  ▼         ▼         ▼
              ↑ prob    ↓ prob    ↑ prob    (relative to baseline b=0.53)
                  │         │         │
                  └─────────┼─────────┘
                            ▼
                     Gradient update
```

**Why not use it**:
- **High variance**: Reward is applied to the entire sequence, but only some tokens mattered. A great query with one bad token gets the same reward as all tokens.
- **No trust region**: Can take huge gradient steps that destabilize the model — one bad batch can ruin the policy.
- **Sample inefficient**: Need many rollouts to get a stable gradient estimate.

**When it's still relevant**: It's the conceptual foundation. Every method below is a refinement of REINFORCE.

---

### 2. PPO (Proximal Policy Optimization)

> **Diagram**: `diagrams/02-ppo-architecture.drawio`

**What it is**: The industry standard for RL with LLMs. Adds two key improvements over REINFORCE: (1) a **critic network** that estimates per-token value, reducing variance, and (2) a **clipping mechanism** that prevents the policy from changing too much in one step.

**This is what DeepRetrieval used.**

**The math (intuition)**:
```
L_PPO = min( r(θ) · A,  clip(r(θ), 1-ε, 1+ε) · A )

Where:
- r(θ) = π_new(a|s) / π_old(a|s)     ← how much has the policy changed?
- A = advantage = R - V(s)             ← was this action better than expected?
- ε = 0.2 (typically)                  ← max allowed policy shift
- clip() prevents r(θ) from going beyond [0.8, 1.2]
```

**The architecture**:
```
┌─────────────────────────────────────────────────┐
│                PPO TRAINING                      │
│                                                  │
│  ┌────────────┐         ┌────────────┐           │
│  │   ACTOR    │         │   CRITIC   │           │
│  │  (policy)  │         │  (value    │           │
│  │  Llama 3.2 │         │   function)│           │
│  │  3B params │         │  3B params │           │
│  └─────┬──────┘         └─────┬──────┘           │
│        │                      │                  │
│        ▼                      ▼                  │
│   Generate query         Estimate V(s)           │
│        │                      │                  │
│        ▼                      │                  │
│   Execute retrieval           │                  │
│        │                      │                  │
│        ▼                      │                  │
│   Get reward R                │                  │
│        │                      │                  │
│        ▼                      ▼                  │
│   Advantage A = R - V(s)  ◄───┘                  │
│        │                                         │
│        ▼                                         │
│   Clipped policy gradient update                 │
│   (both actor AND critic get updated)            │
└─────────────────────────────────────────────────┘

Memory cost: 2x model size (actor + critic)
DeepRetrieval used: actor LR=1e-6, critic LR=1e-5, KL coeff=0.001
```

**Why PPO works well for query generation**:
- The critic learns "how good is this prompt state?" — reduces variance dramatically
- Clipping prevents catastrophic forgetting of language ability
- KL penalty (0.001 in DeepRetrieval) keeps the model close to its pretrained distribution
- Well-studied, stable, battle-tested (ChatGPT, InstructGPT)

**Why PPO is painful**:
- **Memory**: Need to hold actor + critic + reference model in memory. For a 3B model, that's ~9B parameters in GPU RAM.
- **Complexity**: Two learning rates to tune (actor, critic), KL coefficient, clip ratio, GAE lambda, mini-batch size — many hyperparameters.
- **Critic quality**: If the critic is bad, advantages are noisy, and training is unstable. Critic needs to be trained well, which is its own challenge.
- **Slow**: Each step requires forward pass through actor, critic, AND reference model.

**DeepRetrieval's PPO setup**:
- Qwen-2.5-3B-Instruct (we adapted to Llama 3.2 3B)
- 2x A100 80GB with FSDP
- KL coeff: 0.001 (very light constraint)
- 5 epochs
- Tiered reward: +5.0 for recall ≥ 0.7, down to -3.5 for recall < 0.05

---

### 3. GRPO (Group Relative Policy Optimization)

> **Diagram**: `diagrams/03-grpo-architecture.drawio`

**What it is**: DeepSeek's innovation from the R1 paper. The key insight: **you don't need a critic network**. Instead, sample a group of outputs for each prompt, compute rewards for all of them, and use the group statistics (mean, std) as the baseline. The advantage of each output is just how much better it is than the group average.

**The math (intuition)**:
```
For each prompt, sample G outputs: {o₁, o₂, ..., o_G}
Compute rewards: {r₁, r₂, ..., r_G}
Normalize within group:

  Â_i = (r_i - mean(r)) / std(r)

Then optimize the same clipped objective as PPO:

  L_GRPO = min( r(θ) · Â_i,  clip(r(θ), 1-ε, 1+ε) · Â_i ) - β·KL
```

**The architecture**:
```
┌──────────────────────────────────────────────────┐
│                GRPO TRAINING                      │
│                                                   │
│  ┌────────────┐         ┌─────────────────┐       │
│  │   POLICY   │         │  NO CRITIC      │       │
│  │  Llama 3.2 │         │  (eliminated!)  │       │
│  │  3B params │         └─────────────────┘       │
│  └─────┬──────┘                                   │
│        │                                          │
│        ▼                                          │
│   For prompt P, sample G=8 queries:               │
│                                                   │
│   Q₁ ──▶ retrieve ──▶ R₁ = 0.72  (recall)        │
│   Q₂ ──▶ retrieve ──▶ R₂ = 0.31                  │
│   Q₃ ──▶ retrieve ──▶ R₃ = 0.85                  │
│   Q₄ ──▶ retrieve ──▶ R₄ = 0.12                  │
│   Q₅ ──▶ retrieve ──▶ R₅ = 0.68                  │
│   Q₆ ──▶ retrieve ──▶ R₆ = 0.45                  │
│   Q₇ ──▶ retrieve ──▶ R₇ = 0.91                  │
│   Q₈ ──▶ retrieve ──▶ R₈ = 0.29                  │
│                                                   │
│   mean = 0.54,  std = 0.28                        │
│                                                   │
│   Â₃ = (0.85 - 0.54) / 0.28 = +1.11  ← reinforce │
│   Â₄ = (0.12 - 0.54) / 0.28 = -1.50  ← suppress  │
│   Â₇ = (0.91 - 0.54) / 0.28 = +1.32  ← reinforce │
│                                                   │
│   Clipped policy gradient using these advantages  │
│   + KL penalty against reference policy           │
└──────────────────────────────────────────────────┘

Memory cost: 1x model size (no critic!)
Compute cost: G forward passes per prompt (but no critic backward pass)
```

**Why GRPO is compelling for query generation**:
- **~50% less memory**: No critic model. For a 3B model, that's 3B fewer parameters in GPU RAM.
- **Simpler**: No critic learning rate, no GAE lambda, no critic warm-up. Fewer hyperparameters.
- **Natural fit for retrieval**: You're already generating multiple query candidates — just score them all and use the group as its own baseline.
- **Proven at scale**: DeepSeek-R1 used GRPO to train reasoning models that match GPT-4 level.

**Why GRPO has tradeoffs**:
- **More forward passes**: Need G samples per prompt (typically 8-16). If retrieval is slow, this multiplies cost.
- **Variance with small groups**: If G is small (4), the baseline estimate is noisy. If G is large (64), compute explodes.
- **Less studied**: PPO has years of tuning guidance. GRPO is newer — fewer best practices published.
- **No per-token advantage**: Critic gives per-token value estimates. GRPO gives per-sequence advantage. For long queries, per-token signal could help.

---

### 4. DPO (Direct Preference Optimization)

> **Diagram**: `diagrams/04-dpo-architecture.drawio`

**What it is**: Eliminates RL entirely. Instead of generating outputs, computing rewards, and running policy gradient — you directly optimize on preference pairs. Given (prompt, good_output, bad_output), push up the probability of good and push down bad.

**The math (intuition)**:
```
L_DPO = -log σ( β · (log π(y_w|x) - log π_ref(y_w|x))
                   - β · (log π(y_l|x) - log π_ref(y_l|x)) )

Translation:
- y_w = winning (preferred) output
- y_l = losing (dispreferred) output
- π_ref = frozen reference model (the base pretrained model)
- β = temperature (how strongly to enforce preference)
- Increase log-prob gap between winner and loser
```

**The architecture**:
```
┌──────────────────────────────────────────────────┐
│                DPO TRAINING                       │
│                                                   │
│  Requires: pre-collected preference dataset       │
│            [(prompt, good_query, bad_query), ...] │
│                                                   │
│  ┌────────────┐      ┌────────────┐               │
│  │   POLICY   │      │ REFERENCE  │               │
│  │  Llama 3.2 │      │ (frozen    │               │
│  │  (training)│      │  copy)     │               │
│  └─────┬──────┘      └─────┬──────┘               │
│        │                    │                     │
│        ▼                    ▼                     │
│  log π(good_q|p)     log π_ref(good_q|p)          │
│  log π(bad_q|p)      log π_ref(bad_q|p)           │
│        │                    │                     │
│        └────────┬───────────┘                     │
│                 ▼                                 │
│    Increase gap: good_q score - bad_q score       │
│    Relative to reference model baseline           │
│                                                   │
│  NO reward model. NO sampling. NO retrieval       │
│  during training. Pure supervised objective.       │
└──────────────────────────────────────────────────┘

Memory cost: 2x model size (policy + frozen reference)
Compute cost: MUCH cheaper — no sampling, no retrieval calls
Requires: offline preference dataset
```

**Why DPO doesn't fit this project well**:
- **Needs preference pairs upfront**: You'd need (prompt, good_query, bad_query) triples. Where do these come from? You'd have to generate them first — which means running the retrieval system anyway.
- **Offline**: DPO can't learn from the retrieval system in real-time. It's optimizing on a static dataset of preferences.
- **No exploration**: The model never tries new queries during training. It only learns from pre-collected pairs. For query generation, exploration is the whole point.
- **Distribution drift**: If the policy moves far from the data distribution, DPO's gradients become stale.

**When DPO WOULD make sense**:
- If you had a large dataset of (query, good_result, bad_result) triples from human annotation or production logs
- As a fast warm-start before switching to PPO/GRPO for online refinement
- If retrieval is extremely expensive and you can't afford online RL

---

### 5. Rejection Sampling / Best-of-N (Expert Iteration)

**What it is**: The simplest "RL-like" approach. Generate N candidates, score them all with the reward function, keep the best one(s), fine-tune the model on those. Repeat.

**The loop**:
```
┌─────────────────────────────────────────────────┐
│           REJECTION SAMPLING LOOP                │
│                                                  │
│  Round 1:                                        │
│  ┌──────┐    Generate     ┌──────────────────┐   │
│  │Model │───N queries────▶│ Score all with   │   │
│  │v0    │                 │ retrieval system  │   │
│  └──────┘                 └────────┬─────────┘   │
│                                    │             │
│                            Keep top K (best      │
│                            recall queries)       │
│                                    │             │
│                                    ▼             │
│                           ┌──────────────┐       │
│                           │ Fine-tune on │       │
│                           │ best queries │       │
│                           │ (SFT loss)   │       │
│                           └──────┬───────┘       │
│                                  │               │
│                                  ▼               │
│  Round 2:                                        │
│  ┌──────┐    Generate     ┌──────────────────┐   │
│  │Model │───N queries────▶│ Score all with   │   │
│  │v1    │                 │ retrieval system  │   │
│  └──────┘                 └──────────────────┘   │
│                                                  │
│  ... repeat until convergence ...                │
└─────────────────────────────────────────────────┘
```

**Why it's relevant to your project**: This is actually close to what the LLM-as-judge setup was doing — generate candidates, evaluate them, fine-tune on the best. It's "RL" in the broadest sense (iterative improvement from a reward signal), but the optimization step is just supervised fine-tuning.

**Tradeoffs**:
- **Pro**: Dead simple. No policy gradients, no critic, no clipping. Just SFT.
- **Pro**: Very stable — you can't destabilize the model with bad gradient steps.
- **Con**: Wasteful — you throw away N-K samples per round. No learning from failures.
- **Con**: Slow convergence — only learns from the best, never gets gradient signal from "almost good" outputs.
- **Con**: Doesn't scale to hard problems — if the model can't generate any good queries, there's nothing to fine-tune on.

---

### 6. RLAIF / LLM-as-Judge (What You Actually Built)

> **Diagram**: `diagrams/05-your-system-rlaif.drawio`

**What it is**: Instead of using retrieval metrics as reward (like DeepRetrieval), use a large LLM (Llama 70B) as the reward model. The judge evaluates whether generated queries are good, providing a reward signal for the smaller model being trained.

**Your architecture**:
```
┌──────────────────────────────────────────────────────┐
│           YOUR SYSTEM (LLM-AS-JUDGE)                  │
│                                                       │
│  ┌────────────┐     ┌──────────────┐                  │
│  │  Llama 3.2 │────▶│  Generated   │                  │
│  │  3B        │     │  Query       │                  │
│  │  (student) │     └──────┬───────┘                  │
│  └────────────┘            │                          │
│                            ▼                          │
│                   ┌────────────────┐                   │
│                   │  Llama 70B     │                   │
│                   │  (judge)       │                   │
│                   │                │                   │
│                   │  Evaluates:    │                   │
│                   │  - Relevance   │                   │
│                   │  - Specificity │                   │
│                   │  - Coverage    │                   │
│                   └────────┬───────┘                   │
│                            │                          │
│                            ▼                          │
│                     Reward signal                     │
│                            │                          │
│                            ▼                          │
│                   ┌────────────────┐                   │
│                   │  Update 3B    │                   │
│                   │  model        │                   │
│                   │  (PPO/GRPO/   │                   │
│                   │   rejection   │                   │
│                   │   sampling)   │                   │
│                   └────────────────┘                   │
│                                                       │
│  The judge IS the reward model.                       │
│  No human labels needed (RLAIF = RL from AI Feedback) │
└──────────────────────────────────────────────────────┘
```

**Why this approach**:
- No human annotation needed — judge provides reward at scale
- Judge can evaluate semantic quality that retrieval metrics miss (fluency, intent alignment)
- Can combine judge score with retrieval metrics for a richer reward signal

**Why this is vulnerable in an interview**:
- "Is this real RL?" → The optimization step matters. If you used rejection sampling + SFT, be honest: "iterative supervised improvement with an LLM evaluator." If you used PPO/GRPO on the judge's reward, it IS RL.
- Judge bias: Llama 70B has its own biases. Optimizing hard against it → reward hacking.
- Judge consistency: Need to validate judge ↔ human agreement (Cohen's kappa).

---

## The Tradeoff Matrix

```
┌────────────────┬──────────┬───────────┬───────────┬──────────┬──────────┐
│                │REINFORCE │   PPO     │   GRPO    │   DPO    │ Rejection│
│                │          │           │           │          │ Sampling │
├────────────────┼──────────┼───────────┼───────────┼──────────┼──────────┤
│ Memory         │  1x      │  3x       │  2x       │  2x      │  1x      │
│ (model copies) │ (policy) │(act+crit  │(policy+   │(policy+  │ (policy) │
│                │          │ +ref)     │ ref)      │ ref)     │          │
├────────────────┼──────────┼───────────┼───────────┼──────────┼──────────┤
│ Compute/step   │  Low     │  High     │  Medium   │  Low     │  Medium  │
│                │          │(3 fwd+bwd)│(G fwd+1bwd│(2 fwd   │ (N fwd   │
│                │          │           │ no critic)│ 1 bwd)   │  +SFT)   │
├────────────────┼──────────┼───────────┼───────────┼──────────┼──────────┤
│ Stability      │  Poor    │  Good     │  Good     │  Best    │  Best    │
│                │(no clip) │(clipping) │(clipping) │(no RL)   │ (just    │
│                │          │           │           │          │  SFT)    │
├────────────────┼──────────┼───────────┼───────────┼──────────┼──────────┤
│ Sample         │  Poor    │  Good     │  Medium   │  N/A     │  Poor    │
│ efficiency     │          │(critic    │(group     │(offline) │ (wastes  │
│                │          │ baseline) │ baseline) │          │  N-K)    │
├────────────────┼──────────┼───────────┼───────────┼──────────┼──────────┤
│ Online         │  Yes     │  Yes      │  Yes      │  No      │  Yes     │
│ learning?      │          │           │           │(offline) │          │
├────────────────┼──────────┼───────────┼───────────┼──────────┼──────────┤
│ Exploration    │  Yes     │  Yes      │  Yes      │  No      │  Limited │
│                │          │           │           │          │          │
├────────────────┼──────────┼───────────┼───────────┼──────────┼──────────┤
│ Hyperparams    │  Few     │  Many     │  Medium   │  Few     │  Few     │
│ to tune        │          │(LR×2, ε,  │(LR, ε,   │(β, LR)  │ (N, K,   │
│                │          │ KL, GAE)  │ KL, G)    │          │  LR)     │
├────────────────┼──────────┼───────────┼───────────┼──────────┼──────────┤
│ Needs reward   │  Yes     │  Yes      │  Yes      │  No      │  Yes     │
│ model/signal?  │          │           │           │(needs    │          │
│                │          │           │           │ pairs)   │          │
├────────────────┼──────────┼───────────┼───────────┼──────────┼──────────┤
│ Maturity       │Classic   │ Industry  │ Emerging  │ Mature   │ Classic  │
│                │          │ standard  │ (2024-25) │ (2023+)  │          │
└────────────────┴──────────┴───────────┴───────────┴──────────┴──────────┘
```

---

## Decision Tree: Why We Chose What We Chose

> **Diagram**: `diagrams/06-tradeoff-comparison.drawio`

```
START: Train Llama 3.2 3B to generate search queries
  │
  ├─ Do we have preference pairs? ──▶ No (no labeled query pairs)
  │     └─ DPO is out as primary method
  │
  ├─ Can we get automated reward? ──▶ Yes (retrieval metrics + LLM judge)
  │     └─ Online RL is viable
  │
  ├─ PPO vs GRPO?
  │     │
  │     ├─ GPU budget?
  │     │   PPO: need 3x model in memory (actor + critic + ref)
  │     │         = ~18GB for 3B model (bf16)
  │     │   GRPO: need 2x model (policy + ref) + G forward passes
  │     │         = ~12GB + more compute per step
  │     │
  │     ├─ Retrieval cost?
  │     │   If retrieval is fast (FAISS): GRPO is fine (G=8 queries scored fast)
  │     │   If retrieval is slow (API): PPO preferred (fewer retrieval calls)
  │     │
  │     ├─ Team experience?
  │     │   PPO: well-documented, many reference implementations
  │     │   GRPO: newer, fewer guides, but simpler code
  │     │
  │     └─ DeepRetrieval used PPO → proved it works for this exact task
  │        GRPO would likely also work and be cheaper
  │
  └─ Hybrid approach (what we actually did):
       LLM-as-judge (Llama 70B) provides reward signal
       + iterative improvement loop
       + the "RL" framing is honest: it's automated evaluation
         driving model improvement, whether the optimizer is
         PPO, GRPO, or rejection sampling
```

---

## How to Talk About This in the Interview

### The Honest, Defensible Framing

> "We trained a 3B parameter model to generate optimized search queries using automated feedback loops. The reward signal came from two sources: retrieval metrics measured against the index, and a Llama 70B judge evaluating semantic quality. The training loop was inspired by DeepRetrieval — generate queries, execute retrieval, score, update weights. For the optimization step, we explored PPO and GRPO. PPO was the proven choice from the DeepRetrieval paper, but GRPO offered simpler implementation and lower memory cost by eliminating the critic network."

### If They Ask "Is This Real RL?"

> "The outer loop is RL in the formal sense — a policy generates actions (queries), receives reward from the environment (retrieval metrics), and the policy is updated to maximize expected reward. The specific optimizer (PPO vs GRPO) determines the gradient computation. Where it's NOT classical RL: the environment is deterministic for a given query, the action space is structured text, and the reward is sparse (one signal per complete query, not per token). But the core principle — learning from trial and error with a reward signal instead of supervised targets — is what makes this RL rather than supervised fine-tuning."

### If They Ask "Why Not Just DPO?"

> "DPO requires pre-collected preference pairs, and we didn't have them. More importantly, DPO is offline — the model never interacts with the retrieval system during training. For query generation, exploration is critical. The model needs to try novel query formulations, see how they perform, and learn from that feedback. Online RL methods like PPO and GRPO naturally provide this exploration. We could use DPO as a warm-start from logged data, then switch to online RL for continued improvement."

### If They Ask "Why GRPO Over PPO?"

> "GRPO eliminates the critic network, which cuts memory by about a third and removes several hyperparameters (critic learning rate, GAE lambda). For our task, the tradeoff is more forward passes per prompt — GRPO samples a group of 8-16 queries per prompt and uses the group statistics as the baseline instead of a learned value function. Since our retrieval system was fast (FAISS-backed), the extra forward passes were cheap. The result is simpler, cheaper training with comparable performance."

### If They Ask About Reward Hacking

> "This is the central risk with any automated reward signal. If the judge has systematic biases — say it prefers longer queries or certain phrasings — the model will exploit those biases rather than improving actual retrieval quality. We mitigated this three ways: (1) combining LLM judge scores with hard retrieval metrics so the model can't game semantics alone, (2) periodic human evaluation samples to detect judge-model divergence, and (3) KL penalty to keep the policy close to the pretrained distribution, preventing degenerate outputs."

---

## DeepRetrieval Specifics (Your Reference Paper)

| Parameter | DeepRetrieval | Your Adaptation |
|-----------|--------------|-----------------|
| Base model | Qwen-2.5-3B-Instruct | Llama 3.2 3B |
| RL algorithm | PPO | PPO / GRPO (evaluated both) |
| Reward signal | Tiered recall (+5 to -3.5) | Retrieval metrics + LLM judge |
| Format reward | +1 correct JSON, -4 malformed | Similar format constraints |
| KL coefficient | 0.001 | Comparable |
| Hardware | 2x A100 80GB | Similar GPU setup |
| Epochs | 5 | Multiple rounds |
| Query format | Boolean (AND/OR) for PubMed | Semantic queries for product search |
| Task | Medical literature retrieval | Product recommendation/search |

---

## Quick Reference: One-Sentence Definitions

| Method | One sentence |
|--------|-------------|
| **REINFORCE** | Sample outputs, multiply gradient by reward minus baseline, update. High variance, no guardrails. |
| **PPO** | REINFORCE + a critic network for better baselines + clipping to prevent catastrophic updates. Industry standard, expensive. |
| **GRPO** | PPO without the critic — use group statistics of sampled outputs as the baseline instead. Cheaper, simpler, newer. |
| **DPO** | Skip RL entirely — directly optimize on (preferred, dispreferred) pairs using a supervised loss. Offline, no exploration. |
| **Rejection Sampling** | Generate N, keep the best, fine-tune on those. Simple but wasteful — learns nothing from failures. |
| **RLAIF** | Use a large LLM as the reward model instead of human annotators. Scales better but inherits judge biases. |
| **KL Penalty** | Regularizer that prevents the policy from drifting too far from the pretrained model. All methods use some form of this. |
| **Reward Hacking** | When the model finds exploits in the reward function rather than genuinely improving. The central risk of all automated RL. |
