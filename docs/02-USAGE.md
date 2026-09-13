# 02 — Usage

Every shipped command, grouped by what you are trying to do. Paths below assume you
are in the checkout; symlink `bin/exo-mail` onto your `PATH` and drop the `./bin/`.

Global flags on every `exo-mail` subcommand: `--json`, `--account <name>|all`
(default `all`), `--limit N` (default 50).

---

## Reading mail

```sh
exo-mail search "from:jordan@example.com and date:6M.."   # any notmuch query
exo-mail count "tag:inbox and tag:unread"
exo-mail box imbox                                        # imbox feed fins updates
exo-mail box feed --account personal --limit 10           # paper-trail vip
                                                          # needs-reply reply-later
exo-mail thread 0000000000012ab3 --markdown               # quote-stripped
exo-mail semantic "the contract redline thread last spring" --since 1y
```

`search` is exact and structured — it is notmuch, so the
[notmuch-search-terms](https://notmuchmail.org/manpages/notmuch-search-terms-7/)
syntax all works. `semantic` is for when you remember what a message was *about* but
not a word in it; it needs Ollama running and `exo-mail-index` to have run.

For an exact phrase you remember from a *text* rather than an email:

```sh
exo-imsg-search "let's push it to Thursday"
exo-imsg-search -n 30 invoice draft
```

---

## People

```sh
exo-mail contact list                        # top two-way relationships by volume
exo-mail contact show "Jordan Rivera"        # or an address; one whole person
exo-mail contact search acme
exo-mail contact drift --days 120            # quiet across ALL channels
```

`contact show` resolves through the mesh, so it answers for the *person*, not the
address you happened to type: every address and phone they own, per-channel counts
and recency, who tends to initiate, the linked person file if you keep one, and their
recent threads.

```sh
exo-mail bedrock candidates
exo-mail bedrock candidates --min-span 10 --alive-months 6 --json
```

Read-only. See [01-CONCEPTS.md](01-CONCEPTS.md#bedrock) for the four criteria and why
the fourth is yours.

---

## Organising

```sh
exo-mail tag <message-id> +exo/reply-later -unread
exo-mail-filter add news@example.com feed     # allow rule: force bucket, retro-apply
exo-mail-filter remove news@example.com feed  # deny rule: forbid bucket, retro-strip
exo-mail-filter list
```

Tagging is limited to the `exo/*` namespace plus the standard notmuch flags
(`unread`, `flagged`, `inbox`, `replied`, `passed`, `draft`). Anything else is
refused with `FORBIDDEN`, so this command cannot mark mail deleted or spam. Every
`+` has a matching `-`.
`exo-mail-filter` writes `sender-rules.tsv` in the store and then retro-applies the
rule to existing mail, both in notmuch and as the matching Gmail label.

**Always dry-run a filter change first:** `EXO_DRY=1 exo-mail-filter add ...` prints
every notmuch call, every API call and the rule-file write, and performs none of them.

---

## Drafting

```sh
exo-mail reply <thread-id> -m "Sounds good — Thursday works."
exo-mail compose --to jordan@example.com --subject "Follow-up" -m "..." --account work
exo-mail reconnect "Priya Shah"                  # context pack, no draft
exo-mail reconnect "Priya Shah" -m "It has been too long..."   # pack + draft
exo-mail draft list | exo-mail draft show <id> | exo-mail draft delete <id>
```

These create Gmail **drafts**. Nothing sends. `reply` gets the threading right
(`In-Reply-To`, `References`, the Gmail `threadId`) and prefixes `Re:` only when it
is missing.

Every draft opens with a review block that you delete before sending. It names who
you are writing, where the relationship stands across channels, your last few
exchanges, and — the useful part — **things you told them you would do**, extracted
from your own sent mail of the last 200 days. It is a checklist, not prose.

---

## The day

```sh
exo-mesh                 # the whole day, one local read
exo-mesh caps            # what you can do
exo-day --json           # the same, for a program
exo-mail brief           # reply queue + drifting relationships
exo-mail brief --drift-days 180 --json
```

`exo-day` composes the calendar replica, your Things 3 task counts (macOS only; the
section is omitted if Things is not installed), an `exo-mail brief` subprocess, and
whether today's dated note exists under `EXO_MAIL_NOTES`. It only reads.

---

## Calendar

```sh
exo-cal stats                     # what is in the replica
exo-cal pull-apple                # Apple Calendar -> calendar.db
exo-cal auth work                 # one-time Google consent (calendar.readonly)
exo-cal pull-google work
exo-cal pull-all                  # apple + every authed account
```

The window is 730 days back, 365 forward. Upserts are keyed on the event UID, so
re-running is idempotent — the row count does not grow.

---

## iMessage

```sh
exo-imsg snapshot          # WAL-consistent read-only copy + cursor + audit
exo-imsg status            # cursor, counts, freshness
exo-imsg test              # built-in self-checks
exo-imsg-search --build    # (re)build the FTS5 index
exo-imsg-index             # day-window embeddings into the shared vector store
exo-imsg-index --rollback  # delete only the imessage rows from vectors.db
```

Needs Full Disk Access. See [05-LIMITATIONS.md](05-LIMITATIONS.md).

---

## Maintenance

```sh
exo-mail doctor                   # the one to run when something is off
exo-mail storage                  # what is using disk, ranked ways to reclaim it
exo-mail-sync.sh                  # the whole pipeline, by hand
exo-mail-index                    # incremental embed of new mail
exo-mail-contacts                 # rebuild the correspondent index (~2 min)
exo-mail-contacts-merge           # rebuild the contact spine
exo-mesh-resolve                  # rebuild mesh.db
exo-mesh-resolve --test           # same computation, writes nothing
exo-mail-classify                 # bucket new mail (idempotent)
exo-mail-needsreply               # retag the needs-reply queue
exo-mail-archdoc --print          # generate an architecture doc from the live tools
exo-mail-archdoc --check          # diff it against the file on disk; exit 1 if stale
```

Two that write outside their own store, both documented in
[03-SAFETY.md](03-SAFETY.md):

```sh
EXO_DRY=1 exo-mail-ensure-labels  # would-create report; drop EXO_DRY to create
EXO_DRY=1 exo-mail-label-backfill
exo-mesh-bedrock-apply            # dry-run by default
exo-mesh-bedrock-apply --apply    # writes person files
```

---

## As an MCP server

```sh
exo-mail mcp      # stdio JSON-RPC
```

Nine tools, all read-or-draft: `search`, `semantic`, `box`, `thread`, `contact`,
`tag`, `reply_draft`, `day`, `calendar`. Irreversible verbs are not served, because
they do not exist ([03-SAFETY.md](03-SAFETY.md)).

Register it with any MCP client by pointing the command at `bin/exo-mail` with the
argument `mcp`:

```json
{
  "mcpServers": {
    "exo-mail": {
      "command": "<absolute path to your checkout>/bin/exo-mail",
      "args": ["mcp"]
    }
  }
}
```

Print the absolute path with `echo "$PWD/bin/exo-mail"` from the checkout.

`exo-mail skill` prints a compact capability summary written for an agent to read.
