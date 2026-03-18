# Science Breadth Answers

Full answers for all 20 questions. Each answer targets graduate-course depth with practical examples from search, ranking, and recommendation.

---

## A. Supervised Learning Foundations

### 1. Compare logistic regression, gradient boosted trees, and neural networks for a practical ranking or classification problem. When would you choose each, and what are the failure modes?

The choice depends on data volume, feature engineering maturity, interpretability needs, and latency constraints.

**Logistic regression** is a linear model that learns weights w such that P(y=1|x) = sigmoid(w^T x). It is fast to train, fully interpretable, and extremely stable. I would choose it as a first baseline for any classification or ranking task, and it remains a strong production choice when features are well-engineered. At Walmart, the early search ranking stack used logistic regression over hand-crafted features, and it was surprisingly competitive because the features encoded deep domain knowledge. The failure mode is that it cannot capture feature interactions unless you engineer them explicitly — it will underfit on problems where nonlinear decision boundaries matter.

**Gradient boosted trees** (XGBoost, LightGBM) learn an additive ensemble of shallow trees, where each tree corrects the residual errors of the ensemble so far. They handle heterogeneous features, missing values, and nonlinear interactions naturally. They dominate tabular benchmarks and most Kaggle competitions. I would choose them when you have structured/tabular data with moderate to large volume. The failure mode is that they struggle with high-cardinality categorical features that need representation learning (like raw text or user IDs), they do not generalize to unseen feature distributions as gracefully as neural methods, and they are harder to serve at low latency when the ensemble is large.

**Neural networks** shine when the input is raw (text, images, sequences) and you want the model to learn its own representations. For ranking, BERT-based cross-encoders jointly attend to query and document, which is why our cross-encoder ranker at Walmart improved NDCG by +0.192 over the previous system — it could capture fine-grained semantic interactions that no feature-engineered model could. The failure modes are data hunger, training instability, hyperparameter sensitivity, and serving cost. A cross-encoder that processes (query, document) pairs is orders of magnitude more expensive at inference than a logistic regression over precomputed features.

**In practice**, you often stack them: neural embeddings as features into gradient boosted trees, or a two-stage pipeline where a cheap model retrieves candidates and an expensive model reranks.

### 2. Explain the bias-variance tradeoff. How does it manifest differently in linear models, tree ensembles, and deep networks? How do L1, L2, and early stopping each address it?

The bias-variance decomposition says that for any model, the expected prediction error on new data decomposes as: Error = Bias^2 + Variance + Irreducible Noise. Bias is the error from wrong assumptions (underfitting). Variance is the error from sensitivity to training data fluctuations (overfitting). You cannot reduce both simultaneously without more data or better inductive bias.

**Linear models** have high bias and low variance. A logistic regression will never fit a circular decision boundary no matter how much data you give it. But its predictions are stable across different training samples. The lever is feature engineering — adding polynomial or interaction features reduces bias at the cost of increased variance.

**Tree ensembles** manage the tradeoff explicitly. A single deep decision tree has low bias but high variance (it memorizes training data). Random forests reduce variance by averaging many high-variance trees trained on bootstrap samples with random feature subsets. Gradient boosting reduces bias iteratively — each new tree targets the residual error — and controls variance through learning rate, tree depth, and number of rounds.

**Deep networks** are interesting because modern overparameterized networks challenge the classical tradeoff. They can have billions of parameters, perfectly fit training data (low bias), and yet still generalize well — the so-called double descent phenomenon. The implicit regularization of SGD, architecture choices, and data augmentation all contribute. But in small-data regimes, deep networks exhibit classical overfitting.

**L2 regularization** (ridge) adds lambda * ||w||^2 to the loss, shrinking all weights toward zero. This reduces variance by discouraging large weights but adds bias. **L1 regularization** (lasso) adds lambda * ||w||_1, which drives some weights exactly to zero, performing feature selection. It is useful when you believe the true model is sparse. **Early stopping** monitors validation loss and halts training before the model overfits the training set. It is equivalent to a form of L2 regularization for many models — the earlier you stop, the closer your weights stay to their initialization. In my experience, early stopping is the most practical regularizer for deep networks because it requires no additional hyperparameter tuning of the regularization strength itself, just a validation set.

### 3. Walk through how gradient boosted trees work. Why do they dominate tabular ML benchmarks, and where do they fall short compared to neural approaches?

Gradient boosting builds an ensemble of weak learners (typically shallow decision trees) sequentially. The key idea is functional gradient descent: at each step t, the algorithm fits a new tree h_t to the negative gradient of the loss with respect to the current ensemble's predictions. For squared error loss, this negative gradient is simply the residual. For log loss, it is the difference between observed labels and predicted probabilities. The final prediction is F(x) = sum of eta * h_t(x), where eta is the learning rate.

The algorithm works as follows: (1) Initialize with a constant prediction (e.g., log-odds of the base rate). (2) Compute pseudo-residuals: the negative gradient of the loss evaluated at the current predictions. (3) Fit a shallow tree to these pseudo-residuals. (4) Update the ensemble by adding the new tree scaled by the learning rate. (5) Repeat for T rounds.

**Why they dominate tabular data:** Trees naturally handle mixed feature types (numeric, categorical, ordinal) without preprocessing. They capture nonlinear interactions and are invariant to monotone feature transformations. The sequential boosting procedure is a powerful bias-reduction mechanism. Implementations like XGBoost and LightGBM add histogram binning, leaf-wise growth, and GPU acceleration that make them extremely fast. They also handle missing values natively. On benchmarks like the UCI datasets, OpenML-CC18, or Kaggle tabular competitions, GBTs consistently outperform or match neural methods.

