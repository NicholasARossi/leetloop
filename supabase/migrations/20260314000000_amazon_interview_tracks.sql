-- Amazon Resume Defense Track
INSERT INTO system_design_tracks (name, description, track_type, topics, total_topics, rubric)
VALUES (
  'Amazon Resume Defense',
  'Deep-dive interview prep covering every major resume claim — intent-based recommendation, LLM-as-judge RL, content safety, transformer ranking, and ML infrastructure',
  'mle',
  '[
    {"name": "Intent-Based Recommendation & Two-Tower Retrieval", "order": 1, "difficulty": "hard", "example_systems": ["Walmart semantic query generation", "Two-tower retrieval architecture", "Multilingual product recommendation"]},
    {"name": "LLM-as-Judge & Reinforcement Learning", "order": 2, "difficulty": "hard", "example_systems": ["Llama 70B evaluator", "Generative query optimization", "RLAIF training loops"]},
    {"name": "Content Safety & Production Monitoring", "order": 3, "difficulty": "hard", "example_systems": ["Sensitive category filtering", "Drift detection pipelines", "Multilingual compliance monitoring"]},
    {"name": "Transformer Search Ranking & Cross-Encoders", "order": 4, "difficulty": "hard", "example_systems": ["Cross-encoder reranking", "NDCG optimization", "GMV-driven A/B experiments"]},
    {"name": "ML Infrastructure & FAISS Evaluation", "order": 5, "difficulty": "medium", "example_systems": ["FAISS evaluation framework", "Airflow orchestration", "Streaming model freshness"]},
    {"name": "Relevance Filtering for Embedding-Based Retrieval (CIKM)", "order": 6, "difficulty": "hard", "example_systems": ["Embedding relevance thresholding", "Precision-recall tradeoffs at retrieval", "CIKM publication methodology"]},
    {"name": "From Genomics to Production ML", "order": 7, "difficulty": "medium", "example_systems": ["Synthego computer vision", "Genomics data pipelines", "Scientific method in industry ML"]},
    {"name": "Failure Stories & Course Corrections", "order": 8, "difficulty": "hard", "example_systems": ["Production rollback decisions", "Negative experimental results", "Leadership principle alignment"]}
  ]'::JSONB,
  8,
  '{"depth": 4, "tradeoffs": 4, "clarity": 2, "scalability": 1}'::JSONB
)
ON CONFLICT (name) DO UPDATE SET
  description = EXCLUDED.description,
  topics = EXCLUDED.topics,
  total_topics = EXCLUDED.total_topics,
  rubric = EXCLUDED.rubric;

-- Amazon Science Breadth Track
INSERT INTO system_design_tracks (name, description, track_type, topics, total_topics, rubric)
VALUES (
  'Amazon Science Breadth',
  'Core ML methods and scientific reasoning at graduate-course depth — from linear models through experiment design and data quality',
  'mle',
  '[
    {"name": "Linear Models & Regularization", "order": 1, "difficulty": "medium", "example_systems": ["Logistic regression for CTR", "L1/L2 regularization tradeoffs", "Bias-variance decomposition"]},
    {"name": "Trees & Ensemble Methods", "order": 2, "difficulty": "medium", "example_systems": ["Random forests", "Gradient boosted trees (XGBoost/LightGBM)", "Feature importance and splitting criteria"]},
    {"name": "Clustering & Dimensionality Reduction", "order": 3, "difficulty": "medium", "example_systems": ["K-means from first principles", "PCA vs autoencoders", "Gaussian mixture models"]},
    {"name": "Embeddings & Representation Learning", "order": 4, "difficulty": "hard", "example_systems": ["Word2Vec and contextual embeddings", "Contrastive and metric learning", "Transfer learning strategies"]},
    {"name": "Deep Learning Architectures", "order": 5, "difficulty": "hard", "example_systems": ["CNNs for vision", "RNNs and attention mechanisms", "Transformer architecture and scaling"]},
    {"name": "Learning to Rank & Recommender Systems", "order": 6, "difficulty": "hard", "example_systems": ["Pointwise, pairwise, listwise ranking", "Collaborative filtering", "Matrix factorization and hybrid methods"]},
    {"name": "Calibration, Uncertainty & Thresholding", "order": 7, "difficulty": "medium", "example_systems": ["Platt scaling and isotonic regression", "Confidence intervals for predictions", "Operating point selection"]},
    {"name": "Experimental Design & A/B Testing", "order": 8, "difficulty": "hard", "example_systems": ["Sample size and power analysis", "Counterfactual reasoning and causal pitfalls", "Online vs offline evaluation gaps"]},
    {"name": "Evaluation Metrics Deep Dive", "order": 9, "difficulty": "medium", "example_systems": ["Precision/Recall/F1 tradeoffs", "ROC-AUC vs PR-AUC", "NDCG, MAP, and MRR for ranking"]},
    {"name": "Data Quality: Shift, Leakage & Imbalance", "order": 10, "difficulty": "hard", "example_systems": ["Distribution shift detection", "Data leakage in ML pipelines", "Class imbalance strategies"]}
  ]'::JSONB,
  10,
  '{"depth": 4, "clarity": 4, "tradeoffs": 2, "scalability": 1}'::JSONB
)
ON CONFLICT (name) DO UPDATE SET
  description = EXCLUDED.description,
  topics = EXCLUDED.topics,
  total_topics = EXCLUDED.total_topics,
  rubric = EXCLUDED.rubric;
