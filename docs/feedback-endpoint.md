# Feedback endpoint contract

`ncl feedback` and the installer's one-time prompt POST to
`https://www.claude-repo.com/api/never-collide/feedback` (override with
`NCL_FEEDBACK_URL`).

**Status (2026-09-27):** built and deployed, as `api/never-collide/feedback.js`
in the claude-repo.com site repo. Store: one GitHub issue per message in the
private repo `malaysherasia-ai/never-collide-feedback`, labelled `count` or
`feedback`. Until the site's `FEEDBACK_TOKEN` environment variable is set on
Vercel (a fine-grained token with Issues read/write on that repo), the
endpoint answers `503 {"error": "feedback store not configured"}` and `ncl`
shows that line to the person. `scripts/feedback-check.mjs` in the site repo
exercises every branch below against a stub GitHub.

## Request

`POST`, `Content-Type: application/json`, `User-Agent: never-collide/<version>`.

```json
{
  "project": "never-collide",
  "event": "count",
  "version": "0.4.0",
  "os": "Windows",
  "python": "3.11.9",
  "ts": "2026-09-27T14:02:11Z"
}
```

`event` is `count` (anonymous, the fields above only) or `feedback`, which
may add any of `name`, `email`, `tools` and `message`, all strings the person
typed and confirmed. Nothing else is ever sent: no hostname, no repo name,
no paths, no ledger content.

## Response

`200` with any small JSON body (`{"ok": true}`). `ncl` prints the status and
the first 200 bytes. Any non-2xx or a timeout is reported to the person as
"could not send feedback"; nothing is retried.

## Site side (Vercel serverless function, as built)

- Function: `api/never-collide/feedback.js` in the site repo, `POST` only
  (`405` otherwise). The site is static HTML plus Vercel functions; there
  is no framework and no database.
- Validate: `project === "never-collide"`, `event` in the two values, every
  string at most 2000 characters, body at most 16 KB (`413`). Anything else
  is `400` with a one-line reason. A `count` event drops the personal
  fields even if sent.
- Store: one issue per message in the private GitHub repo, title
  `[event] name: first words · version · os`, body the cleaned JSON in a
  fenced block, label `count` or `feedback`. Replies to an `email` happen
  from the issue by hand; no mail service is involved.
- Rate limit: six messages per minute per address, instance-local, `429`
  beyond that. The address is written into the issue body and nowhere else.
- Numbers for the site's Numbers section: search the private repo for
  `label:count` and `label:feedback`, grouped by version and OS from the
  titles, alongside the GitHub clone counter that needs no client at all.
- No auth, no CORS (the client is `ncl`, not a browser). `FEEDBACK_REPO`
  and `FEEDBACK_API` override the repo and the API base for tests.

## Privacy line for the docs

Usage is counted from GitHub clone statistics. `ncl` sends nothing on its
own; the installer asks once per machine and Enter skips it. `ncl feedback`
shows the exact payload and sends only on a yes. `ncl upgrade` is the one
other network call, to GitHub's release API, and only when run.
