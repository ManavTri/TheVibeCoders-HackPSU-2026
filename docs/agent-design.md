# Gemini financial planning chat agent

`POST /api/ai/chat` is a stateless, authenticated assistant endpoint. It accepts
`message` (at most 2,000 characters), up to 12 user/assistant history messages,
and up to 20 selected `contextDocuments`. It returns a concise `reply`,
suggested follow-ups, the document `sources` used, and any `pendingActions`.
History is supplied by the client for that request and is never persisted by
the API.

The endpoint requires backend-only `LLM_API_KEY` and `LLM_MODEL` settings. If
they are missing or Gemini is unavailable, the API returns a friendly 503. The
manual function-calling loop uses the `google-genai` SDK with automatic function
calling disabled. It makes at most six model calls, has a 40-second wall-clock
budget, and caps generated output at 1,024 tokens. A per-user in-memory token
bucket allows at most 20 chat requests per 10 minutes, with one concurrent
chat per user. Confirm/cancel endpoints have a separate limit of 10 calls
per 10 minutes. Large document, finding, and deadline results are capped
before being sent to the model; totals indicate when a result was truncated.

## Tool allowlist

Every repository call receives the authenticated user ID from the server. The
model is never given a `user_id` argument, and document lookups are scoped to
that ID. Tool results are treated as untrusted document data.

| Tool | Access | Behavior |
|---|---|---|
| `list_documents(state)` | Read | Lists the user's active, archived, or deleted documents |
| `get_document(id)` | Read | Returns extracted fields for one owned document |
| `get_findings()` | Read | Returns current findings for active, extracted documents |
| `compare_documents(ids)` | Read | Runs existing validation rules against selected owned documents |
| `get_deadlines()` | Read | Lists explicit deadlines from active extracted documents |
| `financial_summary()` | Read | Sums explicit amounts in Python by currency, separating aid, costs, loans, and remaining balance |
| `cost_compare(option_ids)` | Read | Sums eligible extracted costs deterministically by currency |
| `explain_finding(finding_id)` | Read | Explains a current finding belonging to this user |
| `archive_document(id)` | Write proposal | Creates a pending action; does not archive |
| `restore_document(id)` | Write proposal | Creates a pending action; does not restore |
| `correct_document_field(id, field, value)` | Write proposal | Creates a pending action; field/value are validated when confirmed |
| `reextract_document(id)` | Write proposal | Creates a pending action; preserves user-edited fields when confirmed |
| `recheck_documents()` | Write proposal | Creates a pending action; starts a persisted validation only after confirmation |

There is deliberately no permanent-delete, upload, arbitrary repository, user
settings, network, or URL-fetch tool. Financial totals are calculated by
deterministic Python code; the model must not do arithmetic itself. Values and
dates must be grounded in the returned document data. Missing information is
identified rather than guessed. The assistant offers informational guidance,
not legal, tax, or licensed financial advice.

## Confirmation gate

Write-tool calls only create a random, server-side pending action containing
the authenticated owner, tool, validated arguments, and a 10-minute expiry.
The client receives the action ID, tool name, summary, and arguments. No write
occurs until the same authenticated user calls
`POST /api/ai/actions/{id}/confirm`. Confirmation checks owner and expiry,
removes the action before execution so it is single-use, then invokes the
user-scoped repository operation. The agent can propose at most one write per
chat request, and each user can have at most three outstanding actions.
Repeated identical proposals reuse the existing server-side confirmation ID.
While an action is pending, the frontend pauses new submissions and hides
suggested prompts; it displays the action card instead of the model's separate
conversational confirmation question.
`POST /api/ai/actions/{id}/cancel` discards the action. Unknown or other-user
IDs return 404; expired actions return 410.

Pending actions, the rate limiter, and concurrency guard are process-local
memory and are lost on restart. In a multi-instance deployment, confirmation
must reach the same API instance that created the action; use a single instance
or introduce shared server-side state before scaling out.

## Threat model and privacy

- **Document prompt injection:** PDF-derived fields, filenames, summaries, and
  finding text are returned inside explicit untrusted-data delimiters. The
  system prompt says document content is data, never instructions, and that
  document text must never initiate a tool call. The server independently
  gates every write tool behind explicit confirmation.
- **Cross-user access:** the server injects the verified `current_user` subject
  into each tool execution. Every read and write uses the repositories' scoped
  methods. IDs supplied by the model are not trusted; they are validated and
  looked up for the current owner.
- **Destructive actions:** the agent cannot permanently delete documents or
  delete accounts. The only exposed writes are archive, restore, field
  correction, re-extraction, and validation recheck, each behind the
  confirmation endpoint. Correction values are parsed through the same
  Pydantic field constraints used by the document API, including finite,
  non-negative amounts and ISO date parsing. The confirmation card shows the
  stored value and proposed value before the user submits the single confirm
  action. If the stored field changes after proposal, confirmation fails instead
  of overwriting the newer value.
- **Resource abuse:** request length/history limits, six model iterations,
  output-token and wall-clock caps, per-user chat/action rate limits, one
  pending write proposal per chat, a three-action outstanding cap, and one
  concurrent chat per user bound the agent's work. The frontend applies a
  matching 20-per-10-minute local chat limit for usability, prevents repeated
  submits synchronously, and keeps the conversation mounted while navigating
  between app pages. Backend limits remain authoritative.
- **Logging:** logs include tool names, durations, and user identifiers only.
  They never include user messages, document content, model output, exception
  details, or credentials.
- **External processing:** when enabled, Gemini receives the current message,
  client-supplied history, and only the document-derived tool results required
  for the conversation. Review provider data-handling terms before use with
  real financial documents; use synthetic documents for demos.