**Where they fall short:** GBTs cannot learn representations from raw inputs. If you feed them raw pixel values, they will not discover convolutional features. If you feed them raw text tokens, they will not learn contextual embeddings. They also extrapolate poorly — tree predictions are bounded by the range of training labels, so they fail on distribution shift where the target value moves outside the training range. They are not naturally differentiable, which means you cannot easily integrate them into end-to-end pipelines with embedding models. Finally, for very large-scale problems (billions of examples), distributed tree training is less mature than distributed SGD for neural networks, though frameworks like LightGBM handle this reasonably well now.

In my work, I have seen the strongest results from hybrid approaches: use neural models to generate embeddings, then feed those embeddings as features into GBTs alongside tabular features. This gets the representation learning power of neural nets with the robust tabular modeling of trees.

## B. Clustering and Dimensionality Reduction

### 4. Explain k-means from first principles. When does it fail, and what alternatives would you choose?

K-means partitions N data points into K clusters by iteratively minimizing the within-cluster sum of squared distances to cluster centroids. The algorithm alternates two steps: (1) **Assignment**: assign each point to the nearest centroid. (2) **Update**: recompute each centroid as the mean of its assigned points. This is coordinate descent on the objective J = sum over all points of ||x_i - mu_{c(i)}||^2. Each step monotonically decreases J, and since J is bounded below by zero, the algorithm converges. However, it converges to a local minimum, not necessarily the global one.

**Key assumptions:** K-means assumes clusters are convex, roughly spherical, and roughly equal in size. It uses Euclidean distance, which implicitly assumes isotropic variance within each cluster. You must specify K in advance.

**When it fails:** (1) Non-spherical clusters — if the true clusters are elongated, crescent-shaped, or have complex geometry, k-means will split them incorrectly. (2) Clusters of very different sizes or densities — k-means tends to split large clusters and merge small ones. (3) High-dimensional data — Euclidean distance becomes less meaningful in high dimensions (the curse of dimensionality), and all points become approximately equidistant. (4) Sensitivity to initialization — poor initial centroids can lead to bad local minima. K-means++ initialization addresses this by spreading initial centroids apart. (5) Outliers pull centroids toward themselves.

**Alternatives:** For non-spherical clusters, **DBSCAN** discovers clusters of arbitrary shape based on density, and it does not require specifying K. For overlapping or soft clusters, **Gaussian Mixture Models** (GMMs) with EM provide probabilistic cluster assignments. For hierarchical structure, **agglomerative clustering** builds a dendrogram that lets you choose K after the fact. For high-dimensional data, you might reduce dimensions first (PCA, UMAP) and then cluster, or use spectral clustering which operates on a similarity graph. In embedding spaces for retrieval, I have used k-means to partition the index for approximate nearest neighbor search (IVF in FAISS), where the spherical assumption is reasonable because the embeddings are typically L2-normalized.

### 5. What is the difference between PCA and autoencoders as dimensionality reduction tools? When would you prefer one over the other?

**PCA** finds the linear subspace that captures maximum variance. Mechanically, you compute the covariance matrix of the data, then take its top-k eigenvectors (or equivalently, the top-k left singular vectors from SVD). The projection z = W^T x minimizes reconstruction error ||x - WW^T x||^2 subject to W being orthonormal. PCA is optimal among all linear dimensionality reduction methods for preserving variance.

**Autoencoders** learn an encoder f and decoder g such that x is approximately equal to g(f(x)). When both f and g are linear with no activation functions, and the bottleneck dimension is k, the autoencoder recovers exactly the PCA subspace (up to rotation). The interesting case is when f and g are nonlinear neural networks — then the autoencoder can capture nonlinear manifold structure that PCA completely misses.

**When to prefer PCA:** When the data lives near a linear subspace, when you need interpretability (principal components have clear mathematical meaning), when computation must be fast and deterministic, when you have limited data (PCA has no hyperparameters beyond k and cannot overfit to noise in the same way), or when you need a quick preprocessing step before another model. PCA is also the right tool for whitening or decorrelating features.

**When to prefer autoencoders:** When the data has nonlinear structure (images, text, molecular structures), when you have enough data to train a neural network reliably, when you want to learn a representation for downstream tasks (the bottleneck layer becomes a feature vector), or when you want to generate new data (variational autoencoders). In my work on molecular biology at Synthego, we used autoencoders to learn compressed representations of high-dimensional genomic assay data where the underlying manifold was clearly nonlinear.

**Key tradeoff:** PCA gives you a unique, closed-form, globally optimal solution. Autoencoders give you more expressive power but introduce training instability, hyperparameter sensitivity, and non-uniqueness. For exploratory analysis or quick baselines, PCA first. For representation learning at scale, autoencoders (or their modern successors like contrastive learning methods that do not require reconstruction at all).

### 6. Compare hierarchical clustering and Gaussian mixture models to k-means. What assumptions does each make, and when does each outperform the others?

**Hierarchical agglomerative clustering** builds clusters bottom-up: start with each point as its own cluster, then iteratively merge the two closest clusters. The definition of "closest" is the linkage criterion — single linkage (minimum distance between any two points), complete linkage (maximum distance), average linkage, or Ward's method (minimizes increase in total within-cluster variance). The result is a dendrogram that shows the full merge history, and you can cut it at any level to get K clusters.

Assumptions: Hierarchical clustering makes no parametric assumptions about cluster shape. Single linkage can discover arbitrarily shaped clusters (it is closely related to minimum spanning trees). Ward's linkage tends to find compact, spherical clusters similar to k-means.

Advantages over k-means: You do not need to specify K in advance — the dendrogram gives you a visual tool to choose K. Different linkage criteria handle different cluster geometries. Disadvantages: O(N^2) memory and O(N^3) time in the naive case (or O(N^2 log N) with efficient data structures), which makes it impractical for large datasets. It is also a greedy algorithm — once a merge is made, it cannot be undone.

