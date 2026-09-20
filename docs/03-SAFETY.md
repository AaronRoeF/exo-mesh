# 03 — Safety

What can write, what cannot, and every gate. Read this before running anything with
`--apply`.

---

## The one-line version

**Nothing here sends mail, marks spam, or trashes anything.** Everything it does
write is reversible, and every write that leaves exo-mail's own store is either
dry-run by default or gated behind an environment variable.

---

## Sending: it is not a gate, it is an absence

There is no send path. Not a flag, not a subcommand, not an MCP tool, not a
"confirm" prompt. `exo-mail reply` and `exo-mail compose` call the Gmail **drafts**
endpoint and stop. A human opens Gmail and presses Send.

The same is true of destructive Gmail verbs: nothing in this repository calls
`messages.trash`, `messages.delete`, or sets `SPAM`. The MCP server
(`exo-mail mcp`) serves ten tools — `search`, `semantic`, `box`, `thread`,
`contact`, `tag`, `reply_draft`, `day`, `calendar`, `since` — and that list is the
whole surface. Every one of them declares its effect class in MCP `annotations`;
only `tag` and `reply_draft` are not read-only.

If you are reading this to decide whether to point an autonomous agent at it: the
worst an agent can do with the full surface is retag your mail, create Gmail labels,
and leave you drafts. Those are all things you can undo.

---

## Sources are read-only

| Source | How it is opened |
|---|---|
| `~/Library/Messages/chat.db` | read-only URI, copied to a snapshot; never written |
| Apple Calendar SQLite | read-only |
| Apple Contacts (AddressBook) | read-only |
| Google Calendar | OAuth scope `calendar.readonly` — the token cannot modify a calendar |
| Gmail | pulled by lieer; exo-gmi never pushes |

---

## What writes, and where

### Inside exo-mail's own store — free to delete and rebuild

`contacts.db`, `contacts-master.db`, `mesh.db`, `calendar.db`, `vectors.db`,
`imessage/snapshot.db`, `imessage/fts.db`, `audit.jsonl`, `sender-rules.tsv`,
`mesh-suppress.tsv`, the sync log. Every `.db` is derived; delete it and the tool
that owns it rebuilds it.

### notmuch tags — local, reversible, namespaced

`exo-mail tag`, `exo-mail-classify` and `exo-mail-needsreply` add and remove tags in
the `exo/*` namespace. `exo-mail tag` requires an explicit `+` or `-` on every
operation, and refuses any tag outside `exo/*` and the standard notmuch flags
(`unread`, `flagged`, `inbox`, `replied`, `passed`, `draft`) — so it cannot mark a
message deleted or spam. Tags live in the notmuch database and in Maildir flags;
removing one is symmetric with adding it.

### Gmail labels — additive, and opt-in

| Tool | What it does | Gate |
|---|---|---|
| `exo-mail-classify` | pushes an already-classified message's `exo/*` tags up as Gmail labels | **`EXO_LABEL_PUSH=1`**. Without it, classification stays entirely local |
| `exo-mail-filter` | retro-applies or retro-strips one label for the messages a rule matches | `EXO_DRY=1` prints every call and writes nothing |
| `exo-mail-label-backfill` | adds every local `exo/*` bucket as a Gmail label | `EXO_DRY=1` for counts only |
| `exo-mail-ensure-labels` | **creates** the `exo/*` labels in each account | `EXO_DRY=1` reports what would be created |

`batchModify` with `addLabelIds` is a no-op when the label is already present, so all
of these are idempotent. None of them deletes a label, and none touches a label
outside the `exo/` prefix.

### Outside the store — five tools, each gated

| Tool | Writes | Default |
|---|---|---|
| `exo-mail reply` / `compose` / `reconnect -m` | a Gmail **draft** | writes on every call — by design; a draft is not a send |
| `exo-mail-commitments` | Things 3 tasks, via the `things:///add` URL scheme | **dry run.** `--apply` is required to file anything |
| `exo-mesh-bedrock-apply` | markdown person files under `EXO_MAIL_PEOPLE` | **dry run.** `--apply` writes; exits 2 if no people directory is configured |
| `exo-mail-archdoc` | one generated markdown file at `EXO_MAIL_ARCHDOC_OUT` | overwrites that one file on every run. `--print` writes nothing; `--check` diffs |
| `exo-mail-sync.sh` | copies `sender-rules.tsv`, `mesh-suppress.tsv`, `contacts-master-strip.tsv` to `EXO_MAIL_STATE_BACKUP` | step is skipped entirely when that variable is unset |

`exo-mesh-bedrock-apply` never clobbers: on an existing person file it inserts
frontmatter keys and appends one interaction line. It creates a file only where none
exists.

`exo-mesh-since` reads the same person files and writes **none** of them. It reports
where a file and the mesh disagree and stops there: the row carries both values and
the observation behind it, and nothing in its output is an instruction. Deciding
whether a surfaced change should be applied is the caller's judgment, and applying it
is `exo-mesh-bedrock-apply`'s gated job or yours.

One nuance worth stating rather than hiding: `imessage/snapshot.db` is kept in SQLite's
write-ahead journal mode, so opening it — read-only, like every reader here — makes
SQLite create `snapshot.db-shm` and `snapshot.db-wal` beside it when they are absent.
Beside a live store they already exist and nothing new appears. No reader changes a
byte of the databases themselves, and none of them creates a file of its own.

---

## The draft review block

Every draft opens with a block you delete before sending. It exists because the
failure mode it prevents is expensive and silent — replying warmly to someone whose
last message you never answered, or promising a thing you already promised.

It names: who you are writing and at which address; where the relationship stands
across every channel; the linked person file, if you keep one; **commitments you made
to them**, pulled from your own sent mail; your last few exchanges; and which mailbox
the draft will go out from.

It is plain text and it is loud on purpose. If you find yourself sending it by
accident, that is the block doing its job badly — file an issue.

---

## Untrusted input

Mail bodies, calendar event titles and message text are **data, not instructions**.
If you wire this to an agent, treat every string that came out of a replica as
hostile: a message body can contain anything, including text shaped like a command.
The tools never evaluate content; a consumer must not either.

Header injection is handled where drafts are constructed: CR and LF are stripped from
`To` and `Subject` before the message is built.

---

## Credentials

OAuth client secrets and tokens live in `EXO_MAIL_CONFIG_DIR` (default
`~/.config/exo-mail`) and are written with mode `600`. lieer keeps its own
`.credentials.gmailieer.json` in each account's maildir. None of these files is in
this repository, none is tracked by git, and `.gitignore` names the shapes anyway.

`config.env` — your local settings — is also gitignored. `config.env.example` is the
tracked template and contains no real value.

---

## The rules of thumb

1. **Dry-run first.** `EXO_DRY=1` on the label tools, no `--apply` on the rest.
2. **One writer.** Run `exo-mail-sync.sh` on exactly one machine.
3. **`--test` and `--check` exist.** `exo-mesh-resolve --test`,
   `exo-mail-archdoc --check`, `exo-imsg test` all compute for real and write
   nothing.
4. **`exo-mail doctor` before you debug.** It tells you which layer is stale.
