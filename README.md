# exo-mesh

**Walk into every conversation with the whole relationship in front of you — not
the fragment one inbox remembers. Mail, calendar, iMessage and contacts, joined on
your own disk into one record per person.**

Four systems hold four fragments of the same relationship, and there's no seam
between them. So the question you actually have — *when did I last talk to Priya, and
about what?* — costs four searches and a guess. What are our open items? Where did we leave off? 

exo-mesh answers it in one local read. It mirrors your Gmail to a
[notmuch](https://notmuchmail.org/)-indexed Maildir, pulls your calendars, takes a
read-only snapshot of iMessage, merges your contacts, and resolves the whole pile
into a **mesh**: one row per person, carrying every address and number they own,
per-channel recency, who usually starts the conversation, and how many years it has
run.

Everything stays on your disk. No service, no daemon, no API key on the query path.
Your relationship history is the most revealing corpus you own, and this is the copy
that answers in single-digit milliseconds without renting it to anyone.

And it is the store an agent can read. `exo-mail mcp` speaks MCP, so every agent,
skill and draft you build reasons over the whole relationship instead of one inbox's
fragment — from a file on your disk, under a retention policy you wrote yourself. It
runs against a six-figure message archive, not a demo fixture.

Four channels. One person. Zero egress.

![Four channels in, one person out: mail, calendar, iMessage and contacts are pulled
into local replicas, resolved by email, phone and name into a mesh holding one row per
person, which the CLI and MCP server read — nothing leaves the machine.](assets/exo-mesh.svg)

---

## What you get

**Total recall before a conversation.** `exo-mail contact show "Jordan Rivera"`
assembles every channel at once: the last thread, the last text, meetings you have
shared, who tends to start them, how the relationship has trended.

**Messages that match reality.** Draft a reply and it comes with a context block —
what you last discussed, and the things you *told them you would do*, extracted from
your own sent mail. You stop opening with "it's been ages!" to someone you texted
yesterday.

**Reach out where the relationship lives.** The mesh knows your warmest channel with
each person. Formal email can be stone cold while you text every week.
`exo-mail reconnect "Priya Shah"` points at the channel that is actually alive.

**One person, not four strangers.** A work address, a personal Gmail and a mobile
number resolve to a single identity, so "who is this?" has one complete answer.

**Get told who you're losing before they're gone.** `exo-mail contact drift
--days 120` reports who has gone quiet across *every* channel — not the
email-shaped shadow of it. No false alarm about someone you saw on Tuesday.

**Know which relationships outlived the job that made them.** BEDROCK: seven-plus
years of span, two-way in at least one channel, still alive in the last eighteen
months. The tool computes those three; the fourth — *did it survive a context
change?* — is a human call it records rather than guesses. See
[docs/01-CONCEPTS.md](docs/01-CONCEPTS.md).

**Find it whether you remember the words or only the gist.** `exo-mail search`
for a notmuch query, `exo-mail semantic` for meaning (local embeddings via
[Ollama](https://ollama.com/) — nothing is sent anywhere), and `exo-imsg-search`
for an exact phrase you remember from a text three years ago.

**Open one thing in the morning instead of five.** `exo-mesh` composes today's
meetings, your task counts, the mail that needs a reply, and whether you've written a
journal note yet — one read across the local stores.

---

## Why you can point this at your real mailbox

**No tool in this repository sends mail, marks spam, or moves anything to trash.**
Not the CLI, not the MCP server. There is no flag for it. The only outbound verb is
*save a Gmail draft* — including the reply lane — and a human presses Send in Gmail.

Everything the tools write is reversible: notmuch tags in the `exo/*` namespace,
the matching Gmail labels, local SQLite databases you can delete and rebuild, and
drafts. Sources are read-only: your iMessage database, Apple Calendar and Apple
Contacts are opened read-only and never written.

Read [docs/03-SAFETY.md](docs/03-SAFETY.md) before you run anything that says
`--apply`. Two tools can create or modify records outside their own store
(`exo-mail-ensure-labels` creates Gmail labels; `exo-mesh-bedrock-apply` writes
markdown person files), and both are documented there with their gates.

---

## Install

macOS, Python 3.11+, and roughly: `brew install notmuch`, a lieer checkout per
account, `pip install -r requirements.txt` into a venv, one `notmuch setup`,
`ollama pull nomic-embed-text` if you want semantic search.

The full, tested, line-by-line version — including the Google OAuth steps and the
scheduled sync — is [docs/00-INSTALL.md](docs/00-INSTALL.md). Do that one instead
of this paragraph.

```sh
git clone https://github.com/AaronRoeF/exo-mesh.git
cd exo-mesh
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
./bin/exo-mail-python bin/exomail_config.py     # print what every setting resolved to
```

You almost certainly need no configuration file: your addresses, your name and your
mail root are read from `notmuch config`, which you set up anyway.
[config.env.example](config.env.example) documents every knob for when you do.

---

## Where to go next

| | |
|---|---|
| [00-INSTALL.md](docs/00-INSTALL.md) | Prerequisites, venv, OAuth, first sync, scheduling |
| [01-CONCEPTS.md](docs/01-CONCEPTS.md) | The four channels, identity resolution, BEDROCK |
| [02-USAGE.md](docs/02-USAGE.md) | Every command, grouped by what you are trying to do |
| [03-SAFETY.md](docs/03-SAFETY.md) | What writes, what cannot, and every gate |
| [04-CONFIG.md](docs/04-CONFIG.md) | Every setting, how it resolves, worked example |
| [05-LIMITATIONS.md](docs/05-LIMITATIONS.md) | Where this does not work, honestly |
| [06-COMMANDS.md](docs/06-COMMANDS.md) | Every command and what it gets you — the reference. |
| [07-WHAT-THIS-MAKES-POSSIBLE.md](docs/07-WHAT-THIS-MAKES-POSSIBLE.md) | Seven things a local relationship mesh makes possible — five that work, two that do not exist yet. |
| [AGENTS.md](AGENTS.md) | Reading this as an agent? Start there — MCP tools, JSON contract, exit codes, what writes. |

---

## What will bite you, before you install it

macOS only. Gmail only. Single writer — run the sync on exactly one machine.
Reading iMessage requires granting Full Disk Access, and without it the database
reads **zero rows with no error**, which is why every path asserts a non-empty
result rather than succeeding quietly. Semantic search needs Ollama running
locally. A large mailbox costs real disk. Details and the rest of the list:
[docs/05-LIMITATIONS.md](docs/05-LIMITATIONS.md).

---

## Status and license

Working software that one person runs every day, published because the pattern is
worth copying — not a product, and not something anyone is on call for. Expect to
read the source. Issues and forks welcome; support is not promised.

MIT. See [LICENSE](LICENSE).