**Gaussian Mixture Models** assume the data is generated from a mixture of K multivariate Gaussians: p(x) = sum of pi_k * N(x; mu_k, Sigma_k). The EM algorithm alternates between computing soft assignment probabilities (E-step) and updating the parameters (M-step). Each data point belongs to every cluster with some probability, rather than being hard-assigned.

Assumptions: The data-generating process is actually a mixture of Gaussians. This is a strong parametric assumption. If clusters are not ellipsoidal, GMMs will need many components to approximate the true shape, which introduces model selection problems.

Advantages over k-means: Soft assignments are more informative — you get calibrated uncertainty about cluster membership. GMMs can model clusters of different shapes (elongated, tilted) through the covariance matrices. K-means is actually a special case of GMMs where all covariances are spherical and equal, and you take the hard assignment limit. Disadvantages: More parameters to estimate (especially full covariance matrices), so they need more data. EM can converge to bad local optima. Singularity issues when a component collapses onto a single point.

**When each wins:** K-means for large-scale, roughly spherical clusters where speed matters. Hierarchical clustering for small to medium datasets where you want to explore cluster structure at multiple granularities. GMMs when you need soft assignments, when clusters have different shapes or orientations, or when you want a generative model of the data.

## C. Embeddings and Representation Learning

### 7. What makes a good embedding space for retrieval? How would you evaluate whether an embedding model has learned useful representations?

A good embedding space for retrieval has several properties. First, **semantic similarity should correspond to geometric proximity** — items that are relevant to the same query should be close together, and irrelevant items should be far apart. Second, the space should be **well-utilized** — embeddings should not collapse into a low-dimensional submanifold or cluster into a few tight groups with dead space between them. Third, it should **generalize** — unseen queries and items should land in meaningful regions rather than falling into uncharted territory.

In our two-tower retrieval system at Walmart, the query encoder and item encoder map into a shared 128-dimensional space where dot product (or cosine similarity after L2 normalization) serves as the relevance score. The key architectural choice is that query and item are encoded independently, which enables precomputing item embeddings and serving retrieval with approximate nearest neighbor search (FAISS). This is the fundamental tradeoff versus cross-encoders: independent encoding loses the ability to attend between query and item tokens, but gains the ability to serve at millisecond latency over millions of items.

**Evaluating embedding quality:** I look at multiple levels. (1) **Intrinsic metrics on a held-out retrieval set:** Recall@K, MRR, and NDCG. If the correct item is not in the top-K retrieved candidates, no downstream reranker can fix it. (2) **Alignment and uniformity** (Wang & Isola, 2020): alignment measures how close positive pairs are; uniformity measures how spread out the overall distribution is on the unit hypersphere. Good embeddings have high alignment and high uniformity. (3) **Nearest neighbor inspection:** manually examine nearest neighbors for a sample of queries. Are the retrievals semantically coherent? Do failure cases cluster around specific query types? (4) **Downstream task performance:** ultimately, the embedding is only as good as the end-to-end system. If embedding quality improves but ranking or business metrics do not, the bottleneck is elsewhere. (5) **Embedding drift over time:** in production, I monitor the distribution of cosine similarities between queries and their top retrievals. A shift in this distribution can indicate that query patterns are changing or the embedding is going stale.

### 8. Explain metric learning and contrastive loss. What is the role of negative sampling, and how does the choice of negatives affect what the model learns?

Metric learning trains a model to map inputs into an embedding space where a distance metric (Euclidean, cosine) reflects semantic similarity. Instead of predicting a class label, the model learns a function f such that d(f(x_i), f(x_j)) is small when x_i and x_j are similar and large when they are dissimilar.

**Contrastive loss** (and its variants) is the standard training objective. The original contrastive loss operates on pairs: L = y * d^2 + (1-y) * max(0, margin - d)^2, where y=1 for positive pairs and y=0 for negative pairs. **Triplet loss** operates on (anchor, positive, negative) triples: L = max(0, d(a,p) - d(a,n) + margin). **InfoNCE** (used in SimCLR, CLIP, and most modern two-tower models) treats the problem as softmax classification: given a positive pair (q, d+) and a set of negatives {d-_1, ..., d-_K}, the loss is -log(exp(sim(q,d+)/tau) / sum of exp(sim(q,d_j)/tau)). This is what we used in our two-tower retrieval model.

**Negative sampling is critical** because it defines the decision boundary the model learns. **Random negatives** (uniformly sampled from the corpus) teach the model coarse-grained discrimination — "this shoe is not a laptop." This is easy and the model converges quickly, but it does not learn fine-grained distinctions. **Hard negatives** (items that are similar but not relevant, like a different size of the same shoe, or a product from a competing brand) force the model to learn subtle distinctions. They are harder to train on (risk of collapse if negatives are too hard too early) but produce much more discriminative embeddings. **In-batch negatives** (treat other examples in the mini-batch as negatives) are computationally efficient and provide a diverse set, but their difficulty depends on batch composition.

In practice, I have found that a curriculum works best: start with random negatives to learn the coarse structure of the space, then progressively introduce harder negatives as training stabilizes. At Walmart, our negative sampling strategy for the retrieval model mixed in-batch negatives with mined hard negatives from the previous iteration's top-K retrievals. The hard negatives were essential — without them, the model learned to separate obviously different categories but could not distinguish between subtly different products within the same category, which is exactly what matters for search relevance.

### 9. How do CNNs, RNNs, and Transformers differ as feature extractors? Why have Transformers displaced the other two in most NLP tasks, and where do CNNs or RNNs still have advantages?

