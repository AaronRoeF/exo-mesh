# Every command, and what it gets you

Nothing here reaches the network. Every command below answers from your own disk, so
the numbers are milliseconds and the answers work on a plane.

Two entry points. `exo-mail` is the mail and relationship CLI. The rest are the tools
that build and maintain what it reads. Run `exo-mail --help` for the same list at the
terminal, and `exo-mail <command> --help` for that command's flags. Every command takes
`--json` and prints `{"ok":…, "data":…, "summary":…}`, so you can pipe any of it.

---

## Find things

### `exo-mail search <query>` — find a message by keyword, offline
A [notmuch](https://notmuchmail.org/) query over the whole replica. Full boolean
syntax: `from:`, `to:`, `subject:`, `date:`, `tag:`, `and`, `or`, `not`.

```bash
exo-mail search 'from:jordan@example.com and date:2026..'
exo-mail search 'subject:"renewal" and not tag:exo/feed' --limit 10
```

### `exo-mail semantic <query>` — find it when you remember the gist, not the words
Meaning-based search over local embeddings. No keyword needs to match. Requires
[Ollama](https://ollama.com/) running locally; nothing is sent anywhere.

```bash
exo-mail semantic "the contract argument about data retention"
exo-mail semantic "who was worried about the migration" --since 2026-01-01
```

### `exo-mail count <query>` — how many, without listing them
The same query language as `search`, returning a number. Useful in scripts and for
sizing a cleanup before you start it.

### `exo-mail thread <id>` — read a whole conversation as markdown
Takes a thread id from `search` or `box` output and prints the entire exchange,
quoted replies collapsed, ready to paste into anything.

---

## Work the pile

### `exo-mail box <name>` — read one slice instead of the whole inbox
Five boxes, each a saved query rather than a folder: `imbox` (people writing to you),
`feed` (newsletters), `fins` (receipts and statements), `paper-trail` (things you will
want as evidence later), `reply-later`.

```bash
exo-mail box imbox --limit 20
exo-mail box feed --account personal
```

### `exo-mail tag <target>` — move something into a box, and make it stick
Tags are the data structure; boxes are queries over them. Tagging a sender applies to
their future mail too, so the pile stays sorted without you sorting it again.

### `exo-mail brief` — what needs you today, in one read
The mail that actually wants a reply, what is drifting, and what is on the calendar —
assembled from the local stores rather than five open tabs.

---

## Know where a relationship stands

### `exo-mail contact show <person>` — one person, all four channels
The whole relationship in one record: last email, last text, meetings shared, who
usually starts it, how long it has run, and which addresses and numbers are the same
human.

```bash
exo-mail contact show "Jordan Rivera"
exo-mail contact list --limit 40
exo-mail contact search rivera
```

### `exo-mail contact drift --days 120` — who you are losing
Two-way relationships that have gone quiet across *every* channel, not the
email-shaped shadow of it. No false alarm about someone you saw on Tuesday.

### `exo-mail reconnect <person>` — a warm way back in
A context pack for someone you have drifted from: what you last discussed, what you
said you would do, and which channel is actually alive for them. With `-m` it leaves a
real draft for you to review.

### `exo-mail bedrock` — the relationships that outlived the job that made them
Seven-plus years of span, two-way in at least one channel, still alive in the last
eighteen months. The tool computes those three; whether the relationship survived a
context change is a human call it records rather than guesses. See
[01-CONCEPTS.md](01-CONCEPTS.md).

---

## Write

Read [03-SAFETY.md](03-SAFETY.md) first. **Nothing in this repository sends mail.**
There is no send path to disable — `draft` leaves a draft, and a human presses send.

### `exo-mail reply <thread-id> -m "…"` — reply in-thread with the context already there
### `exo-mail compose --to … --subject … -m "…"` — start a new message
### `exo-mail draft` — leave a real Gmail draft for review

---

## Prove it works

### `exo-mail doctor` — prove the replica is healthy before you rely on it
Message counts, sync freshness, embedding coverage, whether Ollama is up, disk
headroom. Exits non-zero when something is actually wrong, so it belongs in a cron job.

### `exo-mail storage` — where the disk went, per store

---

## Hand it to an agent

### `exo-mail mcp` — the whole thing over MCP, on stdio
Speaks the Model Context Protocol, exposing the read-only tools: search, semantic,
box, thread, contact. Point any MCP client at it and your agent reasons over the whole
relationship instead of one inbox's fragment. See [02-USAGE.md](02-USAGE.md).

### `exo-mail skill` — the machine-readable capability surface
What this install can do, as JSON, for an agent deciding whether to call it.

---

## The day, the calendar, the texts

### `exo-mesh` — the front door to the mesh
The local-first join over mail, contacts, calendar and todos.

### `exo-day` — the whole day in one read
Today's meetings, task counts, the mail that needs a reply, and whether you have
written a journal note yet.

### `exo-cal pull-all` — refresh the local calendar replica
### `exo-imsg snapshot` — take a read-only snapshot of the iMessage database
### `exo-imsg-search <phrase>` — find the text you half-remember from three years ago

---

## Keep it fresh (usually on a timer, rarely by hand)

`exo-mail-sync.sh` runs the whole chain; see [00-INSTALL.md](00-INSTALL.md) for
scheduling it. The steps it calls, if you ever need one alone:

| Command | What it keeps true |
|---|---|
| `exo-gmi` | pulls new mail into the Maildir (a thin wrapper over lieer) |
| `exo-mail-index` | keeps semantic search able to find recent mail |
| `exo-mail-classify` | files new mail into boxes so the pile stays sorted |
| `exo-mail-needsreply` | marks what is waiting on you |
| `exo-mail-contacts` | rebuilds the per-address stats the mesh reads |
| `exo-mail-contacts-merge` | merges your contact sources into one master record |
| `exo-mesh-resolve` | re-resolves one person out of many addresses and numbers |
| `exo-mesh-suppress-sweep` | stops drift nagging about people who left rather than went quiet |
| `exo-mail-commitments` | extracts what you told people you would do |
| `exo-mail-filter` | applies your persistent per-sender rules |
| `exo-mail-ensure-labels` | makes sure the box labels exist in every account |
| `exo-mail-label-backfill` | pushes local box tags up as labels so your phone agrees |
| `exo-imsg-index` | indexes the iMessage snapshot for search |
| `exo-mail-archdoc` | regenerates the architecture section from the code |

### `exo-mesh-suppress-sweep` — stop being nagged about people who left
Drift should tell you who went **quiet**, not who **left**. This proposes suppressions
from two kinds of evidence: a farewell message that was someone's last word, and a
person file that already says they departed.

```bash
exo-mesh-suppress-sweep              # dry run — prints proposals, writes nothing
exo-mesh-suppress-sweep --apply      # writes them to mesh-suppress.tsv
```

Dry run is the default. Suppression is one line in a text file with a reason and a
date: delete the line and the relationship returns. It only ever silences **work**
addresses — a free-mail address and a phone are never touched, because someone can
leave a job without leaving your life. A designated (bedrock) relationship is never
suppressed automatically.
