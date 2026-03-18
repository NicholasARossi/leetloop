# Science Breadth Questions

20 questions covering graduate-level ML fundamentals. Answer out loud, then check answers.md. These go beyond textbook definitions — demonstrate that you understand the method, when to use it, when it fails, and tradeoffs with alternatives.

---

## A. Supervised Learning Foundations (Q1-3)

1. Compare logistic regression, gradient boosted trees, and neural networks for a practical ranking or classification problem. When would you choose each, and what are the failure modes?

2. Explain the bias-variance tradeoff. How does it manifest differently in linear models, tree ensembles, and deep networks? How do L1, L2, and early stopping each address it?

3. Walk through how gradient boosted trees work. Why do they dominate tabular ML benchmarks, and where do they fall short compared to neural approaches?

## B. Clustering and Dimensionality Reduction (Q4-6)

4. Explain k-means from first principles. When does it fail, and what alternatives would you choose?

5. What is the difference between PCA and autoencoders as dimensionality reduction tools? When would you prefer one over the other?

6. Compare hierarchical clustering and Gaussian mixture models to k-means. What assumptions does each make, and when does each outperform the others?

## C. Embeddings and Representation Learning (Q7-9)

7. What makes a good embedding space for retrieval? How would you evaluate whether an embedding model has learned useful representations?

8. Explain metric learning and contrastive loss. What is the role of negative sampling, and how does the choice of negatives affect what the model learns?

9. How do CNNs, RNNs, and Transformers differ as feature extractors? Why have Transformers displaced the other two in most NLP tasks, and where do CNNs or RNNs still have advantages?

## D. Learning-to-Rank and Recommender Systems (Q10-12)

10. Explain the pointwise, pairwise, and listwise approaches to learning-to-rank. What are the tradeoffs, and which would you choose for a search ranking system?

11. What is the exploration-exploitation tradeoff, and where does it show up in recommendation or search systems?

12. Compare content-based filtering, collaborative filtering, and hybrid approaches for recommendation. What cold-start problems does each face, and how would you address them?

## E. Calibration, Uncertainty, and Thresholding (Q13-14)

13. What is calibration, why does it matter, and how would you measure it?

14. How do you choose an operating threshold for a binary classifier in production? What changes when the cost of false positives and false negatives are asymmetric?

## F. Experimental Design and Causal Reasoning (Q15-17)

15. How would you design an experiment to decide whether an LLM-generated query system is genuinely better than a simpler retrieval heuristic?

16. Why can offline ranking gains fail to translate into online gains? Give concrete examples.

17. What is counterfactual reasoning, and why is it important for evaluating recommendation and search systems? How does it relate to position bias?

## G. Evaluation Metrics (Q18-19)

18. Compare precision, recall, ROC-AUC, PR-AUC, NDCG, MAP, and MRR. When is each appropriate, and when can each be misleading?

19. You have a model with high ROC-AUC but poor real-world performance. Diagnose what might be going wrong and how you would fix it.

## H. Data Quality and Robustness (Q20)

20. How would you detect and mitigate data leakage in a recommendation or search pipeline? What about distribution shift, concept drift, and class imbalance — how do these interact in production systems?
