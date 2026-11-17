# CFP refresh pipeline

`python scripts/update_calls.py` checks the 240-hour interval since the last fully successful fetch. `--force` bypasses this gate for a manual test. Python 3.12 and the standard library are sufficient.

The GitHub workflow wakes every hour at minute 17; most runs exit without network access. After a failed source fetch it retries at the next hourly run. This is not a strict clock-time SLA: GitHub scheduled jobs may be delayed or dropped. Public repository schedules can be disabled after 60 days without repository activity; successful refresh commits normally provide activity, but a long-term failure requires maintenance.

Sources are JournalCompass reposted CFP listings, NOT verified publisher pages. The current publisher endpoints return unavailable pages in this environment. Never interpret HTTP 200 alone as successful retrieval. Each row keeps a publisher URL and source-verification label.

A missing/empty/changed source is treated as failure, not a claim that there are no calls. Existing records are preserved. A call omitted from a successfully retrieved listing gets `source_status=not_listed_unconfirmed`, not closed. Deadlines that differ from existing records are stored separately in `reported_deadline`, with `deadline_conflict=true`; the old date and note stay intact. Historical records are never automatically deleted.

`refresh.last_attempt_at` updates after an actual retrieval attempt. `refresh.last_success_at` and top-level `checked_at` update only if all six sources pass. This is secondary-source collection success, not official verification. Partial failure status and per-source errors are persisted and the job exits nonzero.

The workflow commits `data.json`, including failure metadata. It deliberately does NOT enable GitHub Pages or claim a deployment. A commit pushed with GITHUB_TOKEN does not automatically trigger a Pages branch build. For Pages, add an explicit configure/upload/deploy sequence with `pages:write` and `id-token:write` after the repository's Pages setting is enabled. Alternatively, the already-published Site can read the public repository's raw `data.json`, keeping its existing URL and avoiding runtime secrets.

Before publishing, inspect that the repository contains only these public CFP facts and code. Do not include Site service tokens, HMAC keys, signed update headers, private gateway configuration, or other user documents.

Local verification performed: 9 unit tests passed; live refresh retrieved all six lists and 15 records; immediate second run reported `Not due` and made no update. No GitHub write, workflow run or Pages deployment has been executed by this subagent.
