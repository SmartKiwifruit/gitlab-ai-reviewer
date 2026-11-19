## Review Rules: Warning (Important)

This file defines important-notice-level review rules. When warning issues are found, the Score is in the **60-80** range and the Status is **Pass**.

### Review Attitude

- **Report only hazards with real impact**; do not report theoretical possibilities.
- **If the code has a reasonable contextual explanation** (e.g. a known workaround, business constraints), do not report it.
- **Do not duplicate issues already covered by critical.** If an issue is already defined in critical.md, report it as critical.

---

### 1. Error Handling

The following issues make errors hard to diagnose and recover from:

- **Swallowed exceptions**: Empty catch/except blocks where exceptions are silently ignored. Typical counterexample: `try { ... } catch (e) { }` or `try: ... except: pass`
- **Generic Exception fallbacks**: Handling all exceptions the same way, without distinguishing network timeouts, insufficient permissions, missing data, etc.
- **Error messages losing context**: Printing only "Error occurred" without the operation target, key parameters, or stack trace. Logs should contain enough debugging information.

### 2. Concurrency & Timeouts

The following issues cause failures under high concurrency or unstable networks:

- **Shared state without synchronization**: Multi-threaded/coroutine access to shared data without locks, atomic operations, or other synchronization mechanisms.
- **Missing await on async operations**: Calling an async function without await, causing errors to go uncaught and execution order to break. This is the most common async bug.
- **External calls without timeouts**: Database queries, HTTP requests, message queue operations, etc. without timeout settings, potentially hanging requests indefinitely.
- **Potential deadlocks**: Locks acquired in inconsistent orders across code paths, or blocking operations (e.g. network requests) performed while holding a lock.

### 3. Performance Traps

The following issues cause severe performance degradation as data volume grows:

- **N+1 queries**: Database queries or HTTP requests executed inside loops. Use batch fetching instead. Typical counterexample: `for user in users: db.query("SELECT orders WHERE user_id = ?", user.id)`
- **Batchable network/database calls in loops**: Multiple individual calls that could be merged into a single batch call.
- **Unbounded queries**: Queries without LIMIT or pagination that can overwhelm the database or memory as data grows.
- **Large objects recreated in loops**: Large objects/strings repeatedly created inside loops or hot paths; extract them outside the loop or reuse references.

### 4. Input Validation

The following issues cause failures when handling unexpected input:

- **External input used without validation**: Input from users, APIs, files, or the environment is used directly without validation. Note: input validation issues on security-sensitive paths (e.g. SQL, command execution) count as critical.
- **Missing boundary checks**: Edge cases like empty strings, null/nil, empty collections, very large or very small values are not handled.
- **Unverified type assumptions**: Assuming input is always a certain type (e.g. definitely a number, definitely non-empty) without type checks or conversion.

### 5. API Contracts

The following issues make APIs unreliable or hard to use:

- **HTTP method misuse**: GET requests modifying server state, or using POST where PUT/PATCH belongs.
- **Wrong status code semantics**: Wrapping errors in 200 responses, or error codes that don't distinguish scenarios (all errors return 500).
- **Missing idempotency**: Repeated calls to the same API produce side effects. In particular, methods other than POST should be idempotent.
- **Inconsistent response formats**: Success/error response formats are not uniform across an API group, increasing complexity for callers.

---

### Scoring Guide

| Findings | Score | Status |
|----------|-------|--------|
| Warning issues only | 60-80 | Pass |
| Warning + info issues | 60-80 | Pass |
| Any critical issue | See critical.md | Needs Revision |
