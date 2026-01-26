-- Seed Learning Paths: NeetCode 150 and Blind 75
-- Complete curriculum data for structured learning

-- Insert NeetCode 150
INSERT INTO learning_paths (id, name, description, total_problems, categories) VALUES (
  '11111111-1111-1111-1111-111111111150',
  'NeetCode 150',
  'Comprehensive collection of 150 LeetCode problems covering all major DSA patterns. Recommended for thorough interview preparation.',
  150,
  '[
    {
      "name": "Arrays & Hashing",
      "order": 1,
      "problems": [
        {"slug": "contains-duplicate", "title": "Contains Duplicate", "difficulty": "Easy", "order": 1},
        {"slug": "valid-anagram", "title": "Valid Anagram", "difficulty": "Easy", "order": 2},
        {"slug": "two-sum", "title": "Two Sum", "difficulty": "Easy", "order": 3},
        {"slug": "group-anagrams", "title": "Group Anagrams", "difficulty": "Medium", "order": 4},
        {"slug": "top-k-frequent-elements", "title": "Top K Frequent Elements", "difficulty": "Medium", "order": 5},
        {"slug": "encode-and-decode-strings", "title": "Encode and Decode Strings", "difficulty": "Medium", "order": 6},
        {"slug": "product-of-array-except-self", "title": "Product of Array Except Self", "difficulty": "Medium", "order": 7},
        {"slug": "valid-sudoku", "title": "Valid Sudoku", "difficulty": "Medium", "order": 8},
        {"slug": "longest-consecutive-sequence", "title": "Longest Consecutive Sequence", "difficulty": "Medium", "order": 9}
      ]
    },
    {
      "name": "Two Pointers",
      "order": 2,
      "problems": [
        {"slug": "valid-palindrome", "title": "Valid Palindrome", "difficulty": "Easy", "order": 1},
        {"slug": "two-sum-ii-input-array-is-sorted", "title": "Two Sum II", "difficulty": "Medium", "order": 2},
        {"slug": "3sum", "title": "3Sum", "difficulty": "Medium", "order": 3},
        {"slug": "container-with-most-water", "title": "Container With Most Water", "difficulty": "Medium", "order": 4},
        {"slug": "trapping-rain-water", "title": "Trapping Rain Water", "difficulty": "Hard", "order": 5}
      ]
    },
    {
      "name": "Sliding Window",
      "order": 3,
      "problems": [
        {"slug": "best-time-to-buy-and-sell-stock", "title": "Best Time to Buy and Sell Stock", "difficulty": "Easy", "order": 1},
        {"slug": "longest-substring-without-repeating-characters", "title": "Longest Substring Without Repeating Characters", "difficulty": "Medium", "order": 2},
        {"slug": "longest-repeating-character-replacement", "title": "Longest Repeating Character Replacement", "difficulty": "Medium", "order": 3},
        {"slug": "permutation-in-string", "title": "Permutation in String", "difficulty": "Medium", "order": 4},
        {"slug": "minimum-window-substring", "title": "Minimum Window Substring", "difficulty": "Hard", "order": 5},
        {"slug": "sliding-window-maximum", "title": "Sliding Window Maximum", "difficulty": "Hard", "order": 6}
      ]
    },
    {
      "name": "Stack",
      "order": 4,
      "problems": [
        {"slug": "valid-parentheses", "title": "Valid Parentheses", "difficulty": "Easy", "order": 1},
        {"slug": "min-stack", "title": "Min Stack", "difficulty": "Medium", "order": 2},
        {"slug": "evaluate-reverse-polish-notation", "title": "Evaluate Reverse Polish Notation", "difficulty": "Medium", "order": 3},
        {"slug": "generate-parentheses", "title": "Generate Parentheses", "difficulty": "Medium", "order": 4},
        {"slug": "daily-temperatures", "title": "Daily Temperatures", "difficulty": "Medium", "order": 5},
        {"slug": "car-fleet", "title": "Car Fleet", "difficulty": "Medium", "order": 6},
        {"slug": "largest-rectangle-in-histogram", "title": "Largest Rectangle in Histogram", "difficulty": "Hard", "order": 7}
      ]
    },
    {
      "name": "Binary Search",
      "order": 5,
      "problems": [
        {"slug": "binary-search", "title": "Binary Search", "difficulty": "Easy", "order": 1},
        {"slug": "search-a-2d-matrix", "title": "Search a 2D Matrix", "difficulty": "Medium", "order": 2},
        {"slug": "koko-eating-bananas", "title": "Koko Eating Bananas", "difficulty": "Medium", "order": 3},
        {"slug": "find-minimum-in-rotated-sorted-array", "title": "Find Minimum in Rotated Sorted Array", "difficulty": "Medium", "order": 4},
        {"slug": "search-in-rotated-sorted-array", "title": "Search in Rotated Sorted Array", "difficulty": "Medium", "order": 5},
        {"slug": "time-based-key-value-store", "title": "Time Based Key-Value Store", "difficulty": "Medium", "order": 6},
        {"slug": "median-of-two-sorted-arrays", "title": "Median of Two Sorted Arrays", "difficulty": "Hard", "order": 7}
      ]
    },
    {
      "name": "Linked List",
      "order": 6,
      "problems": [
        {"slug": "reverse-linked-list", "title": "Reverse Linked List", "difficulty": "Easy", "order": 1},
        {"slug": "merge-two-sorted-lists", "title": "Merge Two Sorted Lists", "difficulty": "Easy", "order": 2},
        {"slug": "reorder-list", "title": "Reorder List", "difficulty": "Medium", "order": 3},
        {"slug": "remove-nth-node-from-end-of-list", "title": "Remove Nth Node From End of List", "difficulty": "Medium", "order": 4},
        {"slug": "copy-list-with-random-pointer", "title": "Copy List with Random Pointer", "difficulty": "Medium", "order": 5},
        {"slug": "add-two-numbers", "title": "Add Two Numbers", "difficulty": "Medium", "order": 6},
        {"slug": "linked-list-cycle", "title": "Linked List Cycle", "difficulty": "Easy", "order": 7},
        {"slug": "find-the-duplicate-number", "title": "Find the Duplicate Number", "difficulty": "Medium", "order": 8},
        {"slug": "lru-cache", "title": "LRU Cache", "difficulty": "Medium", "order": 9},
        {"slug": "merge-k-sorted-lists", "title": "Merge K Sorted Lists", "difficulty": "Hard", "order": 10},
        {"slug": "reverse-nodes-in-k-group", "title": "Reverse Nodes in K-Group", "difficulty": "Hard", "order": 11}
      ]
    },
    {
      "name": "Trees",
      "order": 7,
      "problems": [
        {"slug": "invert-binary-tree", "title": "Invert Binary Tree", "difficulty": "Easy", "order": 1},
        {"slug": "maximum-depth-of-binary-tree", "title": "Maximum Depth of Binary Tree", "difficulty": "Easy", "order": 2},
        {"slug": "diameter-of-binary-tree", "title": "Diameter of Binary Tree", "difficulty": "Easy", "order": 3},
        {"slug": "balanced-binary-tree", "title": "Balanced Binary Tree", "difficulty": "Easy", "order": 4},
        {"slug": "same-tree", "title": "Same Tree", "difficulty": "Easy", "order": 5},
        {"slug": "subtree-of-another-tree", "title": "Subtree of Another Tree", "difficulty": "Easy", "order": 6},
        {"slug": "lowest-common-ancestor-of-a-binary-search-tree", "title": "Lowest Common Ancestor of a BST", "difficulty": "Medium", "order": 7},
        {"slug": "binary-tree-level-order-traversal", "title": "Binary Tree Level Order Traversal", "difficulty": "Medium", "order": 8},
        {"slug": "binary-tree-right-side-view", "title": "Binary Tree Right Side View", "difficulty": "Medium", "order": 9},
        {"slug": "count-good-nodes-in-binary-tree", "title": "Count Good Nodes in Binary Tree", "difficulty": "Medium", "order": 10},
        {"slug": "validate-binary-search-tree", "title": "Validate Binary Search Tree", "difficulty": "Medium", "order": 11},
        {"slug": "kth-smallest-element-in-a-bst", "title": "Kth Smallest Element in a BST", "difficulty": "Medium", "order": 12},
        {"slug": "construct-binary-tree-from-preorder-and-inorder-traversal", "title": "Construct Binary Tree from Preorder and Inorder", "difficulty": "Medium", "order": 13},
        {"slug": "binary-tree-maximum-path-sum", "title": "Binary Tree Maximum Path Sum", "difficulty": "Hard", "order": 14},
        {"slug": "serialize-and-deserialize-binary-tree", "title": "Serialize and Deserialize Binary Tree", "difficulty": "Hard", "order": 15}
      ]
    },
    {
      "name": "Tries",
      "order": 8,
      "problems": [
        {"slug": "implement-trie-prefix-tree", "title": "Implement Trie (Prefix Tree)", "difficulty": "Medium", "order": 1},
        {"slug": "design-add-and-search-words-data-structure", "title": "Design Add and Search Words Data Structure", "difficulty": "Medium", "order": 2},
        {"slug": "word-search-ii", "title": "Word Search II", "difficulty": "Hard", "order": 3}
      ]
    },
    {
      "name": "Heap / Priority Queue",
      "order": 9,
      "problems": [
        {"slug": "kth-largest-element-in-a-stream", "title": "Kth Largest Element in a Stream", "difficulty": "Easy", "order": 1},
        {"slug": "last-stone-weight", "title": "Last Stone Weight", "difficulty": "Easy", "order": 2},
        {"slug": "k-closest-points-to-origin", "title": "K Closest Points to Origin", "difficulty": "Medium", "order": 3},
        {"slug": "kth-largest-element-in-an-array", "title": "Kth Largest Element in an Array", "difficulty": "Medium", "order": 4},
        {"slug": "task-scheduler", "title": "Task Scheduler", "difficulty": "Medium", "order": 5},
        {"slug": "design-twitter", "title": "Design Twitter", "difficulty": "Medium", "order": 6},
        {"slug": "find-median-from-data-stream", "title": "Find Median from Data Stream", "difficulty": "Hard", "order": 7}
      ]
    },
    {
      "name": "Backtracking",
      "order": 10,
      "problems": [
        {"slug": "subsets", "title": "Subsets", "difficulty": "Medium", "order": 1},
        {"slug": "combination-sum", "title": "Combination Sum", "difficulty": "Medium", "order": 2},
        {"slug": "permutations", "title": "Permutations", "difficulty": "Medium", "order": 3},
        {"slug": "subsets-ii", "title": "Subsets II", "difficulty": "Medium", "order": 4},
        {"slug": "combination-sum-ii", "title": "Combination Sum II", "difficulty": "Medium", "order": 5},
        {"slug": "word-search", "title": "Word Search", "difficulty": "Medium", "order": 6},
        {"slug": "palindrome-partitioning", "title": "Palindrome Partitioning", "difficulty": "Medium", "order": 7},
        {"slug": "letter-combinations-of-a-phone-number", "title": "Letter Combinations of a Phone Number", "difficulty": "Medium", "order": 8},
        {"slug": "n-queens", "title": "N-Queens", "difficulty": "Hard", "order": 9}
      ]
    },
    {
      "name": "Graphs",
      "order": 11,
      "problems": [
        {"slug": "number-of-islands", "title": "Number of Islands", "difficulty": "Medium", "order": 1},
        {"slug": "max-area-of-island", "title": "Max Area of Island", "difficulty": "Medium", "order": 2},
        {"slug": "clone-graph", "title": "Clone Graph", "difficulty": "Medium", "order": 3},
        {"slug": "walls-and-gates", "title": "Walls and Gates", "difficulty": "Medium", "order": 4},
        {"slug": "rotting-oranges", "title": "Rotting Oranges", "difficulty": "Medium", "order": 5},
        {"slug": "pacific-atlantic-water-flow", "title": "Pacific Atlantic Water Flow", "difficulty": "Medium", "order": 6},
        {"slug": "surrounded-regions", "title": "Surrounded Regions", "difficulty": "Medium", "order": 7},
        {"slug": "course-schedule", "title": "Course Schedule", "difficulty": "Medium", "order": 8},
        {"slug": "course-schedule-ii", "title": "Course Schedule II", "difficulty": "Medium", "order": 9},
        {"slug": "graph-valid-tree", "title": "Graph Valid Tree", "difficulty": "Medium", "order": 10},
        {"slug": "number-of-connected-components-in-an-undirected-graph", "title": "Number of Connected Components", "difficulty": "Medium", "order": 11},
        {"slug": "redundant-connection", "title": "Redundant Connection", "difficulty": "Medium", "order": 12},
        {"slug": "word-ladder", "title": "Word Ladder", "difficulty": "Hard", "order": 13}
      ]
    },
    {
      "name": "Advanced Graphs",
      "order": 12,
      "problems": [
        {"slug": "reconstruct-itinerary", "title": "Reconstruct Itinerary", "difficulty": "Hard", "order": 1},
        {"slug": "min-cost-to-connect-all-points", "title": "Min Cost to Connect All Points", "difficulty": "Medium", "order": 2},
        {"slug": "network-delay-time", "title": "Network Delay Time", "difficulty": "Medium", "order": 3},
        {"slug": "swim-in-rising-water", "title": "Swim in Rising Water", "difficulty": "Hard", "order": 4},
        {"slug": "alien-dictionary", "title": "Alien Dictionary", "difficulty": "Hard", "order": 5},
        {"slug": "cheapest-flights-within-k-stops", "title": "Cheapest Flights Within K Stops", "difficulty": "Medium", "order": 6}
      ]
    },
    {
      "name": "1-D Dynamic Programming",
      "order": 13,
      "problems": [
        {"slug": "climbing-stairs", "title": "Climbing Stairs", "difficulty": "Easy", "order": 1},
        {"slug": "min-cost-climbing-stairs", "title": "Min Cost Climbing Stairs", "difficulty": "Easy", "order": 2},
        {"slug": "house-robber", "title": "House Robber", "difficulty": "Medium", "order": 3},
        {"slug": "house-robber-ii", "title": "House Robber II", "difficulty": "Medium", "order": 4},
        {"slug": "longest-palindromic-substring", "title": "Longest Palindromic Substring", "difficulty": "Medium", "order": 5},
        {"slug": "palindromic-substrings", "title": "Palindromic Substrings", "difficulty": "Medium", "order": 6},
        {"slug": "decode-ways", "title": "Decode Ways", "difficulty": "Medium", "order": 7},
        {"slug": "coin-change", "title": "Coin Change", "difficulty": "Medium", "order": 8},
        {"slug": "maximum-product-subarray", "title": "Maximum Product Subarray", "difficulty": "Medium", "order": 9},
        {"slug": "word-break", "title": "Word Break", "difficulty": "Medium", "order": 10},
        {"slug": "longest-increasing-subsequence", "title": "Longest Increasing Subsequence", "difficulty": "Medium", "order": 11},
        {"slug": "partition-equal-subset-sum", "title": "Partition Equal Subset Sum", "difficulty": "Medium", "order": 12}
      ]
    },
    {
      "name": "2-D Dynamic Programming",
      "order": 14,
      "problems": [
        {"slug": "unique-paths", "title": "Unique Paths", "difficulty": "Medium", "order": 1},
        {"slug": "longest-common-subsequence", "title": "Longest Common Subsequence", "difficulty": "Medium", "order": 2},
        {"slug": "best-time-to-buy-and-sell-stock-with-cooldown", "title": "Best Time to Buy and Sell Stock with Cooldown", "difficulty": "Medium", "order": 3},
        {"slug": "coin-change-ii", "title": "Coin Change II", "difficulty": "Medium", "order": 4},
        {"slug": "target-sum", "title": "Target Sum", "difficulty": "Medium", "order": 5},
        {"slug": "interleaving-string", "title": "Interleaving String", "difficulty": "Medium", "order": 6},
        {"slug": "longest-increasing-path-in-a-matrix", "title": "Longest Increasing Path in a Matrix", "difficulty": "Hard", "order": 7},
        {"slug": "distinct-subsequences", "title": "Distinct Subsequences", "difficulty": "Hard", "order": 8},
        {"slug": "edit-distance", "title": "Edit Distance", "difficulty": "Medium", "order": 9},
        {"slug": "burst-balloons", "title": "Burst Balloons", "difficulty": "Hard", "order": 10},
        {"slug": "regular-expression-matching", "title": "Regular Expression Matching", "difficulty": "Hard", "order": 11}
      ]
    },
    {
      "name": "Greedy",
      "order": 15,
      "problems": [
        {"slug": "maximum-subarray", "title": "Maximum Subarray", "difficulty": "Medium", "order": 1},
        {"slug": "jump-game", "title": "Jump Game", "difficulty": "Medium", "order": 2},
        {"slug": "jump-game-ii", "title": "Jump Game II", "difficulty": "Medium", "order": 3},
        {"slug": "gas-station", "title": "Gas Station", "difficulty": "Medium", "order": 4},
        {"slug": "hand-of-straights", "title": "Hand of Straights", "difficulty": "Medium", "order": 5},
        {"slug": "merge-triplets-to-form-target-triplet", "title": "Merge Triplets to Form Target Triplet", "difficulty": "Medium", "order": 6},
        {"slug": "partition-labels", "title": "Partition Labels", "difficulty": "Medium", "order": 7},
        {"slug": "valid-parenthesis-string", "title": "Valid Parenthesis String", "difficulty": "Medium", "order": 8}
      ]
    },
    {
      "name": "Intervals",
      "order": 16,
      "problems": [
        {"slug": "insert-interval", "title": "Insert Interval", "difficulty": "Medium", "order": 1},
        {"slug": "merge-intervals", "title": "Merge Intervals", "difficulty": "Medium", "order": 2},
        {"slug": "non-overlapping-intervals", "title": "Non-overlapping Intervals", "difficulty": "Medium", "order": 3},
        {"slug": "meeting-rooms", "title": "Meeting Rooms", "difficulty": "Easy", "order": 4},
        {"slug": "meeting-rooms-ii", "title": "Meeting Rooms II", "difficulty": "Medium", "order": 5},
        {"slug": "minimum-interval-to-include-each-query", "title": "Minimum Interval to Include Each Query", "difficulty": "Hard", "order": 6}
      ]
    },
    {
      "name": "Math & Geometry",
      "order": 17,
      "problems": [
        {"slug": "rotate-image", "title": "Rotate Image", "difficulty": "Medium", "order": 1},
        {"slug": "spiral-matrix", "title": "Spiral Matrix", "difficulty": "Medium", "order": 2},
        {"slug": "set-matrix-zeroes", "title": "Set Matrix Zeroes", "difficulty": "Medium", "order": 3},
        {"slug": "happy-number", "title": "Happy Number", "difficulty": "Easy", "order": 4},
        {"slug": "plus-one", "title": "Plus One", "difficulty": "Easy", "order": 5},
        {"slug": "powx-n", "title": "Pow(x, n)", "difficulty": "Medium", "order": 6},
        {"slug": "multiply-strings", "title": "Multiply Strings", "difficulty": "Medium", "order": 7},
        {"slug": "detect-squares", "title": "Detect Squares", "difficulty": "Medium", "order": 8}
      ]
    },
    {
      "name": "Bit Manipulation",
      "order": 18,
      "problems": [
        {"slug": "single-number", "title": "Single Number", "difficulty": "Easy", "order": 1},
        {"slug": "number-of-1-bits", "title": "Number of 1 Bits", "difficulty": "Easy", "order": 2},
        {"slug": "counting-bits", "title": "Counting Bits", "difficulty": "Easy", "order": 3},
        {"slug": "reverse-bits", "title": "Reverse Bits", "difficulty": "Easy", "order": 4},
        {"slug": "missing-number", "title": "Missing Number", "difficulty": "Easy", "order": 5},
        {"slug": "sum-of-two-integers", "title": "Sum of Two Integers", "difficulty": "Medium", "order": 6},
        {"slug": "reverse-integer", "title": "Reverse Integer", "difficulty": "Medium", "order": 7}
      ]
    }
  ]'::jsonb
) ON CONFLICT (name) DO UPDATE SET
  description = EXCLUDED.description,
  total_problems = EXCLUDED.total_problems,
  categories = EXCLUDED.categories,
  updated_at = NOW();

