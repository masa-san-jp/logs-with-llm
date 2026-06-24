# Thug-Fugu Repository Review

Date: 2026-06-24  
Repository: `masa-san-jp/Thug-Fugu`  
Review type: static repository review

## Executive Summary

Thug-Fugu is a compact, local-first Python implementation for coordinating multiple local LLM roles and exposing the result through a minimal OpenAI Chat Completions-compatible API. The repository is coherent, intentionally small, dependency-free, and reasonably well documented. It is already usable as a private/local experimental tool.

Current maturity: **prototype+ / local private-network tool**. It is not yet a hardened service, which is consistent with the repository’s own positioning.

Overall score: **7.4 / 10**

## What is strong

1. **Clear architecture**
   - The implementation is separated into config loading, backend adapters, orchestration, HTTP server, and CLI.
   - The orchestration model is simple and understandable: select worker roles, run them concurrently, synthesize, then fall back to deterministic merge.

2. **Good local-first discipline**
   - No runtime dependencies.
   - `pyproject.toml` uses `src` layout and exposes a CLI entrypoint.
   - Echo backend enables offline tests and development without a real LLM.

3. **Configuration validation is solid**
   - Unknown backends, missing HTTP backend `base_url`, invalid role model references, duplicate names, invalid selection policy, non-positive concurrency, and invalid token limits are validated.

4. **Failure isolation exists**
   - Worker failures are captured per role.
   - Total failure raises an orchestration error.
   - Synthesizer failure falls back to deterministic merge.

5. **Security posture is honestly documented**
   - The repository clearly states that the built-in server is local/private-network oriented and not a hardened internet service.
   - Request body size limits and server-level concurrency limits exist.
   - Prompt and generation content are intentionally excluded from normal structured logs.

6. **Test coverage is meaningful for the current size**
   - Config, server, orchestration, fallback behavior, request limits, concurrency exhaustion, and observability are covered.
   - GitHub Actions runs unit tests across Python 3.9–3.12 and builds/install-smoke-tests the package.

## Main findings

### P0 — Backend error handling can leak sensitive content into logs/errors

`_post_json()` includes the raw HTTP error response body in `BackendError`. That error can be stored in `WorkerResult.error` and included in orchestrator structured logs. This conflicts with the intent that prompts and generated content are not logged by default, because some local LLM servers may echo request fragments, prompts, or generated text in error responses.

Recommended fix:
- Do not include raw backend error body in `BackendError` by default.
- Log only status code, backend type, host, and a short sanitized error category.
- Keep raw backend response bodies only behind an explicit debug flag, and redact by default.
- Add tests proving prompt strings do not appear in logs when backend HTTP errors occur.

### P1 — Invalid `messages` requests can be mapped to 502 instead of 400

The HTTP layer validates `stream`, `tools`, and `tool_choice`, then calls `messages_from_dicts()`. Invalid or missing `messages` can raise `OrchestrationError`, which the HTTP layer maps to 502. That makes a client-side request-shape error look like a backend/orchestration failure.

Recommended fix:
- Validate `messages` in `_validate_chat_completion_request()`.
- Require a non-empty list of objects.
- Require string `role` and string `content`.
- Consider restricting roles to `system`, `user`, `assistant`, and maybe `tool` only when tool support exists.
- Map schema errors to 400.

### P1 — Unsafe bind should require explicit acknowledgement

The CLI allows arbitrary `--host`. The documentation correctly says the built-in server should not be exposed directly and lists future work for unsafe-bind warnings. This should be enforced in code before broader use.

Recommended fix:
- If host is not `127.0.0.1`, `localhost`, or `::1`, print a warning.
- For `0.0.0.0` / `::`, require `--allow-unsafe-bind`.
- Optionally print a one-line checklist: TLS/auth/rate limit/reverse proxy required.

### P1 — Request-level deadline is missing

Each backend call has its own timeout, but an overall orchestration can still wait for the slowest selected worker before synthesis. With multiple roles, a single slow worker can dominate latency.

Recommended fix:
- Add an optional `orchestrator.request_timeout_seconds`.
- Derive per-worker remaining budget from the request deadline.
- Return partial successful worker results once deadline expires, rather than waiting for every worker until individual backend timeout.

### P2 — Keyword selection policy is intentionally simple but brittle

The `keyword` policy does substring matching against the latest user message. This is easy to reason about but can overmatch or undermatch, especially across English/Japanese mixed prompts.

Recommended fix:
- Keep current behavior as `keyword_substring`.
- Add future policies such as `keyword_regex`, `role_router`, or `llm_router`.
- Add tests for Japanese keywords, mixed-case English, and accidental substring matches.

### P2 — OpenAI compatibility is explicit but minimal

The repository is transparent that streaming, tool calling, multimodal messages, `/v1/models`, and accurate token usage are out of scope for now. This is acceptable, but clients may still infer more compatibility than actually exists.

Recommended fix:
- Add `/v1/models` with a minimal local response if targeting OpenAI-compatible tooling.
- Consider `usage: null` or an explicit custom metadata field if zero token counts are placeholders.
- Add compatibility tests for common clients that the project intends to support.

## Suggested next PR sequence

1. **PR 1: Harden HTTP request validation**
   - Move `messages` validation into `_validate_chat_completion_request()`.
   - Add tests for missing, empty, non-list, and malformed messages.
   - Ensure all request-shape errors return 400.

2. **PR 2: Redact backend errors**
   - Sanitize `BackendError`.
   - Add log redaction tests for HTTPError paths.
   - Keep debug-only raw error body behind an explicit flag.

3. **PR 3: Unsafe bind guard**
   - Add CLI guard for non-localhost bind.
   - Add `--allow-unsafe-bind`.
   - Test CLI argument behavior.

4. **PR 4: Request deadline**
   - Add optional global orchestration deadline.
   - Return partial results where appropriate.
   - Document timeout semantics.

5. **PR 5: Tooling quality**
   - Add `ruff` or equivalent linting.
   - Add coverage reporting.
   - Add package smoke test for `fugu-local run`, not only `validate-config`.

## Roadmap prioritization

Existing open issues already point in the right direction:
- model pools / failover / load balancing
- tool calling design
- streaming support
- distributed inference
- multi-GPU role/model assignment

Recommended priority order:
1. request validation + error redaction
2. unsafe bind enforcement
3. request-level deadline / partial-result behavior
4. model pools + failover
5. streaming
6. tool calling

Tool calling should not be implemented before the orchestration semantics are designed. With multiple workers and a synthesizer, tool execution semantics are materially different from single-model OpenAI-compatible serving.

## Bottom line

This is a clean and useful minimal implementation. The biggest gap is not architecture; it is boundary hardening. Fix request validation, error redaction, unsafe bind behavior, and global timeout semantics before adding larger features such as streaming, tool calling, or dynamic model pools.
