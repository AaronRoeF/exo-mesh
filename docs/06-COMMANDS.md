# Every command, and why you would run it

Each heading below is the reason, not the name. Find the problem you have; the command
is underneath it.

Nothing here touches the network. Every answer comes off your own disk, which is why
the numbers are milliseconds and why all of it works on a plane. Every command takes
`--json` and prints `{"ok":…, "data":…, "summary":…}`, so anything you can read, you can
pipe. `exo-mail <command> --help` has the flags.

---

## When you know it exists and cannot find it

### You know you got that email — `exo-mail search`
You remember the sender, or a phrase, or roughly when. Search your entire archive with
full boolean syntax, offline, faster than a web page loads. By default it searches mail
**and** texts together, merged by time and listed newest first, keeping the newest
`--limit` matches across both; a notmuch field query (`from:`, `tag:`, …) answers from
mail alone, since that syntax means nothing to the text index. `--channel mail` stays the
original mail-only shape, newest first as it always was; `--channel texts` searches only
the recovered iMessage text, also newest first, including text that lives only in the
packed body. Text results carry `content_trust: "untrusted"`. `--account` narrows mail
only: texts belong to no account, so an account-narrowed search answers from that
account's mail and names texts as skipped. A text index that cannot be read never stops
the mail side either: texts are named as skipped, with `exo-imsg-search --build` as the
repair (under `--channel texts` it is a not-found error with the same hint).

```bash
exo-mail search 'from:jordan@example.com and date:2026..'
exo-mail search 'subject:"renewal" and not tag:exo/feed' --limit 10
exo-mail search "let's do lunch" --channel texts
```

