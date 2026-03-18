# Resume Defense Questions

30 questions covering every major resume claim. Answer out loud, then check answers.md.

---

## A. Recommendation and Retrieval (Q1-8)

1. Walk me through the end-to-end architecture of your intent-based recommendation system at Walmart.

2. Why did you use LLM-generated semantic queries plus a two-tower retrieval system instead of a more standard collaborative-filtering or co-purchase approach?

3. How were the training examples constructed for the retrieval model?

4. What negative sampling strategy did you use, and why?

5. How did you evaluate the quality of the generated semantic queries?

6. What were the biggest failure modes in multilingual markets?

7. If relevance improved by 46%, what exactly was the metric and what were the caveats behind that number?

8. How would you redesign the system if latency or inference cost became the main bottleneck?

## B. LLM Evaluation and RL (Q9-16)

9. Explain exactly what you mean by "RL training loops using LLM-as-judge."

10. What was the state, action, reward, and policy in your practical setup?

11. Was this true RLHF, RLAIF, reranking optimization, or iterative supervised improvement with an evaluator in the loop?

12. Why was Llama 70B a good choice as judge, and what were its limitations?

13. How did you validate that the judge aligned with human preferences rather than amplifying its own bias?

14. What failure modes arise when optimizing too hard against a learned judge?

15. How would you detect reward hacking or overfitting to the evaluator?

16. If Amazon pushed on whether this was "real RL," how would you answer clearly and defensibly?

## C. Safety, Monitoring, and Compliance (Q17-22)

17. Describe the content safety architecture you built for sensitive product categories.

18. What features or models were used for filtering and sentiment analysis?

19. How did you define drift in the generative AI pipeline?

20. What was monitored online versus offline?

21. How did locale-specific compliance requirements change the system across Canada and Mexico?

22. What would trigger rollback of a generative feature in production?

## D. Ranking and Search (Q23-27)

23. Why did cross-encoders improve NDCG relative to the previous stack?

24. What are the retrieval-versus-ranking tradeoffs between two-tower models and cross-encoders?

25. How did you manage the latency and serving cost of cross-encoders?

26. What was the experimentation methodology behind the GMV lift claims?

27. How do you connect offline metrics like NDCG to online business outcomes?

## E. Infrastructure and Prior Experience (Q28-30)

28. Explain the FAISS-based evaluation framework and where the 10x speedup came from.

29. What parts of the Airflow and streaming setup were most critical to model freshness?

30. From your genomics and computer vision work, what scientific instincts carry over into production ML?