**CNNs** apply learnable filters (convolutions) across local windows of the input, with weight sharing across positions. They build up hierarchical features: early layers detect edges or n-grams, deeper layers detect compositions. The inductive bias is locality — nearby elements interact strongly, and the receptive field grows with depth. For text, 1D convolutions over token sequences capture local phrase patterns. For images, 2D convolutions capture spatial patterns.

**RNNs** (including LSTMs and GRUs) process sequences step-by-step, maintaining a hidden state that is updated at each position: h_t = f(h_{t-1}, x_t). The inductive bias is sequential order — the model has an explicit notion of "before" and "after." LSTMs add gating mechanisms (forget, input, output gates) to mitigate the vanishing gradient problem and maintain long-range dependencies. But even LSTMs struggle with very long sequences because information must pass through many sequential steps, each of which can attenuate the signal.

**Transformers** use self-attention to compute interactions between all pairs of positions simultaneously: Attention(Q,K,V) = softmax(QK^T / sqrt(d_k)) V. The key insight is that every position can attend directly to every other position in a single layer, without the information needing to propagate through sequential steps. Multi-head attention allows the model to learn different interaction patterns in parallel.

**Why Transformers won NLP:** (1) Parallelism — unlike RNNs, self-attention computes all positions simultaneously, which maps efficiently to GPU architectures. This enables training on vastly more data. (2) Long-range dependencies — direct attention between any two positions, versus the sequential bottleneck of RNNs. (3) Scalability — Transformer architectures scale predictably with data and compute (scaling laws), enabling the foundation model paradigm. (4) Pre-training — the architecture is naturally suited to masked language modeling (BERT) and autoregressive generation (GPT), which transfer powerfully to downstream tasks.

**Where CNNs still win:** Image processing at the edge (CNNs are more parameter-efficient for spatial data), real-time audio/signal processing, and any setting where the locality prior is correct and you need efficiency. Vision Transformers (ViT) have caught up on images, but they need more data to match CNN performance because they lack the locality inductive bias. **Where RNNs still have advantages:** Online/streaming settings where you process one token at a time and need constant memory (Transformers need memory proportional to sequence length), and small-data sequential tasks where the sequential inductive bias helps generalize. State-space models (Mamba, S4) are emerging as a hybrid that combines the efficiency of RNNs with the parallelism of Transformers.

## D. Learning-to-Rank and Recommender Systems

### 10. Explain the pointwise, pairwise, and listwise approaches to learning-to-rank. What are the tradeoffs, and which would you choose for a search ranking system?

**Pointwise** methods treat ranking as regression or classification on individual items. Given a (query, document) pair, predict a relevance score (regression) or a relevance grade (classification). The loss function is independent per item: MSE for regression, cross-entropy for classification. Examples: linear regression, logistic regression, or a neural network predicting relevance scores. The ranking is obtained by sorting predicted scores.

Limitation: Pointwise methods ignore the relative order between documents. If two documents have true relevance 3 and 1, a model that predicts 2.9 and 2.8 has nearly zero regression loss but produces a poor ranking because the gap is compressed. The loss does not directly optimize ranking quality.

**Pairwise** methods learn to correctly order pairs of documents for the same query. Given documents d_i and d_j where d_i is more relevant, the model learns that score(d_i) > score(d_j). The canonical loss is RankNet's cross-entropy on the pairwise probability: L = -log(sigmoid(s_i - s_j)). LambdaMART extends this by weighting each pair by the change in NDCG that would result from swapping them — this makes the pairwise gradients approximate a listwise objective.

Limitation: The number of pairs grows quadratically with the number of documents per query, which is expensive. Not all pairs are equally informative — pairs of similarly relevant documents contribute noise.

**Listwise** methods directly optimize a list-level ranking metric. The cleanest approach is LambdaRank/LambdaMART, which defines gradients (lambdas) that directly optimize NDCG. Other approaches include ListNet (cross-entropy between predicted and true permutation distributions) and SoftRank (smooth approximation of ranking metrics).

**What I would choose:** For a production search ranking system, I would use a pairwise or lambda-based approach. Specifically, LambdaMART (gradient boosted trees with lambda gradients) is the workhorse of production search ranking — it directly optimizes NDCG, handles the pairwise comparisons efficiently, and works well with engineered features. When we moved to neural ranking at Walmart, we used cross-encoder BERT models trained with pairwise loss over (query, relevant doc, irrelevant doc) triples, which gave us the +0.192 NDCG improvement. The key insight is that pairwise training with NDCG-aware weighting gives you most of the benefit of listwise optimization without the computational complexity. Pointwise is fine for a quick baseline but leaves ranking quality on the table.

### 11. What is the exploration-exploitation tradeoff, and where does it show up in recommendation or search systems?

The exploration-exploitation tradeoff arises whenever a system must choose between using what it already knows to maximize immediate reward (exploitation) and trying new options to learn whether they might be even better (exploration). Pure exploitation converges to a local optimum — you keep showing the items you already know perform well, but you never discover items that might perform better. Pure exploration wastes user patience on random or uncertain items.

**Formally**, this is the multi-armed bandit problem. At each time step, you choose an arm (item to recommend), observe a reward (click, purchase), and update your beliefs. Epsilon-greedy explores with probability epsilon. UCB (Upper Confidence Bound) chooses the arm with the highest optimistic estimate: argmax(estimated_reward + c * sqrt(log(t) / n_arm)), balancing the mean reward against uncertainty. Thompson sampling draws from posterior distributions and picks the arm with the highest sampled value — it explores naturally by sampling from uncertain posteriors.

**Where it shows up in recommendation and search:**

(1) **New item cold-start.** A new product has no click data. If the system only shows well-established items (exploitation), the new item never gets impressions and never accumulates data. You need a mechanism to allocate exploration traffic to new items. At Walmart, this is a concrete problem — new products launch weekly, and without deliberate exploration they get buried.