### You remember the argument, not the words — `exo-mail semantic`
Someone pushed back on data retention two years ago and you cannot recall a single term
they used. Meaning-based search finds it with no keyword in common. Runs on local
embeddings via [Ollama](https://ollama.com/); nothing is sent anywhere.

```bash
exo-mail semantic "the contract argument about data retention"
exo-mail semantic "who was worried about the migration" --since 2026-01-01
```

### You want to know how big the job is before you start it — `exo-mail count`
Same query language, returns a number. Size a cleanup, or a migration, or an argument,
before committing an afternoon to it.

### You need the whole exchange, not a fragment — `exo-mail thread`
Takes a thread id and prints the entire conversation as markdown, quoted replies
collapsed. Paste it into a brief, a doc, or a prompt without reconstructing it by hand.

---

## When the inbox is twenty-five thousand things and twenty of them matter

### You are reading newsletters in the same place as people — `exo-mail box`
Five boxes, each a saved query rather than a folder, so nothing is ever moved or lost:
`imbox` (humans writing to you), `feed` (newsletters), `fins` (receipts and statements),
`paper-trail` (what you will want as evidence later), `reply-later`.

```bash
exo-mail box imbox --limit 20
exo-mail box feed --account personal
```

### You are sorting the same sender for the tenth time — `exo-mail tag`
Tag a sender once and their future mail sorts itself. Tags are the data structure;
boxes are queries over them. The pile stays sorted without you sorting it again.

### You want to open one thing in the morning, not five — `exo-mail brief`
What actually needs you today: the mail waiting on a reply, who is drifting, what is on
the calendar. One read across the local stores.

---

## Before you talk to someone

### You are about to say "it's been forever" to someone you texted Tuesday — `exo-mail contact show`
One person, all four channels: last email, last text, meetings you shared, who usually
starts it, how long it has run, and which addresses and numbers are the same human.
Walk in knowing where you actually stand.

```bash
exo-mail contact show "Jordan Rivera"
exo-mail contact list --limit 40
exo-mail contact search rivera
```

### You want the messages themselves, not just the summary — `exo-mesh conversation`
One person's mail and texts merged into a single timeline, oldest to newest, each item
carrying its channel and direction. Windowed by `--since`/`--until` (default: the 90 days
up to their newest item), capped by `--limit`. Message text is real content pulled off
your disk — the envelope marks it `content_trust: "untrusted"` so a caller knows to treat
it as the other person's words, not a verified fact.

```bash
exo-mesh conversation "Jordan Rivera"
exo-mesh conversation "+15551234567" --since 30d --channels texts
```

### You want the pattern, not the messages — `exo-mesh relationship`
The same cross-channel history as `conversation`, reduced to numbers: sent and received
per channel, who usually breaks a silence, the longest run of consecutive days in touch,
the longest gaps, unanswered follow-ups, a heatmap of when you talk, and — for texts —
standing tapback reactions and how long they take to read you. No message text leaves the
machine; the envelope is `content_trust: "derived"`.

```bash
exo-mesh relationship "Jordan Rivera"
exo-mesh relationship "Jordan Rivera" --since 52w --gap 12 --tz America/New_York
```

### You want to find out you are losing someone while you can still do something — `exo-mail contact drift`
Two-way relationships gone quiet across *every* channel, not the email-shaped shadow of
it. No false alarm about the person you saw on Tuesday, and no silence about the one you
have not spoken to in a year.

```bash
exo-mail contact drift --days 120
```

### You have been avoiding a message because you cannot remember where you left off — `exo-mail reconnect`
A context pack for someone you have drifted from: what you last discussed, what you said
you would do, and which channel is actually alive for them. With `-m` it leaves a real
draft for you to review.

### You need to reach someone and have no relationship with them — `exo-mail intro`
Who do you already know who knows them. Two kinds of evidence, both already on your disk:
every calendar event you both attended (strong — you were in a room together on purpose)
and every message you were both named on (weaker — a long Cc list is not a relationship).
Ranked by your own side of it, because a connector you have never replied to is not a
warm path.

```bash
exo-mail intro "acme.example"        # a whole company
exo-mail intro "Priya Shah"          # one person
exo-mail intro "priya@example.com" --min-edges 3
```

Every row shows the counts that produced its score — meetings together, threads together,
when you last spoke to the connector — so you can overrule the arithmetic. A connector you
already share an upcoming meeting with is called out separately: you may not need an
introduction at all.

### You want to know which relationships to protect when a job ends — `exo-mail bedrock`
Seven-plus years of span, two-way in at least one channel, still alive in the last
eighteen months. The tool computes those three; whether a relationship survived a change
of context is a human call it records rather than guesses. See
[01-CONCEPTS.md](01-CONCEPTS.md).

---

## When you need to reply

Read [03-SAFETY.md](03-SAFETY.md) first. **Nothing in this repository sends mail.** There
is no send path to disable — `draft` leaves a draft, and a human presses send.

### You should not have to go hunting for what you promised them — `exo-mail reply`
Replies in-thread with the context already assembled: the last exchange, and the
commitments you made in your own sent mail.

### You want to write without leaving the terminal — `exo-mail compose`, `exo-mail draft`
`compose` starts a new message; `draft` leaves a real Gmail draft for you to review on
any device before sending.

---

## Before you trust what it tells you

### You are about to make a decision on this data — `exo-mail doctor`
Message counts, sync freshness, embedding coverage, whether the model server is up, disk
headroom. Exits non-zero when something is actually wrong, so it belongs in a cron job
and not in your memory.

### Your disk is filling and you do not know what is eating it — `exo-mail storage`
Per-store breakdown, so you delete the right thing.

---

## When an agent should stop guessing about your life

### Your agent knows nothing about your relationships — `exo-mail mcp`
Speaks the Model Context Protocol on stdio, exposing the read-only tools: search,
semantic, box, thread, contact. Point any MCP client at it and every agent, skill and
draft you build reasons over the whole relationship instead of one inbox's fragment —
from a file on your disk, under a retention policy you wrote yourself.

### An agent needs to decide whether calling this is worth it — `exo-mail skill`
The capability surface as JSON: what this particular install can actually do.

---

## Your whole day, without five tabs

### You want the day in one read — `exo-day`
Today's meetings, task counts, the mail that needs a reply, and whether you have written
a journal note yet.

### You want the mesh itself — `exo-mesh`
The front door: the local-first join over mail, contacts, calendar and todos.

### You are about to have an agent research what a query already knows — `exo-mesh since`
`exo-mesh-since` is the window: who you interacted with since `--since` (one row per
person, per-channel counts, a class that tells newsletters from humans), the meetings
inside `--horizon` with attendees already resolved to identities, and the enrichment
diff between what the mesh observed and what your person files claim. Deterministic,
offline, read-only — it proposes, and never writes.

```sh
exo-mesh since --since 26h --include diff        # the cheap daily pass
exo-mesh since --include meetings --horizon 3d   # who is in the room, resolved
```

### You want calendar answers with the network off — `exo-cal pull-all`
Refreshes the local calendar replica from Apple and both Google accounts, skipping any
that are not authorised.

### You want a text you half-remember from three years ago — `exo-imsg-search`
Builds and refreshes the text index `exo-mail search`'s texts side reads. `exo-imsg
snapshot` takes the read-only copy it indexes; `--refresh` then indexes only messages
newer than the last run's cursor (by row id) -- a message edited in place keeps its old
indexed words until the next `--build`, and the very first run is always a full build.
`--build` rebuilds the index from scratch. Reactions (tapbacks) are never indexed as
searchable text.

---

## Keeping it true without thinking about it

`exo-mail-sync.sh` runs the whole chain on a timer; [00-INSTALL.md](00-INSTALL.md) has
the scheduling. You would only run one of these alone to debug it.

| Command | What breaks if it stops |
|---|---|
| `exo-gmi` | new mail never arrives; everything below goes stale |
| `exo-mail-index` | semantic search cannot find anything recent |
| `exo-mail-classify` | new mail lands unsorted and the boxes stop being useful |
| `exo-mail-needsreply` | you stop being told what is waiting on you |
| `exo-mail-contacts` | relationship stats freeze at yesterday |
| `exo-mail-contacts-merge` | one person starts looking like three again |
| `exo-mesh-resolve` | addresses and numbers stop resolving to one human |
| `exo-mesh-suppress-sweep` | drift keeps nagging about people who already left |
| `exo-mail-commitments` | drafts stop knowing what you promised |
| `exo-mail-filter` | your per-sender rules stop applying to new mail |
| `exo-mail-ensure-labels` | box labels go missing in one account and your phone disagrees |
| `exo-mail-label-backfill` | local sorting never reaches Gmail |
| `exo-imsg-index` | iMessage search goes stale |
| `exo-mail-archdoc` | the architecture doc drifts from the code |

### You are being nagged about someone who already left — `exo-mesh-suppress-sweep`
Drift should tell you who went **quiet**, not who **left**. This proposes suppressions
from two kinds of evidence: a farewell message that was genuinely someone's last word,
and a person file that already records their departure.

```bash
exo-mesh-suppress-sweep              # dry run — prints proposals, writes nothing
exo-mesh-suppress-sweep --apply      # writes them
```

Dry run is the default. A suppression is one line in a text file with a reason and a
date: delete the line and the relationship returns. It only ever silences **work**
addresses — a free-mail address and a phone are never touched, because someone can leave
a job without leaving your life. A designated (bedrock) relationship is never suppressed
automatically.
