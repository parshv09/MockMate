# Data Structures & Algorithms Fundamentals

## 1. Asymptotic Complexity and Big-O Notation
- **Order of Growth:** $O(1) < O(\log n) < O(n) < O(n \log n) < O(n^2) < O(2^n) < O(n!)$.
- **Definitions:** Big-O ($O$) describes upper bound worst-case; Big-Omega ($\Omega$) describes lower bound; Big-Theta ($\Theta$) denotes tight asymptotically bound complexity.
- **Space Complexity:** Considers auxiliary runtime allocations plus stack depth from recursive call frames.

## 2. Linear Data Structures
- **Arrays:** Contiguous memory allocations. Offers $O(1)$ random indexing, but amortized $O(1)$ push and $O(n)$ arbitrary insertions/deletions due to element shifting.
- **Linked Lists:** Singly/Doubly linked nodes holding data and pointers. $O(1)$ insertions/deletions once pointer is positioned; $O(n)$ sequential search. Eliminates reallocation overhead.
- **Stacks & Queues:**
  - *Stack:* Last-In-First-Out (LIFO). Push, pop, peek operate in $O(1)$ (e.g., call stacks, parenthesis matching).
  - *Queue:* First-In-First-Out (FIFO). Enqueue, dequeue run in $O(1)$ (e.g., BFS, job scheduling, circular buffers, deques).

## 3. Hash Tables
- **Mechanics:** Computes array bucket index using a hash function on keys.
- **Collisions:** Resolved via *Separate Chaining* (linked lists or balanced trees per bucket) or *Open Addressing* (Linear/Quadratic probing).
- **Complexity:** Average $O(1)$ for insert, search, delete; degrades to $O(n)$ under poor hash distribution or high load factor triggering resizing.

## 4. Trees, BST, and Heaps
- **Binary Trees:** Hierarchical nodes with left/right children. Traversals: Pre-order (Root-L-R), In-order (L-Root-R: yields sorted sequence in BST), Post-order (L-R-Root), Level-order (BFS).
- **Binary Search Tree (BST):** Left child < Root < Right child. Search/Insert takes $O(\log n)$ average, degrading to $O(n)$ in degenerate skewed trees. Balanced variants (AVL, Red-Black) guarantee $O(\log n)$.
- **Binary Heap:** Complete binary tree satisfying heap property (Min-Heap: parent $\le$ children; Max-Heap: parent $\ge$ children). Array representation: child indices $2i+1, 2i+2$. Find min/max in $O(1)$; insert/delete in $O(\log n)$; heap construction (`heapify`) in $O(n)$.

## 5. Graphs and Traversals
- **Representations:** Adjacency Matrix ($O(V^2)$ space, $O(1)$ edge check) vs. Adjacency List ($O(V+E)$ space, optimal for sparse graphs).
- **Breadth-First Search (BFS):** Explores neighbors level-by-level using a FIFO queue. Time: $O(V+E)$; space: $O(V)$. Computes shortest path in unweighted graphs.
- **Depth-First Search (DFS):** Traverses deep into branches using a stack or recursion. Time: $O(V+E)$. Used for cycle detection, topological sorting, and connected components.

## 6. Sorting Algorithms
- **MergeSort:** Divide-and-conquer; stable; time: $O(n \log n)$ across all cases; requires $O(n)$ auxiliary space.
- **QuickSort:** Partition-based; unstable; average time: $O(n \log n)$; worst case: $O(n^2)$ with bad pivot; $O(\log n)$ recursion stack.
- **HeapSort:** In-place, unstable; guaranteed $O(n \log n)$ time and $O(1)$ auxiliary space.
- **Elementary Sorts:** Insertion, Selection, Bubble sorts run in $O(n^2)$ time.

## 7. Dynamic Programming & Core Algorithmic Techniques
- **Dynamic Programming (DP):** Solves problems with *Overlapping Subproblems* and *Optimal Substructure*.
  - *Memoization (Top-down):* Recursive decomposition caching results in hash map or array.
  - *Tabulation (Bottom-up):* Iterative table filling from base cases up to target solution.
- **Two-Pointer Technique:** Operates two indices traversing toward each other (e.g., sorted two-sum) or in the same direction (fast/slow pointers for linked list cycle detection).
- **Sliding Window:** Maintains a contiguous window over an array/string (fixed or dynamic size via expanding/contracting bounds) to compute sub-ranges in $O(n)$ time.