(2) **Ranking model staleness.** If the ranking model only trains on items it has previously ranked highly, it creates a feedback loop — items that were never shown get no positive signal, so they continue to never be shown. This is the position bias problem: items shown in position 1 get more clicks regardless of relevance, which biases the training data toward already-favored items.

(3) **Query understanding evolution.** If you only serve the query interpretation that historically performed best, you miss emerging user intents. In our LLM-generated query system, we explicitly maintained diversity in the generated query set to avoid collapsing to a single interpretation.

(4) **A/B test design.** Every A/B test has an exploration cost — the control group receives a potentially worse experience. Multi-armed bandit approaches (adaptive experiments) can reduce this cost by shifting traffic toward the winning variant earlier.

The practical challenge is that in large-scale systems, pure bandit algorithms are too slow to converge (millions of items, sparse feedback). Production systems typically combine a learned ranking model (exploitation) with heuristic exploration mechanisms: randomized re-ranking within the top-K, periodic injection of under-explored items, or contextual bandits that learn an exploration policy conditioned on user and item features.

### 12. Compare content-based filtering, collaborative filtering, and hybrid approaches for recommendation. What cold-start problems does each face, and how would you address them?

**Content-based filtering** recommends items similar to what the user has liked before, based on item features (category, brand, description embeddings, visual features). For each user, you build a preference profile from their history and recommend items whose features match that profile. The model learns a mapping from item features to user preference.

Cold-start: Content-based handles new items well (as long as you have features for them) but struggles with new users who have no history. It also has a discovery problem — it only recommends items similar to what the user already consumed, creating a filter bubble. It cannot leverage the collaborative signal that "users who liked X also liked Y" when X and Y have dissimilar features.

**Collaborative filtering** recommends items based on the behavior of similar users. Matrix factorization (the canonical approach) decomposes the user-item interaction matrix R into low-rank factors: R is approximately equal to U * V^T, where U is user embeddings and V is item embeddings. The predicted rating for user u on item i is the dot product u_u^T v_i. More modern approaches use neural collaborative filtering or graph-based methods.

Cold-start: Collaborative filtering fails for both new users and new items — a new user has no row in R, and a new item has no column. You have no interaction data to learn from. It also suffers from popularity bias (popular items dominate) and sparsity (most users interact with a tiny fraction of items).

**Hybrid approaches** combine both signals. The most effective modern approach is the two-tower architecture: one tower encodes user features plus behavioral history, the other encodes item features. The model learns to predict interaction probability from the dot product of the two tower outputs. This naturally combines content features (from the item tower) with collaborative signals (from the user history fed into the user tower).

At Walmart, our intent-based recommendation system was essentially a hybrid: the LLM-generated semantic queries captured content-level understanding of what a user might want next, and the two-tower retrieval model learned from collaborative interaction patterns. For new items, the item tower can produce embeddings from content features alone. For new users, we fall back to popularity-based or contextual recommendations until enough history accumulates.

**Addressing cold-start practically:** (1) For new users — use contextual features (device, location, entry point, session behavior) to infer initial preferences. (2) For new items — use content features and transfer from similar items. (3) Explore/exploit — deliberately show new items to accumulate data (see Q11). (4) Side information — incorporate knowledge graphs, product taxonomy, or cross-domain signals.

## E. Calibration, Uncertainty, and Thresholding

### 13. What is calibration, why does it matter, and how would you measure it?

A model is calibrated if its predicted probabilities match empirical frequencies. Formally, for all p in [0,1], among all examples where the model predicts probability p, the fraction of actual positives should be p. A model that says "80% chance of click" should, across many such predictions, see clicks roughly 80% of the time.

**Why it matters:** Calibration is essential whenever you use predicted probabilities as actual probabilities rather than just as ranking scores. (1) **Bid optimization in ads:** If your click-through-rate model predicts 5% but the true rate is 2%, you will systematically overbid and lose money. (2) **Threshold-based decisions:** If you set a content safety threshold at P(unsafe) > 0.9, you need that 0.9 to actually mean 90% probability, not just "high score." (3) **Combining model scores:** When you multiply P(click) * P(purchase|click) * expected_revenue, miscalibrated individual models compound into badly wrong value estimates. (4) **Communicating uncertainty to stakeholders:** A product manager asking "how confident are we?" needs calibrated answers.

Note that calibration and discrimination are independent properties. A model can have perfect AUC (perfect ranking) but terrible calibration, or perfect calibration but random ranking (predicting the base rate for everything is perfectly calibrated but useless for ranking).

**How to measure it:** (1) **Reliability diagram (calibration curve):** Bin predictions into buckets (e.g., 0-0.1, 0.1-0.2, ...), plot the mean predicted probability versus the actual fraction of positives in each bin. Perfect calibration is the diagonal. (2) **Expected Calibration Error (ECE):** The weighted average of |predicted - actual| across bins: ECE = sum(n_b/N * |acc_b - conf_b|). Lower is better. (3) **Brier score:** Mean squared error of probability predictions: (1/N) * sum(p_i - y_i)^2. Decomposes into calibration + refinement + uncertainty. (4) **Hosmer-Lemeshow test:** Statistical test for calibration (though it has power issues with large N).

**How to fix miscalibration:** Platt scaling (fit a logistic regression on the logits using a held-out calibration set) or isotonic regression (fit a non-parametric monotone function). Temperature scaling (divide logits by a learned temperature T) is the modern standard for neural networks — it is a single-parameter adjustment that preserves ranking while fixing calibration. In my experience, most production models benefit from post-hoc calibration, especially after any threshold or score is interpreted as a probability.

### 14. How do you choose an operating threshold for a binary classifier in production? What changes when the cost of false positives and false negatives are asymmetric?

