# Python Fundamentals

## 1. Data Types and Mutability
- **Immutable Types:** `int`, `float`, `bool`, `str`, `tuple`, `frozenset`. Modifications allocate a new object; references cannot mutate in-place.
- **Mutable Types:** `list`, `dict`, `set`, `bytearray`. Changes modify the object in-place without altering its memory address (`id()`).
- **Copying:** Shallow copy (`copy.copy()`) duplicates the container while maintaining references to nested objects. Deep copy (`copy.deepcopy()`) recursively clones all nested objects.
- **Mutable Default Arguments:** Function default arguments evaluate once at definition time. Using `def append_to(item, target=[])` creates shared state across calls; always use `target=None`.

## 2. Comprehensions and Generators
- **Comprehensions:** List, dict, and set comprehensions provide concise loops executed in optimized C-level bytecode: `[x**2 for x in nums if x > 0]`.
- **Generators:** Functions using `yield` return lazy iterators that produce values on demand, preserving execution frames with $O(1)$ memory usage.
- **Iterator Protocol:** Requires `__iter__()` returning the iterator and `__next__()` producing the next item or raising `StopIteration`.

## 3. Decorators and Context Managers
- **Decorators:** Higher-order functions wrapping callables to extend behavior. Use `@functools.wraps(fn)` to preserve original function name and docstrings.
- **Context Managers:** Ensure safe resource lifecycle using `with`. Implemented via `__enter__()` and `__exit__()` (for cleanup and exception handling) or `@contextlib.contextmanager`.

## 4. GIL and Concurrency
- **Global Interpreter Lock (GIL):** A CPython mutex ensuring only one native thread executes bytecode at once, protecting reference-count integrity.
- **Concurrency Trade-offs:** Threading benefits I/O-bound tasks by releasing GIL during I/O operations. CPU-bound tasks require `multiprocessing` to utilize multiple CPU cores.

## 5. Memory Management and Garbage Collection
- **Reference Counting:** CPython's primary memory management tracks active pointers (`ob_refcnt`). Objects deallocate immediately when count hits zero.
- **Generational GC:** Collects reference cycles via three generations (Gen 0, 1, 2) based on object survival age, scanning younger generations most frequently.

## 6. Functions, Arguments, and Built-ins
- ***args and \*\*kwargs:** `*args` collects extra positional arguments into a tuple; `**kwargs` gathers extra keyword arguments into a dictionary.
- **Lambda:** Anonymous inline functions limited to a single expression: `sorted(items, key=lambda x: x['score'])`.
- **Core Built-ins:** `zip()` aggregates iterables, `enumerate()` adds index counters, `any()`/`all()` provide short-circuiting logical evaluation.

## 7. Exception Handling Patterns
- **Structure:** `try` runs target logic, `except` handles specific errors, `else` runs only when no errors occur, and `finally` runs unconditionally for teardown.
- **Exception Chaining:** `raise CustomException() from original_err` retains underlying exception traces.