-- Insert Blind 75 (subset of NeetCode 150)
INSERT INTO learning_paths (id, name, description, total_problems, categories) VALUES (
  '22222222-2222-2222-2222-222222222275',
  'Blind 75',
  'The essential 75 LeetCode problems curated for FAANG interviews. A focused subset for efficient preparation.',
  75,
  '[
    {
      "name": "Arrays & Hashing",
      "order": 1,
      "problems": [
        {"slug": "two-sum", "title": "Two Sum", "difficulty": "Easy", "order": 1},
        {"slug": "contains-duplicate", "title": "Contains Duplicate", "difficulty": "Easy", "order": 2},
        {"slug": "valid-anagram", "title": "Valid Anagram", "difficulty": "Easy", "order": 3},
        {"slug": "group-anagrams", "title": "Group Anagrams", "difficulty": "Medium", "order": 4},
        {"slug": "top-k-frequent-elements", "title": "Top K Frequent Elements", "difficulty": "Medium", "order": 5},
        {"slug": "product-of-array-except-self", "title": "Product of Array Except Self", "difficulty": "Medium", "order": 6},
        {"slug": "encode-and-decode-strings", "title": "Encode and Decode Strings", "difficulty": "Medium", "order": 7},
        {"slug": "longest-consecutive-sequence", "title": "Longest Consecutive Sequence", "difficulty": "Medium", "order": 8}
      ]
    },
    {
      "name": "Two Pointers",
      "order": 2,
      "problems": [
        {"slug": "valid-palindrome", "title": "Valid Palindrome", "difficulty": "Easy", "order": 1},
        {"slug": "3sum", "title": "3Sum", "difficulty": "Medium", "order": 2},
        {"slug": "container-with-most-water", "title": "Container With Most Water", "difficulty": "Medium", "order": 3}
      ]
    },
    {
      "name": "Sliding Window",
      "order": 3,
      "problems": [
        {"slug": "best-time-to-buy-and-sell-stock", "title": "Best Time to Buy and Sell Stock", "difficulty": "Easy", "order": 1},
        {"slug": "longest-substring-without-repeating-characters", "title": "Longest Substring Without Repeating Characters", "difficulty": "Medium", "order": 2},
        {"slug": "longest-repeating-character-replacement", "title": "Longest Repeating Character Replacement", "difficulty": "Medium", "order": 3},
        {"slug": "minimum-window-substring", "title": "Minimum Window Substring", "difficulty": "Hard", "order": 4}
      ]
    },
    {
      "name": "Stack",
      "order": 4,
      "problems": [
        {"slug": "valid-parentheses", "title": "Valid Parentheses", "difficulty": "Easy", "order": 1}
      ]
    },
    {
      "name": "Binary Search",
      "order": 5,
      "problems": [
        {"slug": "find-minimum-in-rotated-sorted-array", "title": "Find Minimum in Rotated Sorted Array", "difficulty": "Medium", "order": 1},
        {"slug": "search-in-rotated-sorted-array", "title": "Search in Rotated Sorted Array", "difficulty": "Medium", "order": 2}
      ]
    },
    {
      "name": "Linked List",
      "order": 6,
      "problems": [
        {"slug": "reverse-linked-list", "title": "Reverse Linked List", "difficulty": "Easy", "order": 1},
        {"slug": "merge-two-sorted-lists", "title": "Merge Two Sorted Lists", "difficulty": "Easy", "order": 2},
        {"slug": "linked-list-cycle", "title": "Linked List Cycle", "difficulty": "Easy", "order": 3},
        {"slug": "reorder-list", "title": "Reorder List", "difficulty": "Medium", "order": 4},
        {"slug": "remove-nth-node-from-end-of-list", "title": "Remove Nth Node From End of List", "difficulty": "Medium", "order": 5},
        {"slug": "merge-k-sorted-lists", "title": "Merge K Sorted Lists", "difficulty": "Hard", "order": 6}
      ]
    },
    {
      "name": "Trees",
      "order": 7,
      "problems": [
        {"slug": "invert-binary-tree", "title": "Invert Binary Tree", "difficulty": "Easy", "order": 1},
        {"slug": "maximum-depth-of-binary-tree", "title": "Maximum Depth of Binary Tree", "difficulty": "Easy", "order": 2},
        {"slug": "same-tree", "title": "Same Tree", "difficulty": "Easy", "order": 3},
        {"slug": "subtree-of-another-tree", "title": "Subtree of Another Tree", "difficulty": "Easy", "order": 4},
        {"slug": "lowest-common-ancestor-of-a-binary-search-tree", "title": "Lowest Common Ancestor of a BST", "difficulty": "Medium", "order": 5},
        {"slug": "binary-tree-level-order-traversal", "title": "Binary Tree Level Order Traversal", "difficulty": "Medium", "order": 6},
        {"slug": "validate-binary-search-tree", "title": "Validate Binary Search Tree", "difficulty": "Medium", "order": 7},
        {"slug": "kth-smallest-element-in-a-bst", "title": "Kth Smallest Element in a BST", "difficulty": "Medium", "order": 8},
        {"slug": "construct-binary-tree-from-preorder-and-inorder-traversal", "title": "Construct Binary Tree from Preorder and Inorder", "difficulty": "Medium", "order": 9},
        {"slug": "binary-tree-maximum-path-sum", "title": "Binary Tree Maximum Path Sum", "difficulty": "Hard", "order": 10},
        {"slug": "serialize-and-deserialize-binary-tree", "title": "Serialize and Deserialize Binary Tree", "difficulty": "Hard", "order": 11}
      ]
    },
    {
      "name": "Tries",
      "order": 8,
      "problems": [
        {"slug": "implement-trie-prefix-tree", "title": "Implement Trie (Prefix Tree)", "difficulty": "Medium", "order": 1},
        {"slug": "design-add-and-search-words-data-structure", "title": "Design Add and Search Words Data Structure", "difficulty": "Medium", "order": 2},
        {"slug": "word-search-ii", "title": "Word Search II", "difficulty": "Hard", "order": 3}
      ]
    },
    {
      "name": "Heap / Priority Queue",
      "order": 9,
      "problems": [
        {"slug": "find-median-from-data-stream", "title": "Find Median from Data Stream", "difficulty": "Hard", "order": 1},
        {"slug": "merge-k-sorted-lists", "title": "Merge K Sorted Lists", "difficulty": "Hard", "order": 2}
      ]
    },
    {
      "name": "Backtracking",
      "order": 10,
      "problems": [
        {"slug": "combination-sum", "title": "Combination Sum", "difficulty": "Medium", "order": 1},
        {"slug": "word-search", "title": "Word Search", "difficulty": "Medium", "order": 2}
      ]
    },
    {
      "name": "Graphs",
      "order": 11,
      "problems": [
        {"slug": "number-of-islands", "title": "Number of Islands", "difficulty": "Medium", "order": 1},
        {"slug": "clone-graph", "title": "Clone Graph", "difficulty": "Medium", "order": 2},
        {"slug": "pacific-atlantic-water-flow", "title": "Pacific Atlantic Water Flow", "difficulty": "Medium", "order": 3},
        {"slug": "course-schedule", "title": "Course Schedule", "difficulty": "Medium", "order": 4},
        {"slug": "graph-valid-tree", "title": "Graph Valid Tree", "difficulty": "Medium", "order": 5},
        {"slug": "number-of-connected-components-in-an-undirected-graph", "title": "Number of Connected Components", "difficulty": "Medium", "order": 6}
      ]
    },
    {
      "name": "Advanced Graphs",
      "order": 12,
      "problems": [
        {"slug": "alien-dictionary", "title": "Alien Dictionary", "difficulty": "Hard", "order": 1}
      ]
    },
    {
      "name": "1-D Dynamic Programming",
      "order": 13,
      "problems": [
        {"slug": "climbing-stairs", "title": "Climbing Stairs", "difficulty": "Easy", "order": 1},
        {"slug": "house-robber", "title": "House Robber", "difficulty": "Medium", "order": 2},
        {"slug": "house-robber-ii", "title": "House Robber II", "difficulty": "Medium", "order": 3},
        {"slug": "longest-palindromic-substring", "title": "Longest Palindromic Substring", "difficulty": "Medium", "order": 4},
        {"slug": "palindromic-substrings", "title": "Palindromic Substrings", "difficulty": "Medium", "order": 5},
        {"slug": "decode-ways", "title": "Decode Ways", "difficulty": "Medium", "order": 6},
        {"slug": "coin-change", "title": "Coin Change", "difficulty": "Medium", "order": 7},
        {"slug": "maximum-product-subarray", "title": "Maximum Product Subarray", "difficulty": "Medium", "order": 8},
        {"slug": "word-break", "title": "Word Break", "difficulty": "Medium", "order": 9},
        {"slug": "longest-increasing-subsequence", "title": "Longest Increasing Subsequence", "difficulty": "Medium", "order": 10}
      ]
    },
    {
      "name": "2-D Dynamic Programming",
      "order": 14,
      "problems": [
        {"slug": "unique-paths", "title": "Unique Paths", "difficulty": "Medium", "order": 1},
        {"slug": "longest-common-subsequence", "title": "Longest Common Subsequence", "difficulty": "Medium", "order": 2}
      ]
    },
    {
      "name": "Greedy",
      "order": 15,
      "problems": [
        {"slug": "maximum-subarray", "title": "Maximum Subarray", "difficulty": "Medium", "order": 1},
        {"slug": "jump-game", "title": "Jump Game", "difficulty": "Medium", "order": 2}
      ]
    },
    {
      "name": "Intervals",
      "order": 16,
      "problems": [
        {"slug": "insert-interval", "title": "Insert Interval", "difficulty": "Medium", "order": 1},
        {"slug": "merge-intervals", "title": "Merge Intervals", "difficulty": "Medium", "order": 2},
        {"slug": "non-overlapping-intervals", "title": "Non-overlapping Intervals", "difficulty": "Medium", "order": 3},
        {"slug": "meeting-rooms", "title": "Meeting Rooms", "difficulty": "Easy", "order": 4},
        {"slug": "meeting-rooms-ii", "title": "Meeting Rooms II", "difficulty": "Medium", "order": 5}
      ]
    },
    {
      "name": "Math & Geometry",
      "order": 17,
      "problems": [
        {"slug": "rotate-image", "title": "Rotate Image", "difficulty": "Medium", "order": 1},
        {"slug": "spiral-matrix", "title": "Spiral Matrix", "difficulty": "Medium", "order": 2},
        {"slug": "set-matrix-zeroes", "title": "Set Matrix Zeroes", "difficulty": "Medium", "order": 3}
      ]
    },
    {
      "name": "Bit Manipulation",
      "order": 18,
      "problems": [
        {"slug": "number-of-1-bits", "title": "Number of 1 Bits", "difficulty": "Easy", "order": 1},
        {"slug": "counting-bits", "title": "Counting Bits", "difficulty": "Easy", "order": 2},
        {"slug": "reverse-bits", "title": "Reverse Bits", "difficulty": "Easy", "order": 3},
        {"slug": "missing-number", "title": "Missing Number", "difficulty": "Easy", "order": 4},
        {"slug": "sum-of-two-integers", "title": "Sum of Two Integers", "difficulty": "Medium", "order": 5}
      ]
    }
  ]'::jsonb
) ON CONFLICT (name) DO UPDATE SET
  description = EXCLUDED.description,
  total_problems = EXCLUDED.total_problems,
  categories = EXCLUDED.categories,
  updated_at = NOW();
