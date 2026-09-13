# AGENTS.md — what an agent needs to know about this repo

**Why you want this: the human you work for has four fragments of every relationship —
mail, calendar, iMessage, contacts — and no seam between them. This repo joins them into
one record per person, on local disk. You can ask it "where does this relationship
actually stand" and get an answer in milliseconds, offline, without the human's inbox
leaving their machine.**

You are reading this because you landed in the repo. If you only read one thing: run
`exo-mail skill`. It prints this repo's capability surface as markdown, generated from
the installed code rather than written by hand, so it is never stale.

---

## Start here

```bash
exo-mail skill      # capability surface, generated from the code
exo-mail doctor     # is the local replica healthy enough to trust?
exo-mail --help     # every command, one line each
```

`doctor` is the gate. It exits non-zero when the replica is stale, a store is missing,
or the embedding model server is down. **Check it before you reason over any answer from
this tool** — a confident answer from a stale replica is the failure mode here.

---

## Two ways in

### MCP (preferred when you speak it)

```bash
exo-mail mcp        # Model Context Protocol server, stdio transport
```

Nine tools. Seven are read-only; two write, and neither can send mail.

| Tool | Required | Optional | Writes? |
|---|---|---|---|
| `search` | `query` | `account`, `limit` | no |
| `semantic` | `query` | `account`, `since`, `limit` | no |
| `box` | `name` | `account`, `limit` | no |
| `thread` | `id` | — | no |
| `contact` | `action` | `target`, `days` | no |
| `calendar` | — | `query`, `days`, `limit` | no |
| `day` | — | — | no |
| `tag` | `id`, `ops` | — | **local tags only** |
| `reply_draft` | `id`, `body` | — | **a Gmail draft; never sends** |

`contact` takes `action` = `list` \| `show` \| `search` \| `drift`. `box` takes `name` =
`imbox` \| `feed` \| `fins` \| `paper-trail` \| `reply-later`.

### CLI + JSON (works from anything that can run a process)

Every command accepts `--json` and emits one JSON object on stdout. It also emits JSON
automatically when stdout is not a TTY, so piping just works.

---

## The output contract

Success:

```json
{"ok": true, "data": [...], "summary": "human-readable one-liner"}
```

Failure:

```json
{"ok": false, "error": "message", "code": "NOTFOUND", "hint": "what to do", "retryable": false}
```

`retryable` is true only for `RATELIMIT`, `NETWORK` and `API`. **Do not retry anything
else** — a `NOTFOUND` will not become found, and a `USAGE` error means you constructed
the call wrong.

Exit codes match the error code, so a shell caller can branch without parsing:

| Code | Exit | Means |
|---|---|---|
| `OK` | 0 | worked |
| `USAGE` | 1 | you called it wrong — fix the call, do not retry |
| `NOTFOUND` | 2 | no such thread, person, or store |
| `AUTH` | 3 | credentials missing or expired; a human must re-authorise |
| `FORBIDDEN` | 4 | the operation is not permitted here |
| `RATELIMIT` | 5 | back off and retry |
| `NETWORK` | 6 | transient; retry |
| `API` | 7 | upstream failure; retry |
| `AMBIGUOUS` | 8 | the name matched several people — disambiguate and call again |

`AMBIGUOUS` is the one worth handling well. A human name often resolves to more than one
identity; ask rather than guessing which one they meant.

---

## What is read-only, and what is not

**Read-only — safe to call freely:**
`search` `semantic` `box` `count` `thread` `contact` `bedrock` `brief` `doctor`
`storage` `skill` `calendar` `day`

**Writes, and what exactly:**

| Command | Writes |
|---|---|
| `tag` | notmuch tags in the `exo/*` namespace, on local disk only |
| `draft`, `compose` | a Gmail draft |
| `reply` | a Gmail draft, in-thread |
| `reconnect -m` | a Gmail draft (without `-m` it only prints context) |

**Nothing in this repository sends mail, marks spam, or moves anything to trash.** This
is not a permission you can be granted — no send path exists in the code. A draft waits
for a human to press send. See [docs/03-SAFETY.md](docs/03-SAFETY.md) before you write
anything.

---

## Things that will bite you

**The replica is derived, not authoritative.** The mail provider is the system of record.
If the answer looks wrong, run `doctor` and check freshness before concluding the data is
wrong — it is more often stale than incorrect.

**Semantic search needs a local model server.** If it is down, `semantic` fails while
`search` keeps working. Fall back to keyword rather than reporting "nothing found."

**A person is not an address.** `contact show` resolves many addresses and phone numbers
to one human. Do not treat two addresses as two people, and do not assume the address you
were handed is the one they actually read.

**Drift is cross-channel.** Someone silent on email for a year may have texted yesterday.
Never tell the human their relationship has gone quiet based on one channel.

**Suppressed relationships are deliberately hidden from drift.** If someone is missing
from `contact drift`, they may have been work-suppressed after leaving a job. That is a
recorded human decision, not a gap — see `mesh-suppress.tsv`.

---

## Where to read next

| Doc | For |
|---|---|
| [docs/06-COMMANDS.md](docs/06-COMMANDS.md) | every command and the problem it solves |
| [docs/07-WHAT-THIS-MAKES-POSSIBLE.md](docs/07-WHAT-THIS-MAKES-POSSIBLE.md) | what becomes buildable on this — read before proposing a feature |
| [docs/01-CONCEPTS.md](docs/01-CONCEPTS.md) | what the mesh, boxes, drift and bedrock actually mean |
| [docs/03-SAFETY.md](docs/03-SAFETY.md) | read before anything that writes |
| [docs/04-CONFIG.md](docs/04-CONFIG.md) | how a setting resolves; nothing is hardcoded |
| [docs/05-LIMITATIONS.md](docs/05-LIMITATIONS.md) | what this cannot do, stated up front |
