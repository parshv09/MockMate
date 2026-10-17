# Node.js Fundamentals

## 1. Architecture and Event Loop
- **Event-Driven Non-Blocking I/O:** Runs on Chrome's V8 engine and `libuv`.
- **Libuv & Thread Pool:** Libuv manages an event loop and worker thread pool (default 4 threads, configurable with `UV_THREADPOOL_SIZE`). Offloads expensive operations (file I/O, DNS lookup, crypto, compression) to keep the main JavaScript thread non-blocking.
- **Event Loop Phases:**
  - *Timers:* Runs `setTimeout` and `setInterval` callbacks.
  - *Pending I/O:* Executes deferred system I/O callbacks.
  - *Poll:* Retrieves new I/O events and processes their handlers.
  - *Check:* Runs `setImmediate` callbacks.
  - *Close Callbacks:* Runs cleanup (e.g., `socket.on('close')`).
  - *Microtasks (`process.nextTick`, Promises):* Executed immediately after the current operation before moving forward.

## 2. CommonJS vs. ES Modules
- **CommonJS (CJS):** Synchronous dynamic imports using `require()` and `module.exports`. Evaluated at runtime.
- **ES Modules (ESM):** Asynchronous static imports using `import`/`export`. Enabled via `"type": "module"` in `package.json` or `.mjs`. Supports top-level `await`.

## 3. Buffers and Streams
- **Buffer:** Fixed-size raw memory allocated outside the V8 heap (`Buffer.alloc()`, `Buffer.from()`) for binary payloads.
- **Streams:** Process chunked data efficiently without loading whole files into RAM. Four types: `Readable`, `Writable`, `Duplex`, `Transform`.
- **Backpressure:** Managed via `.pipe()` or `stream.pipeline()` when read rate outpaces write capacity.

## 4. Clustering & Process Management
- **Cluster Module:** Spawns worker processes using `cluster.fork()`, sharing server ports across CPU cores.
- **Process Object:** `process.env` (environment variables), `process.argv` (CLI flags), `process.exit()`. Production setups use PM2 or containers for process monitoring and automatic restarts.

## 5. Express.js Middleware Architecture
- **Middleware:** Functions accessing `(req, res, next)`. Process incoming requests, modify state, or terminate responses.
- **Error Handling:** Special 4-parameter signature `(err, req, res, next)` mounted at the end of middleware chains.

## 6. Package Management & Error Handling
- **npm & SemVer:** `^` permits minor/patch updates; `~` permits patch updates only. `package-lock.json` ensures deterministic dependency resolution.
- **Error Types:** Distinguish operational errors (handled with try/catch and HTTP codes) from unhandled bugs. Monitor `unhandledRejection` and `uncaughtException`.

## 7. REST API Design Best Practices
- **HTTP Methods & Codes:** Proper use of `GET` (safe/idempotent), `POST`, `PUT`, `PATCH`, `DELETE` along with standard HTTP status codes (`200`, `201`, `204`, `400`, `401`, `403`, `404`, `500`).
- **Security:** Stateless auth tokens (JWT), request sanitization, rate limiting, and security headers with `helmet`.