A binary classifier outputs a score, and you need to choose a threshold above which you predict positive. This threshold defines the operating point on the precision-recall (or ROC) curve, and the right choice depends entirely on the cost structure of the application.

**Symmetric costs:** If false positives and false negatives are equally costly, you might choose the threshold that maximizes the F1 score (harmonic mean of precision and recall) or accuracy. Equivalently, on the ROC curve, you might pick the point closest to (0,1) — perfect classification.

**Asymmetric costs are the norm in practice.** In content safety at Walmart, a false negative (unsafe content shown to users) could cause brand damage or regulatory issues — far more costly than a false positive (safe content incorrectly flagged for review). So we set the threshold very low, accepting low precision (many false alarms for human review) in exchange for high recall (catching nearly all unsafe content). Conversely, in a spam filter for search queries, a false positive (blocking a legitimate query) directly hurts the user experience, so you want high precision even at the cost of lower recall.

**The formal framework:** Define C_FP as the cost of a false positive and C_FN as the cost of a false negative. The optimal threshold minimizes expected cost: E[cost] = C_FP * FP_rate * P(negative) + C_FN * FN_rate * P(positive). This gives the optimal threshold where the slope of the ROC curve equals (C_FP / C_FN) * (P(negative) / P(positive)). When C_FN >> C_FP, you threshold lower (higher recall). When C_FP >> C_FN, you threshold higher (higher precision).

**Practical considerations:** (1) The cost ratio is often hard to quantify precisely — "how much is one missed unsafe product worth in brand damage?" I have found it useful to present stakeholders with the precision-recall tradeoff curve and let them choose the operating point based on concrete numbers: "at this threshold, we catch 99% of unsafe content but flag 15% of safe content for review — can the review team handle that volume?" (2) The optimal threshold can change over time as the data distribution shifts. I recommend monitoring precision and recall on a rolling basis and alerting when either degrades. (3) Use calibrated probabilities for thresholding (see Q13) — otherwise the threshold is just an arbitrary score cutoff with no probabilistic interpretation. (4) Consider multi-threshold systems: a high-confidence threshold for automated decisions and a lower threshold that routes to human review.

## F. Experimental Design and Causal Reasoning

### 15. How would you design an experiment to decide whether an LLM-generated query system is genuinely better than a simpler retrieval heuristic?

This is a question I have worked through in practice, so I will describe the actual experimental design philosophy rather than a textbook answer.

**Step 1: Define the metric hierarchy.** The primary metric should be a business outcome: revenue per session, conversion rate, or customer satisfaction (measured through surveys or return rates). Secondary metrics include ranking quality (NDCG, MRR), engagement (click-through rate), and diversity of results. Guardrail metrics protect against regressions: latency p50/p95/p99, error rate, and content safety violations. The LLM system must not only improve the primary metric but must not degrade any guardrail metric.

**Step 2: Offline evaluation first.** Before spending live traffic, evaluate on a held-out set of (query, relevant items) pairs. Compare NDCG, recall@K, and diversity metrics between the LLM-generated queries and the heuristic baseline. This gives a signal about retrieval quality but cannot tell you about user behavior.

**Step 3: Design the A/B test.** Randomize at the user level (not session level) to avoid within-user contamination. The control gets the heuristic retrieval; the treatment gets LLM-generated queries feeding into the same downstream ranking stack. This isolates the effect of query generation from other system differences. Size the test using a power analysis: given the baseline conversion rate and the minimum detectable effect (MDE) you care about, compute the required sample size. For our system at Walmart, we typically needed 2-4 weeks of traffic to detect effects of 15-20 bps in GMV.

**Step 4: Guard against pitfalls.** (1) Novelty effect — users may initially engage more with different results simply because they are different. Run the experiment long enough for the novelty to wear off (at least 2 weeks). (2) Network effects — if users share recommendations, treatment can leak into control. User-level randomization mitigates this but does not eliminate it. (3) Simpson's paradox — the effect might be positive overall but negative for specific segments (e.g., head queries vs. tail queries). Always look at heterogeneous treatment effects across key segments. (4) Multiple testing — if you look at 20 metrics, one will be significant by chance. Pre-register the primary metric and apply corrections for secondary metrics.

**Step 5: Decision framework.** The treatment wins if: primary metric improves with p < 0.05, no guardrail metric degrades beyond a predefined tolerance, and the effect holds across key segments. If the primary metric is flat but retrieval diversity improves, that might still justify deployment if you believe diversity drives long-term retention — but that is a judgment call, not a statistical one.

### 16. Why can offline ranking gains fail to translate into online gains? Give concrete examples.

This is one of the most important lessons in applied ranking work, and I have seen it happen multiple times. The core issue is that offline evaluation and online evaluation measure fundamentally different things, and many assumptions that hold offline break in the live system.

**Position bias and feedback loops.** Offline evaluation uses historical click data, but clicks are heavily influenced by position — an item shown in position 1 gets far more clicks than the same item in position 5, regardless of relevance. If your offline test set was collected under the old ranking policy, it is biased toward items the old model preferred. A new model that promotes different items will look worse on this biased test set even if it is genuinely better. This is the counterfactual evaluation problem. Solutions include inverse propensity scoring (weight each example by 1/P(shown at that position)) or using unbiased evaluation datasets where items were shown in random positions.

**Train-serve skew.** The model was trained and evaluated with features computed in a batch pipeline, but in production the features are computed by a real-time serving system. Differences in feature computation (stale features, different aggregation windows, numerical precision, missing values handled differently) can degrade the model's effective performance. I have seen cases where a model improved NDCG by 3% offline but was flat online because a critical feature was computed slightly differently in the serving path.

**User behavior adaptation.** Users adapt to the interface. If the new model surfaces different types of results, users may need time to change their browsing patterns. Short-term click metrics may drop even if long-term satisfaction improves. Conversely, novelty effects can make a worse model look better initially.

