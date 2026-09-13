# 05 — Limitations

The honest list. Read it before you invest a weekend.

---

## macOS only, and not portably

The calendar, iMessage and contacts layers read Apple's local SQLite stores —
`~/Library/Group Containers/group.com.apple.calendar/Calendar.sqlitedb`,
`~/Library/Messages/chat.db`, `~/Library/Application Support/AddressBook/…` — and
`exo-mail-commitments` speaks the Things 3 URL scheme. `exo-mail-sync.sh` uses
`stat -f %m` and `du -sm`, which are BSD spellings.

The **mail** half (lieer + notmuch + the CLI + semantic search + the email side of
the mesh) has no macOS dependency beyond those two shell idioms, so a Linux port is
mostly a matter of dropping the Apple readers and fixing `stat`. Nobody has done it.

## Gmail only

lieer speaks the Gmail API. No IMAP, no Exchange, no Fastmail. If your mail is not
in Gmail, the replica layer does not apply — and the mesh, drift and BEDROCK all sit
on top of it.

## iMessage needs Full Disk Access, and fails silently without it

`chat.db` is TCC-protected. Without Full Disk Access for the process doing the
reading, it returns **zero rows with no error** — indistinguishable from an empty
database, which is how you end up with a confidently wrong "you have never texted
this person."

Every iMessage path asserts a non-empty read and fails loudly instead. Grant access
to your terminal *and* to whatever runs the scheduled sync — a LaunchAgent running
`/bin/bash` does not inherit your terminal's grant.

## Single writer

`exo-mail-sync.sh` takes an atomic lock against itself, but nothing stops a *second
machine* from pulling into the same mail root, and lieer's per-account state file
does not survive that. Run the sync on exactly one machine. Other machines can read
the store over a shared volume, but only one may write.

## Semantic search needs a local model server

`exo-mail semantic` and `exo-imsg-index` require Ollama on `localhost:11434` with
`nomic-embed-text` pulled. Without it, `semantic` returns a `NETWORK` error and the
index step is a no-op; everything else works. Embedding a large mailbox the first
time takes hours. Nothing is sent off the machine.

## Disk

Budget roughly 1.5× your mailbox for the Maildir, plus the notmuch index, plus
768-dimension vectors for every chunk of every message. `exo-mail storage` reports
the breakdown and ranks ways to reclaim space; the sync logs a warning past
`EXO_MAIL_STORAGE_CAP_MB` (default 14 GB) and never deletes anything itself.

## Calendar coverage is uneven

Apple Calendar events carry no attendee list in the local store, so the
shared-meeting channel in the mesh is effectively **Google-only**. If your calendar
is Apple-only, `cal_count` will be zero for everyone and the mesh runs on email plus
iMessage. The replica window is 730 days back and 365 forward — nothing older or
further out is stored.

## Contacts merging is heuristic

Linking is by shared email or shared last-ten-digits phone number, with a
shared-line guard (more than four distinct names on one key means an office line,
and does not link) and a rule that a name alone never links. It is deliberately
conservative, so expect **duplicate people** rather than wrongly merged ones. There
is no interactive merge UI in this repository; that tooling was written against a
private notes vault and is not published.

## BEDROCK's fourth criterion is not computed

By design. A machine cannot distinguish "we still talk because we still work
together" from "we still talk although nothing makes us." `bedrock candidates` emits
a review list; a human confirms. If you were hoping for an automatic answer, this is
not it.

## No deletion, no send, no undo tooling

No send path exists, which is a feature. But it also means there is no outbox, no
scheduled send, no snooze, and no way to clean up mail from here — trash and spam
are things you do in Gmail.

## Not a product

One person runs this daily; that is the whole of the testing. There is no CI matrix,
no version guarantee, no support commitment, and the schema of any `.db` may change
in a commit (they are all derived — delete and rebuild). Expect to read the source.
Issues and forks are welcome; an answer is not promised.

## Known rough edges

- `exo-day`'s task counts assume Things 3. Without it, the section is omitted.
- `exo-mail contact search` matches on substrings and will happily return a company.
- A store written by an older build may be missing a column a newer tool asks for.
  Readers treat that as "not present" and self-heal on the next rebuild — the
  correspondent index is rebuilt daily, `mesh.db` on every sync — so the symptom is
  a transiently empty field, not a crash.
- The first `exo-gmi pull` on a large mailbox is measured in hours and has no
  resume-progress display beyond lieer's own.
