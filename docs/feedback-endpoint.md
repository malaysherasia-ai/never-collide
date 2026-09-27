# Feedback endpoint contract

`ncl feedback` and the installer's one-time prompt POST to
`https://www.claude-repo.com/api/never-collide/feedback` (override with
`NCL_FEEDBACK_URL`). The endpoint does not exist yet; this is what the site
must implement so the counts and messages land somewhere.

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

## Site side (Next.js route on Vercel)

- Route: `app/api/never-collide/feedback/route.ts`, `POST` only.
- Validate: `project === "never-collide"`, `event` in the two values,
  each string at most 2000 characters, body at most 16 KB. Reject anything
  else with `400`.
- Store: a table with the raw JSON, the `event`, the received time and
  nothing derived from the request beyond that. Vercel Postgres or KV both
  fit. For `feedback` events with an `email`, also forward the message by
  email (Resend) so a reply can happen.
- Rate limit by IP (a handful per minute) and do not log IPs beyond that.
- Numbers for the site's Numbers section: `count` plus `feedback` events
  grouped by version and OS, alongside the GitHub clone counter that needs
  no client at all.
- No auth, no CORS (the client is `ncl`, not a browser).

## Privacy line for the docs

Usage is counted from GitHub clone statistics. `ncl` sends nothing on its
own; the installer asks once per machine and Enter skips it. `ncl feedback`
shows the exact payload and sends only on a yes. `ncl upgrade` is the one
other network call, to GitHub's release API, and only when run.
