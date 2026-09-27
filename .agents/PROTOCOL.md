# Ledger protocol

The coordination ledger is `ledger.jsonl` on the orphan branch
`agents/ledger` of `origin`. It is append-only: every event adds one JSON
object, and the newest state record for a task is that task's current state.
Nothing is ever rewritten, so a lost push race is a rebase with no conflict.

## Lifecycle

```
claimed -> in_progress -> done -> tested -> released
```

- `note` adds an event and keeps the current status.
- `handoff` by the holder releases the claim (or, with `--paths`, drops those
  patterns from it) and messages the recipient. `handoff` by anyone else is a
  request message; the holder's state is untouched.
- A claim expires after `ttl_h` hours (default 4). Any update restarts the
  clock. Expired claims block nobody, but ask before reusing their paths.

## Record fields

State records: `id`, `task`, `agent`, `tool`, `status`, `paths`, `ts`
(UTC ISO-8601), `ttl_h`, `branch`; plus `intent` (claim), `message` (note),
`pr` (done), `evidence` and `preview` (tested), `to` (handoff).

Message records add `"kind": "message"` with `to`, `message`, `paths` and a
status of `handoff` or `requested`. Messages never change a task's state.

## Concurrency

Every write fetches the ledger, checks it, creates a commit whose parent is
the fetched revision and pushes it as a fast-forward. If another agent won,
the push is rejected; `ncl` fetches again, re-checks and retries, up to four
times. A new claim is refused when its paths overlap an active claim by
another agent. Overlap is decided on literal path prefixes, so two globs in
the same directory are treated as overlapping; claim narrowly.

## Access

Every participating tool needs fetch and push access to `origin`, and its own
`AGENT_NAME`. The ledger branch never touches the working tree.
