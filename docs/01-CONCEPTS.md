# 01 — Concepts

What the pieces are, and why they are shaped this way.

---

## Local-first, and why it matters here

Every answer is composed from a replica on your disk. No rate limit sits on the query
path, so a program can ask a thousand questions about your relationship graph in the
time one API call would take, and it can ask them on a plane.

The replica is boring on purpose:

| Layer | What it is |
|---|---|
| Mail | a Maildir per account, synced by [lieer](https://github.com/gauteh/lieer), indexed by [notmuch](https://notmuchmail.org/) |
| Calendar | `calendar.db` — SQLite, one row per event, from Apple Calendar and Google |
| iMessage | `imessage/snapshot.db` — a read-only copy of `chat.db`, plus an FTS5 index |
| Contacts | `contacts-master.db` — Apple Contacts and Google People merged into one record per person |
| Mesh | `mesh.db` — the join of all four |
| Semantic | `vectors.db` — sqlite-vec, embeddings computed locally by Ollama |

They all live in the **store** (default `~/Mail/exo`). Every one of them is
derivable: delete any `.db` and the tool that owns it rebuilds it. The only files in
the store that are *not* reproducible are the ones you wrote by hand —
`sender-rules.tsv`, `mesh-suppress.tsv` — which is why the sync can copy those, and
only those, to a backup directory.

---

## The four channels

A relationship does not live in one place. It lives in whichever medium is
convenient, which changes over the years, which is exactly what makes a single-inbox
view lie to you.

exo-mail reads four:

1. **Email** — counts sent and received, first and last contact, per address.
2. **iMessage/SMS** — the same, per handle, over one-to-one chats.
3. **Calendar** — shared meetings, as a recency and investment signal.
4. **Contacts** — not a channel of its own, but the *spine*: the record that says
   this address and that phone number are the same human.

---

## Identity resolution

The hard part is (4). Without it you have four strangers.

`exo-mail-contacts-merge` builds the spine. It links contact records that share a
real email address or a real phone number (compared on the last ten digits), with two
guards that exist because the naive version is wrong:

- **A shared line does not link people.** A key that touches more than four distinct
  names is an office line or a shared inbox, and linking on it would merge a company
  into one person.
- **A name alone never links.** Too many collisions.

`exo-mesh-resolve` then joins the spine to the three channels and writes one row per
person into `mesh.db`: every address and phone they own, per-channel counts, first
and last contact per channel, a unified `last_contact` across all of them, the span
of the relationship in years, and which channels are live.

Two details that are easy to get wrong and are handled explicitly:

- iMessage counterparties are resolved through `chat_handle_join` (a one-to-one chat
  has exactly one participant) joined to `chat_message_join`. Joining `message` to
  `handle` directly looks correct and silently drops about 45% of the data, because
  messages you *sent* carry `handle_id = 0`.
- Apple timestamps are nanoseconds since 2001-01-01, not seconds since 1970.

Everything downstream — drift, reconnect, the draft context block, BEDROCK — reads
`mesh.db`. When it is missing, each of them falls back to the email-only path rather
than failing.

---

## Boxes

Mail is bucketed into `exo/*` notmuch tags, which are pushed up as matching Gmail
labels so both views agree:

| Box | What lands there |
|---|---|
| `imbox` | real correspondence — the inbox minus everything below |
| `feed` | newsletters and bulk mail |
| `fins` | financial, investment, tax |
| `updates` | notifications from machines |
| `paper-trail` | receipts, confirmations |
| `vip` | people you have marked |
| `needs-reply` | set by `exo-mail-needsreply` |
| `reply-later` | set by you |

Classification is rules-before-heuristics: `sender-rules.tsv` is consulted first, and
an allow rule forces a bucket while a deny rule forbids one. The heuristics only run
where you have not expressed an opinion. `exo-mail-filter add <sender> <bucket>` is
how you express one, and it retro-applies to existing mail.

The bucketing is idempotent and marked with `exo/classified`, so a re-run is free.

---

## Drift

"Who have I gone quiet with?" — but honestly.

`exo-mail contact drift --days 120` reports relationships that are two-way in at
least one channel and whose *cross-channel* `last_contact` is older than the window.
Someone you email rarely but text weekly is not drifting, and the single-inbox
version of this query would have told you they were.

A `mesh-suppress.tsv` in the store removes people from the proactive surfaces without
deleting the relationship: one row per key (an address or a ten-digit phone number),
with a scope. Scope `drift` hides them from drift; scope `all` hides them everywhere.
This is how a departed colleague, or a relationship you deliberately ended, stops
being suggested to you.

---

## BEDROCK

Drift asks who is fading. BEDROCK asks the opposite and more interesting question:
**which relationships outlived the context that created them?**

The job you shared, the city you both left, the company that no longer exists — most
relationships are downstream of a context, and end with it. The ones that don't are a
different category, and they are worth being deliberate about.

Four criteria. The tool computes three:

1. **Span ≥ 7 years** between first and last contact, across all channels.
2. **Two-way** in at least one channel — a mailing list is not a relationship.
3. **Still alive** — contact within the last 18 months.

The fourth is **did it survive a context change?**, and it is deliberately *not*
computed. A machine cannot tell "we still talk because we still work together" from
"we still talk although nothing makes us." So:

```sh
exo-mail bedrock candidates          # read-only: the review list, writes nothing
exo-mail bedrock candidates --min-span 10 --alive-months 6
```

emits candidates and stops. If you keep person files, you confirm the fourth
criterion yourself in a TSV and `exo-mesh-bedrock-apply` records your call as
`bedrock: true` in the person file (dry-run by default; `--apply` writes). See
[03-SAFETY.md](03-SAFETY.md).

One deliberate asymmetry: a `status:` of departed or terminated *hides* someone from
drift, but is *shown, not filtered* in BEDROCK. For drift a departure is noise. For
BEDROCK it is supporting evidence — the context ended and the relationship did not.

---

## Person files (optional)

Point `EXO_MAIL_PEOPLE` at a directory of markdown files, one per person, named
`first-last.md`, with the person's own addresses in the YAML frontmatter:

```markdown
---
name: Jordan Rivera
emails: [jordan@acmerobotics.example.com, jordan.rivera@example.com]
status: active
---
```

Then every mesh row carries a `person_file` link, `exo-mail contact show` points at
it, the draft context block reminds you to open it before replying, and
`exo-mesh-bedrock-apply` has somewhere to record a designation.

Only the frontmatter is scanned, and only for the person's *own* addresses — prose in
the body is ignored, so quoting someone else's address in your notes does not
misattribute them.

Unset the variable and all of this is simply skipped. Nothing requires it.

---

## The output contract

Every `exo-mail` command prints a JSON envelope when piped or given `--json`:

```json
{"ok": true, "data": ..., "summary": "18 threads"}
{"ok": false, "error": "...", "code": "NOTFOUND", "hint": "...", "retryable": false}
```

with typed exit codes — 0 OK, 1 Usage, 2 NotFound, 3 Auth, 4 Forbidden,
5 RateLimit, 6 Network, 7 API, 8 Ambiguous. On a terminal it prints a table instead.

That contract is the point: it is what makes the whole surface safe to hand to a
program. `exo-mail mcp` serves the read-only subset over stdio JSON-RPC as an MCP
server for exactly that reason.
