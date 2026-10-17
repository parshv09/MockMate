# Java Fundamentals

## 1. JVM Architecture
- **ClassLoader Subsystem:** Handles Loading (Bootstrap, Extension/Platform, Application), Linking (Verification, Preparation, Resolution), and Initialization.
- **JVM Memory Areas:**
  - **Heap Area:** Stores all runtime objects and instance variables; managed by the Garbage Collector.
  - **Metaspace (Method Area):** Stores class metadata, bytecode, and static variables in native memory.
  - **JVM Stack & PC Registers:** Thread-private frames storing local variables, method invocations, and instruction pointers.
- **Execution Engine:** Contains the Interpreter, JIT Compiler (compiles frequently executed hotspots to native machine code), and GC.

## 2. OOP Principles & Access Modifiers
- **Encapsulation:** Protects internal state using `private` fields exposed via public getters/setters.
- **Inheritance:** Class extension via `extends` (single class inheritance; multiple interface implementation).
- **Polymorphism:** Compile-time (method overloading) and runtime (method overriding resolved via dynamic dispatch).
- **Abstraction:** Interface contracts and abstract base classes hiding underlying implementation details.
- **Access Modifiers:** `public` (accessible everywhere), `protected` (package and subclasses), `default` (package-private), `private` (class-only).

## 3. Abstract Classes vs. Interfaces
- **Abstract Classes:** Can declare instance variables, constructors, and concrete or abstract methods; models an "is-a" relationship.
- **Interfaces:** Define peripheral capabilities ("can-do"). Variables are implicitly `public static final`. Supports `default` and `static` methods (Java 8+) and `private` methods (Java 9+).

## 4. Collections Framework
- **ArrayList vs. LinkedList:** `ArrayList` uses dynamic array with fast $O(1)$ indexed reads and $O(n)$ shifts on middle inserts. `LinkedList` uses doubly-linked nodes with fast $O(1)$ pointer insertions but $O(n)$ traversal.
- **HashMap vs. TreeMap:** `HashMap` uses bucket hashing with $O(1)$ average lookups, converting buckets to Red-Black trees at 8 collisions ($O(\log n)$ worst-case). `TreeMap` implements `NavigableMap` using Red-Black trees for sorted keys in $O(\log n)$ time.

## 5. Exception Hierarchy
- **Throwable:** Root class splitting into `Error` (irrecoverable system failures like `OutOfMemoryError`) and `Exception`.
- **Checked Exceptions:** Subclasses of `Exception` (except `RuntimeException`) checked at compile time; require `try-catch` or `throws` (e.g., `IOException`, `SQLException`).
- **Unchecked Exceptions:** Subclasses of `RuntimeException` indicating logical bugs (e.g., `NullPointerException`, `IllegalArgumentException`).

## 6. Multithreading Basics
- **Thread Lifecycle:** `NEW`, `RUNNABLE`, `BLOCKED`, `WAITING`, `TIMED_WAITING`, `TERMINATED`.
- **Synchronization:** `synchronized` locks the intrinsic monitor to ensure mutual exclusion across critical sections.
- **Volatile Keyword:** Ensures immediate read/write visibility of variables across CPU thread caches and prohibits compiler reordering.

## 7. Garbage Collection, String Pool & Autoboxing
- **Garbage Collection:** Divides Heap into Young (Eden, S0, S1) and Old generations. Algorithms include G1GC (region-based) and ZGC (concurrent low-latency).
- **String Pool:** String literals are cached in the heap String Constant Pool. Strings are immutable for security and caching. `StringBuilder` is mutable and unsynchronized; `StringBuffer` is synchronized.
- **Autoboxing:** Automatic conversion between primitives (e.g., `int`) and wrappers (`Integer`). Values -128 to 127 are cached; unboxing `null` throws `NullPointerException`.
