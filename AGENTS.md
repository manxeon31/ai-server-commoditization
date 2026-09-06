# AGENTS.md

## Mission
Maintain a deterministic, auditable monitor that tracks whether the AI-server hardware layer is becoming commoditized across Dell Technologies, NVIDIA, Hewlett Packard Enterprise, and Super Micro Computer.

## Non-negotiables
- Prefer official SEC filings and attached earnings releases as primary sources.
- Never invent or infer a missing financial metric. Use `null` / unavailable.
- Every extracted metric must retain source URL, filing accession, evidence snippet, and confidence.
- Keep the 0-100 Commoditization Index deterministic and documented. The LLM, if added later, may explain a score but must never calculate or override it.
- Tests must use local fixtures or mocks. Do not make tests depend on the live internet.
- A partial earnings cycle must never generate a quarterly report.
- First live run establishes a baseline and must not generate a report.
- Avoid committing weekly no-op state churn.
- Never log secrets or a user's SEC contact string.
- Before completing changes, run `pytest`.

## Design preference
Keep the code small, typed, and inspectable. Favor explicit rules over opaque abstractions. Financial extraction should fail conservatively.
