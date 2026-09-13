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
full boolean syntax, offline, faster than a web page loads.

```bash
exo-mail search 'from:jordan@example.com and date:2026..'
exo-mail search 'subject:"renewal" and not tag:exo/feed' --limit 10
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

### You want calendar answers with the network off — `exo-cal pull-all`
Refreshes the local calendar replica from Apple and both Google accounts, skipping any
that are not authorised.

### You want a text you half-remember from three years ago — `exo-imsg-search`
Exact-phrase search over the local iMessage snapshot. `exo-imsg snapshot` takes the
read-only copy it searches.

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
