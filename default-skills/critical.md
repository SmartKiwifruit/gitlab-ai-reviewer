## Review Rules: Critical (Blocking)

This file defines blocking-level review rules. When any critical issue is found, the Status MUST be **Needs Revision** and the Score MUST NOT exceed **40** (it may decrease further based on the number of issues; there is no lower bound).

### Review Attitude

- **Report only issues you are confident will cause production incidents.** If you are not sure whether an issue is critical, report it as a warning instead — do not escalate.
- **Do not mark something critical just because it "might be risky"**; there must be a concrete attack path or failure scenario.
- **Do not report the same issue twice.** Report each issue only once, in one place.

---

### 1. Injection & Access Control

The following issues can directly lead to system compromise or data theft:

- **SQL/NoSQL injection**: User input is concatenated into queries instead of using parameterized queries or an ORM. Typical counterexample: `query = f"SELECT * FROM users WHERE id = {user_input}"`
- **Command injection**: User input is passed to system command execution (exec, system, subprocess, etc.) without strict validation and escaping.
- **Template injection**: User input is embedded directly into a template engine (Jinja2, Twig, Pug, etc.), potentially leading to remote code execution.
- **Path traversal**: User-supplied file paths are used without restricting them to the intended directory. Typical counterexample: `open(user_input)` instead of `open(safe_dir / basename(user_input))`
- **Missing authorization**: Endpoints/routes lack authentication. Do not assume "the frontend already restricts access".
- **Broken access control**: User A can access user B's data by modifying an ID. Every query should verify resource ownership.

### 2. Sensitive Data Exposure

The following issues leak sensitive information:

- **Sensitive data in logs**: Passwords, tokens, national ID numbers, bank card numbers, etc. appear in log output.
- **Error messages leaking internals**: Error messages returned to users contain stack traces, database schemas, internal IPs, file paths, etc.
- **Sensitive files committed to version control**: `.env` files, config files containing secrets, etc. are committed to the git repository.

### 3. Data Integrity

The following issues cause data loss or inconsistency:

- **Multi-step writes without transaction protection**: Multiple related write operations are not in the same transaction; partial success causes data inconsistency. Typical counterexample: update the account balance first, then write the transaction record, with no transaction protecting the two steps.
- **Race conditions causing data corruption**: Concurrent writes to shared data without locking or optimistic locking. Typical counterexample: two requests both read balance 100, each deduct 50, and both write back 50 instead of 0.
- **External input written to storage without validation**: Input from users/APIs/files is written directly to the database or filesystem without any validation. Note: input validation issues outside security-sensitive paths count as warning.

### 4. Critical Stability Defects

The following issues cause service crashes or unavailability:

- **Uncaught exceptions crashing the service**: Critical paths lack exception handling, causing entire requests to fail or even the process to exit. Note: exceptions that are caught but swallowed (empty catch) count as warning, not critical.
- **Resource leaks**: Files, network connections, database connections, locks, etc. are not released after use. Use the language's resource management constructs (context manager, defer, try-with-resources, using, etc.).
- **Infinite loops or deadlocks**: Loops lack exit conditions, or locks are acquired in inconsistent orders across code paths, causing deadlocks.

### 5. Cryptographic Misuse

The following issues render cryptographic protection useless:

- **Weak hashes for password storage**: Passwords stored with fast hashes like MD5 or SHA1. Use slow hash algorithms such as bcrypt, scrypt, or Argon2.
- **Hand-rolled encryption**: Writing custom encryption logic instead of using a vetted cryptographic library.
- **Predictable randomness in security contexts**: Generating tokens, keys, or salts with non-cryptographically-secure random sources (e.g. Math.random(), rand()). Use crypto.getRandomValues(), the secrets module, etc.

---

### Scoring Guide

| Findings | Score | Status |
|----------|-------|--------|
| Any critical issue | ≤ 40 (decreases with count) | Needs Revision |
| No critical issues | See warning.md / info.md | See warning.md / info.md |
