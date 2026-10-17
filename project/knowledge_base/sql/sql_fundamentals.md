# SQL Fundamentals

## 1. JOIN Types and Relational Operations
- **INNER JOIN:** Selects records with matching keys in both participating tables.
- **LEFT (OUTER) JOIN:** Returns all left table records; matching right rows populate, otherwise fill with `NULL`.
- **RIGHT (OUTER) JOIN:** Returns all right table records; matching left rows populate, otherwise fill with `NULL`.
- **FULL (OUTER) JOIN:** Retains all records from both tables, populating missing sides with `NULL`.
- **CROSS JOIN:** Produces Cartesian product ($M \times N$ rows) matching every left row with every right row.

## 2. Aggregations: GROUP BY and HAVING
- **GROUP BY:** Aggregates row subsets by unique column values for functions (`COUNT`, `SUM`, `AVG`, `MIN`, `MAX`).
- **WHERE vs. HAVING:** `WHERE` filters rows *before* grouping (no aggregates allowed); `HAVING` filters aggregated output *after* grouping completes.

## 3. Subqueries
- **Scalar Subquery:** Produces a single scalar value usable in expressions and conditional comparisons.
- **Correlated Subquery:** References outer query attributes, executing per outer candidate row.
- **Set Operators:** `EXISTS` tests boolean row presence and halts on first match; `IN` compares values to a set.

## 4. Indexing: B-Tree and Hash
- **B-Tree Index:** Balanced tree structure with $O(\log n)$ search, insert, and range scans (`<`, `>`, `BETWEEN`).
- **Hash Index:** Bucket lookup providing $O(1)$ equality operations; cannot perform range queries or sorting.
- **Clustered vs. Non-Clustered:** Clustered index controls physical disk order (one per table, usually PK). Non-clustered index stores sorted search keys containing row pointers.

## 5. Database Normalization
- **1NF:** Atomic attribute values, no repeating groups, unique primary key.
- **2NF:** In 1NF; eliminates partial dependencies (non-keys depend on entire candidate key).
- **3NF:** In 2NF; eliminates transitive dependencies (non-keys depend only on candidate keys).
- **BCNF:** Stricter 3NF where every determinant in a functional dependency is a superkey.
- **Denormalization:** Selective schema redundancy to accelerate intensive read queries.

## 6. ACID Properties and Transactions
- **Atomicity:** All-or-nothing execution across operations.
- **Consistency:** Ensures constraints and database validity rules hold post-transaction.
- **Isolation:** Prevents concurrent transaction conflicts across standard levels: Read Uncommitted, Read Committed, Repeatable Read, and Serializable (prevents dirty reads, non-repeatable reads, phantom reads).
- **Durability:** Committed data is safely written to disk using Write-Ahead Logging (WAL).
- **Commands:** `BEGIN TRANSACTION`, `COMMIT`, `ROLLBACK`, `SAVEPOINT`.

## 7. Window Functions, Views, and Optimization
- **Window Functions:** Evaluate aggregates across row windows without collapsing rows: `OVER (PARTITION BY ... ORDER BY ...)`. Includes `ROW_NUMBER()`, `RANK()`, `DENSE_RANK()`, `LEAD()`, `LAG()`.
- **Views & Procedures:** Views offer virtual queries; materialized views persist results. Stored procedures store precompiled database logic.
- **Optimization:** Inspect plans with `EXPLAIN ANALYZE`. Keep queries sargable (avoid functions on indexed columns in `WHERE`), omit redundant `SELECT *`, and index foreign keys.