**Metric mismatch.** Offline NDCG measures relevance ranking quality, but online business metrics measure conversion and revenue. A model that ranks highly relevant but low-margin items above less relevant but high-margin items will improve NDCG but may decrease revenue. The optimization objective and the business objective are not the same thing.

**Latency effects.** A more complex model that improves quality but increases p99 latency from 200ms to 500ms may degrade the overall user experience, with the latency harm outweighing the quality gain. We saw this tension directly when introducing cross-encoders — the NDCG improvement was clear offline, but we had to carefully optimize the serving infrastructure to avoid introducing latency that would erode the online gains.

**Sample selection bias.** The offline dataset may not represent the full diversity of live traffic. Long-tail queries, seasonal patterns, and new inventory are underrepresented in historical data. A model that excels on the offline head-query distribution may fail on the live tail.

### 17. What is counterfactual reasoning, and why is it important for evaluating recommendation and search systems? How does it relate to position bias?

Counterfactual reasoning asks: "What would have happened if we had made a different decision?" In the context of recommendation and search, the central question is: "If we had shown a different set of items in a different order, what would the user have done?" This is a causal question, not a correlational one, and it is fundamentally harder to answer because we only observe what actually happened (the factual), never what would have happened under the alternative (the counterfactual).

**Why it matters for evaluation:** When you train a new ranking model and want to evaluate it offline, you have historical data collected under the old policy: (query, items shown, user interactions). You want to estimate how users would interact with the new ranking. But you cannot directly measure this — you only see interactions with items that were shown by the old model, at the positions the old model chose. Naively evaluating the new model on this data is biased because items the old model never showed have no interaction data, and items shown in top positions have inflated interaction rates.

**Position bias** is the canonical manifestation. Users are more likely to click items in higher positions regardless of relevance — this is both an attention effect (users scan top-to-bottom and may not even see lower items) and a trust effect (users assume the system ranked relevant items higher). If you train a model on raw click data, it learns to predict "will the user click given this position?" rather than "is this item relevant?" A model trained this way perpetuates the existing ranking because it has learned position effects, not relevance.

**Solutions from the counterfactual framework:** (1) **Inverse propensity scoring (IPS):** Weight each interaction by 1/P(item was shown at that position under the old policy). Items that were rarely shown get upweighted, correcting the selection bias. The propensity scores can be estimated from the logging policy. (2) **Doubly robust estimation:** Combines a direct model of outcomes with IPS to reduce variance. (3) **Interleaving experiments:** Show results from the old and new models interleaved within a single result list, which controls for position bias because both models' results appear at all positions. (4) **Unbiased learning to rank:** During training, incorporate position as a feature or use propensity-weighted losses so the model learns relevance separately from position effects. (5) **Randomized evaluation sets:** Periodically inject randomly ordered results (at a small cost to user experience) to collect unbiased relevance judgments.

In my work, we used interleaving as a quick online signal before committing to a full A/B test. It is more sensitive than A/B testing for detecting ranking quality differences because it controls for user-level and query-level variation — each user serves as their own control.

## G. Evaluation Metrics

### 18. Compare precision, recall, ROC-AUC, PR-AUC, NDCG, MAP, and MRR. When is each appropriate, and when can each be misleading?

**Precision** = TP / (TP + FP). Of the items you predicted positive, what fraction are actually positive? Use when the cost of false positives is high (e.g., content safety: if you flag something as safe, it better be safe).

**Recall** = TP / (TP + FN). Of the actual positives, what fraction did you catch? Use when the cost of false negatives is high (e.g., fraud detection: you cannot afford to miss fraudulent transactions).

Both are threshold-dependent and tell you about a single operating point.

**ROC-AUC** measures discrimination across all thresholds: the probability that a randomly chosen positive is scored higher than a randomly chosen negative. It is threshold-independent and useful for overall model comparison. **Misleading when:** Class imbalance is severe. With 99% negatives, a model can achieve 0.95 AUC by being good at ranking the abundant negatives, while being mediocre at distinguishing among the positives that actually matter. ROC-AUC is also insensitive to calibration — a model with terrible probability estimates can have perfect AUC.

**PR-AUC** (area under the precision-recall curve) is the better metric under class imbalance because it focuses on the positive class. It measures the tradeoff between precision and recall without being inflated by true negatives. I use PR-AUC whenever the positive class is rare and the application cares about finding positives (e.g., detecting unsafe content in a corpus that is 99.5% safe).

**NDCG** (Normalized Discounted Cumulative Gain) is a ranking metric that accounts for position and graded relevance. DCG = sum of (2^rel_i - 1) / log2(i+1), normalized by the ideal DCG. It rewards placing highly relevant items at the top. This was our primary offline metric for search ranking at Walmart — the +0.192 NDCG improvement from cross-encoders was measured on a curated test set with human relevance judgments. **Misleading when:** The relevance judgments are incomplete (unjudged items are treated as irrelevant, penalizing models that surface novel relevant items) or when the gain function does not match business value.

**MAP** (Mean Average Precision) averages precision at each relevant document's rank position, then averages across queries. It is equivalent to PR-AUC for ranking and assumes binary relevance. Good for information retrieval where you want high precision at all recall levels.

**MRR** (Mean Reciprocal Rank) = average of 1/rank_of_first_relevant_item across queries. It only cares about the first relevant result, making it appropriate for navigational queries where the user wants one specific item. **Misleading when:** Queries have multiple relevant items and you care about the full ranking, not just the first hit.

**My practical approach:** For binary classification, use PR-AUC and precision/recall at the operating threshold. For ranking with graded relevance, use NDCG. For retrieval (finding candidates), use recall@K. Always report multiple metrics — a single number hides important tradeoffs.

