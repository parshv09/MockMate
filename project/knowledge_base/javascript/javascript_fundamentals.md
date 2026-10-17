# JavaScript Fundamentals

## 1. Event Loop and Asynchronous Execution
JavaScript runs on a single-threaded runtime with an event-driven concurrency model.
- **Call Stack:** Synchronous execution frames organized in LIFO order.
- **Microtask Queue:** High-priority callbacks (`Promise` resolutions, `queueMicrotask`, `MutationObserver`). Drains completely after each call stack frame empties before any macrotask runs.
- **Macrotask Queue:** Timers (`setTimeout`, `setInterval`) and I/O callbacks.
- **Loop Tick:** Call Stack executes -> Microtask Queue drains -> Browser renders -> Next Macrotask executes.

## 2. Closures and Scope
- **Lexical Scope:** Inner functions have access to variables declared in their outer parent scopes.
- **Closure:** A function combined with references to its surrounding lexical environment. It preserves variable state even after the parent function has finished executing.
- **Use Cases:** Data encapsulation/private state, function currying, and memoization caches.

## 3. Hoisting and Declarations (var vs. let vs. const)
- **var:** Function-scoped, hoisted and initialized with `undefined`, allows re-declaration.
- **let & const:** Block-scoped `{}`. Hoisted into the **Temporal Dead Zone (TDZ)** where access prior to declaration throws `ReferenceError`. `const` prevents identifier reassignment.
- **Function Hoisting:** Full function declarations are hoisted with definition; function expressions assigned to variables are subject to variable hoisting rules.

## 4. 'this' Keyword and Arrow Functions
- **Binding Rules:**
  - *Default:* Global scope (`window` or `undefined` in strict mode).
  - *Implicit:* Calling object context (`object.method()`).
  - *Explicit:* Bound with `.call()`, `.apply()`, or `.bind()`.
  - *New:* Bound to newly created instance inside constructor functions.
- **Arrow Functions:** Lack own `this`, `arguments`, and `super`. They inherit `this` lexically from their enclosing context and cannot serve as constructors.

## 5. Prototypal Inheritance
- **Prototype Chain:** Objects link to an internal prototype (`[[Prototype]]` or `__proto__`). Property access checks the instance first, then walks up the chain until reaching `null`.
- **ES6 Classes:** Syntactic sugar over prototype delegation via `prototype` property and `Object.create()`.

## 6. Promises and Async/Await
- **Promise States:** `pending`, `fulfilled`, `rejected`. State changes are terminal and immutable.
- **Combinators:** `Promise.all()` (fails on first reject), `Promise.allSettled()` (waits for all), `Promise.race()` (first to settle), `Promise.any()` (first to fulfill).
- **Async/Await:** Syntactic sugar over Promises. Marked functions return promises; `await` pauses execution until fulfillment or rejection.

## 7. Type Coercion, Modern ES6+ & DOM
- **Falsy Values:** `false`, `0`, `""`, `null`, `undefined`, `NaN`.
- **Equality:** `==` allows implicit type coercion; `===` strictly checks value and data type.
- **ES6+ Syntax:** Destructuring, spread/rest (`...`), optional chaining (`?.`), nullish coalescing (`??`).
- **DOM & Web APIs:** Browser APIs (Fetch, Timers, LocalStorage). Events bubble upward from target element; stopped via `event.stopPropagation()`.