### 19. You have a model with high ROC-AUC but poor real-world performance. Diagnose what might be going wrong and how you would fix it.

This is a common and instructive failure mode. High AUC means the model discriminates well — it generally ranks positives above negatives. Poor real-world performance means that despite this, the system is not delivering value. Here are the most likely causes, roughly ordered by frequency in my experience:

**1. Class imbalance masking poor positive-class performance.** If 99% of examples are negative, the model can achieve 0.98 AUC by being excellent at ranking negatives while only mediocre at ranking among the rare positives. Switch to PR-AUC and precision/recall at your operating threshold. You will likely see that precision or recall is poor where it matters.

**2. Calibration failure.** The model ranks correctly but the predicted probabilities are wrong. If a downstream system uses these probabilities for decisions (bid optimization, expected value calculations, threshold-based routing), miscalibrated scores lead to poor decisions even with perfect ranking. Fix: apply Platt scaling or temperature scaling on a calibration set. Check with a reliability diagram.

**3. Distribution shift between evaluation and production.** The AUC was measured on a test set that does not represent current traffic. Common causes: temporal shift (test set from last month, but user behavior changed), population shift (test set overrepresents power users), or feature drift (a feature value distribution shifted in production). Fix: evaluate on recent data, monitor feature distributions, set up drift detection.

**4. Train-serve skew.** Features computed differently in batch training versus real-time serving. A feature like "user's click rate in the last 7 days" might be perfectly computed in the training pipeline but stale or differently aggregated in the serving path. Fix: compare feature value distributions between training and serving, log and audit serving-time features.

**5. Threshold selection error.** High AUC does not tell you anything about the threshold choice. If the operating threshold is poorly chosen — too aggressive (too many false positives) or too conservative (missing too many positives) — real-world performance suffers even with good discrimination. Fix: tune the threshold on a representative validation set using the actual business cost function.

**6. Metric mismatch.** AUC measures ranking quality, but the business cares about something else: revenue, user retention, latency-adjusted engagement. A model that perfectly ranks items by relevance but ignores price, availability, or user intent diversity may have high AUC and low business impact. Fix: align the evaluation metric with the business objective, or add business-relevant features and constraints.

**7. Feedback loop corruption.** If the model was trained on its own logged predictions, it may have high AUC on data it generated but poor performance on the true distribution. This is the off-policy evaluation problem. Fix: use counterfactual evaluation (IPS), or collect fresh labels on a random sample.

**Diagnostic workflow:** First, check PR-AUC and calibration. Then compare offline feature distributions to production. Then examine performance by segment (query type, user type, time). The answer is usually in the first two checks.

## H. Data Quality and Robustness

### 20. How would you detect and mitigate data leakage in a recommendation or search pipeline? What about distribution shift, concept drift, and class imbalance — how do these interact in production systems?

**Data leakage** occurs when information from the test set (or from the future) leaks into the training process, producing optimistically biased evaluation. In recommendation and search pipelines, leakage is insidious because the systems are inherently temporal and interconnected.

**Common leakage patterns I watch for:** (1) **Temporal leakage**: Training on data from after the prediction point. If you predict whether a user will click tomorrow, you cannot use features computed from tomorrow's data. Always split by time, not randomly. (2) **Target leakage**: A feature that is a proxy for the label. For example, "number of times this item was purchased" as a feature for predicting purchase — if computed on the full dataset including the test period, it directly encodes the label. (3) **Cross-contamination in pipelines**: In a multi-stage system (retrieval -> ranking -> reranking), if the retrieval model was trained on data that includes the ranking model's outputs, the evaluation of the full pipeline is biased. (4) **User-level leakage**: The same user appears in both train and test, and user-specific features leak the test labels. For recommendation, split by user or by time, not by random interaction.

**Detection:** (1) Suspiciously high offline metrics that do not replicate online. (2) Feature importance analysis — if a feature is disproportionately important and it was not expected to be, it might be leaking. (3) Ablation: remove suspect features and check if performance drops unreasonably. (4) Temporal validation: always evaluate on a strictly future holdout set and compare to random-split results. If random-split AUC is much higher than temporal-split AUC, leakage is likely.

**Distribution shift** means the data distribution at serving time differs from training time. Covariate shift: P(X) changes but P(Y|X) stays the same (e.g., query distribution shifts seasonally). Concept drift: P(Y|X) changes (e.g., what counts as "relevant" changes as the product catalog evolves). Prior probability shift: P(Y) changes (e.g., click-through rates change due to a UI redesign).

**Monitoring in production:** Track input feature distributions (KL divergence, PSI — population stability index), prediction distribution statistics (mean, variance, quantiles), and model performance on labeled samples. At Walmart, we monitored embedding similarity distributions and flagged when the mean query-document similarity in production deviated from the training distribution, which was an early indicator that the model was encountering queries it was not trained for.

**Class imbalance** interacts with both shift and leakage in dangerous ways. In a search safety classifier, unsafe content might be 0.5% of items. A model trained on this distribution learns that the prior is heavily negative. If drift causes the unsafe fraction to increase to 2%, the model's calibration degrades — it was trained to expect rarity and may under-predict the positive class. Conversely, if you oversample the minority class during training (SMOTE, upweighting), you correct the class imbalance but introduce a calibration offset that must be corrected post-hoc.

**Mitigation strategies:** (1) Retrain regularly on recent data to adapt to distribution shift. (2) Use time-aware cross-validation, never random splits. (3) For class imbalance, use focal loss, class-weighted loss, or stratified sampling during training, and always apply post-hoc calibration. (4) Deploy monitoring dashboards that track PSI on key features, prediction mean/variance drift, and performance on a labeled evaluation set that is refreshed periodically. (5) Set up automated alerts and rollback triggers when drift exceeds thresholds.
