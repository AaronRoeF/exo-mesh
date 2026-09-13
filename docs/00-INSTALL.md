# 00 — Install

Fresh macOS machine to a working replica. Roughly 30 minutes of your attention plus
however long the first Gmail pull takes (hours, for a large mailbox — it runs
unattended).

Nothing here needs `sudo`.

---

## 0. What you need

| | |
|---|---|
| macOS | Apple silicon or Intel. This is a macOS project — see [05-LIMITATIONS.md](05-LIMITATIONS.md) |
| Python | 3.14 is what this is developed and run on. No tool uses syntax newer than 3.8, but 3.14 is the only version it has been tested against |
| Homebrew | for `notmuch` |
| Gmail | one or more accounts. Only Gmail; lieer speaks the Gmail API, not IMAP |
| Disk | budget 1.5× the size of your mailbox for the Maildir, plus the index |
| Ollama | optional, only for `exo-mail semantic` |

---

## 1. notmuch

```sh
brew install notmuch
```

Decide where mail will live. The default this project assumes is `~/Mail`, with one
directory per account beneath it:

```sh
mkdir -p ~/Mail/work ~/Mail/personal
```

The names `work` and `personal` are just the default account names. Use whatever you
like — set `EXO_MAIL_ACCOUNTS` to match ([04-CONFIG.md](04-CONFIG.md)).

Configure notmuch. **This step also configures exo-mail:** your addresses, your name
and your mail root are read back out of `notmuch config`, so there is usually no
second identity to set up.

```sh
notmuch setup
```

Answer it like this:

- **Full name** — your real name. It is used for the review banner on drafts and to
  derive a default sign-off (`Jordan Rivera` → `~jr`).
- **Primary email** — the address of your *first* account, i.e. the first name in
  `EXO_MAIL_ACCOUNTS` (`work`, by default).
- **Other email addresses** — the remaining accounts, **in the same order** as
  `EXO_MAIL_ACCOUNTS`. Order matters: account *n* is matched to address *n*.
- **Mail directory** — `~/Mail` (or wherever you chose).

Verify:

```sh
notmuch config get user.primary_email
notmuch config get user.other_email
notmuch config get database.mail_root
```

Tell notmuch to ignore exo-mail's own store and its scratch files, so a stray `.json`
or lock file is never indexed as mail:

```sh
notmuch config set new.ignore 'exo;/.*[.](json|lock|bak)$/'
```

---

## 2. This repository and its venv

```sh
git clone https://github.com/AaronRoeF/exo-mesh.git ~/exo-mesh
cd ~/exo-mail
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
```

`notmuch2`, the Python binding lieer needs, compiles against the Homebrew `notmuch`
you installed in step 1. If pip cannot find its headers:

```sh
CFLAGS="-I$(brew --prefix notmuch)/include" LDFLAGS="-L$(brew --prefix notmuch)/lib" \
  ./venv/bin/pip install -r requirements.txt
```

The tools find this venv on their own: each one is a two-line `sh` header that
re-execs through `bin/exo-mail-python`, which looks for `../venv/bin/python` relative
to `bin/`. Nothing writes an absolute path into a file, so you can move or rename the
checkout freely. Confirm what resolved:

```sh
./bin/exo-mail-python bin/exomail_config.py
```

That prints every setting and where it came from. If `emails` shows your accounts and
`store` points somewhere sensible, you are configured — no config file needed. If
something is wrong, [04-CONFIG.md](04-CONFIG.md) explains each knob.

Optional, so you can type `exo-mail` from anywhere:

```sh
mkdir -p ~/.local/bin
ln -s ~/exo-mail/bin/exo-mail ~/.local/bin/exo-mail
ln -s ~/exo-mail/bin/exo-mesh ~/.local/bin/exo-mesh
```

---

## 3. Gmail credentials

Each Gmail account needs OAuth credentials that you own. Google's console, once:

1. Go to <https://console.cloud.google.com/> and create a project (any name).
2. **APIs & Services → Library** → enable **Gmail API**. Enable **Google Calendar
   API** and **People API** too if you want calendar and contacts.
3. **APIs & Services → OAuth consent screen** → External → add yourself as a test
   user. You are not publishing an app; test-user mode is the end state.
4. **Credentials → Create credentials → OAuth client ID → Desktop app.** Download
   the JSON.

Repeat for a second Google account only if the accounts are in different
organisations; otherwise one client works for both.

---

## 4. Connect each mail account (lieer)

lieer is installed in the venv as `gmi`. Run it once per account, inside that
account's directory:

```sh
cd ~/Mail/work
~/exo-mail/venv/bin/gmi init you@example.com
```

`gmi init` opens a browser for consent and writes `.credentials.gmailieer.json` and
`.state.gmailieer.json` into that directory. exo-mail reads both later, so leave them
where they are.

Then the first pull. Use `exo-gmi` rather than `gmi` directly — it sets the Gmail
query lieer has no flag for (skip chats, spam, trash, and anything over 250 KB):

```sh
cd ~/Mail/work && ~/exo-mail/bin/exo-gmi pull
cd ~/Mail/personal && ~/exo-mail/bin/exo-gmi pull
```

This is the long one. Override the query per account with `EXO_GMI_QUERY`, or
permanently with `EXO_GMI_QUERY_WORK` / `EXO_GMI_QUERY_PERSONAL`
([04-CONFIG.md](04-CONFIG.md)).

Index it:

```sh
notmuch new
notmuch count '*'
```

---

## 5. First derived build

```sh
cd ~/exo-mail
./bin/exo-mail-contacts       # correspondent index  -> contacts.db   (~2 min)
./bin/exo-mail-classify       # bucket newsletters, receipts, notifications
./bin/exo-mail doctor         # is everything wired?
```

`exo-mail doctor` is the thing to re-run whenever something looks wrong. It reports
sync freshness, per-account Gmail history IDs, bucket counts, mesh freshness,
embedding coverage, whether Ollama is up, and storage.

Try it:

```sh
./bin/exo-mail box imbox
./bin/exo-mail contact list
./bin/exo-mail contact drift --days 120
```

---

## 6. Calendar (optional)

Apple Calendar needs no credentials — it is read from the local SQLite store:

```sh
./bin/exo-cal pull-apple
./bin/exo-cal stats
```

Google calendars need the OAuth client from step 3, placed where exo-cal looks for
it. The *first* account in `EXO_MAIL_ACCOUNTS` uses the unsuffixed name; the rest are
suffixed with the account name:

```sh
mkdir -p ~/.config/exo-mail
cp ~/Downloads/client_secret_*.json ~/.config/exo-mail/gcp-oauth.keys.json           # first account
cp ~/Downloads/client_secret_*.json ~/.config/exo-mail/gcp-oauth-personal.keys.json  # each other account
chmod 600 ~/.config/exo-mail/*.json

./bin/exo-cal auth work
./bin/exo-cal auth personal
./bin/exo-cal pull-all
```

`exo-cal auth` opens a browser, catches the redirect on `127.0.0.1:55871`
(`EXO_OAUTH_PORT` to change it), and writes a token with mode 600. The scope is
`calendar.readonly` — exo-cal cannot modify a calendar even if you ask it to.

---

## 7. iMessage (optional)

**Requires Full Disk Access**, and this is the one prerequisite that fails silently
if you skip it: without it, `chat.db` reads **zero rows with no error**.

System Settings → Privacy & Security → Full Disk Access → add your terminal (and any
scheduler that will run the sync). Then:

```sh
./bin/exo-imsg snapshot
./bin/exo-imsg status
```

`snapshot` takes a WAL-consistent read-only copy into the store and advances a
cursor. It never writes to `chat.db`. Every path asserts it read a non-empty result
and fails loudly rather than reporting success over an empty read.

Then build the search surfaces:

```sh
./bin/exo-imsg-search --build      # FTS5 over individual messages
./bin/exo-imsg-index               # day-window embeddings (needs Ollama, step 9)
```

---

## 8. Contacts and the mesh (optional but recommended)

The mesh joins channels through a master contact record — the email↔phone spine.
`exo-mail-contacts-merge` builds it from your Apple Contacts (read-only) plus, if you
have them, per-account Google People exports named `gcontacts-<account>.json` in the
work directory (`EXO_MAIL_WORKDIR`, default `<store>/work`).

```sh
./bin/exo-mail-contacts-merge     # -> contacts-master.db
./bin/exo-mesh-resolve            # -> mesh.db, one row per person
./bin/exo-mesh-resolve --test     # same computation, writes nothing
```

Without a master record the mesh degrades to the email-only path — `contact drift`
still works, it just cannot see iMessage or shared meetings.

---

## 9. Semantic search (optional)

```sh
brew install ollama
ollama serve &
ollama pull nomic-embed-text
cd ~/exo-mail && ./bin/exo-mail-index
```

`exo-mail-index` is incremental: it skips anything already embedded, so re-running it
is cheap. Embeddings are computed locally by Ollama on `localhost:11434`; no mail
content leaves the machine.

```sh
./bin/exo-mail semantic "the contract redline thread from last spring"
```

---

## 10. Schedule the sync

`bin/exo-mail-sync.sh` runs the whole pipeline: pull each account, `notmuch new`,
embed, calendar, iMessage snapshot, mesh resolve, classify, needs-reply, and a daily
correspondent rebuild. It takes an atomic lock, so overlapping runs are a no-op.

**Run it on exactly one machine.** It is a single writer; two machines pulling into
one mail root will corrupt lieer's state.

Dry it once by hand first:

```sh
~/exo-mail/bin/exo-mail-sync.sh
tail -40 ~/.local/share/exo-mail/sync.log
```

Then a scheduled job. A plist needs absolute paths, so write it with a heredoc
and let the shell fill them in — no hand-editing, nothing to get wrong:

```sh
mkdir -p ~/Library/LaunchAgents ~/Library/Logs
cat > ~/Library/LaunchAgents/com.example.exo-mail-sync.plist <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.example.exo-mail-sync</string>
  <key>ProgramArguments</key>
  <array><string>/bin/bash</string><string>$HOME/exo-mail/bin/exo-mail-sync.sh</string></array>
  <key>StartInterval</key><integer>600</integer>
  <key>RunAtLoad</key><false/>
  <key>StandardOutPath</key><string>$HOME/Library/Logs/exo-mail-sync.out.log</string>
  <key>StandardErrorPath</key><string>$HOME/Library/Logs/exo-mail-sync.err.log</string>
</dict>
</plist>
EOF
```

Adjust the checkout path if you did not clone into your home directory, then load
it in your own user domain — no elevation, no `sudo`:

```sh
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.example.exo-mail-sync.plist
launchctl print gui/$(id -u)/com.example.exo-mail-sync | head -20
```

Tell `exo-mail doctor` to check that the job is loaded by naming the label in your
config: `EXO_MAIL_SYNC_JOB=com.example.exo-mail-sync`. Unset, the check is skipped
rather than reported as a failure.

If the sync will snapshot iMessage, grant Full Disk Access to `/bin/bash` as well —
the LaunchAgent runs outside your terminal's grant.

To stop it: `launchctl bootout gui/$(id -u)/com.example.exo-mail-sync`.

---

## 11. Verify

```sh
cd ~/exo-mail
bash tests/smoke.sh
./bin/exo-mail doctor
./bin/exo-mesh
```

`tests/smoke.sh` is read-only and never touches the network. It skips (loudly) rather
than passing silently when a store is absent, so it is also the right thing to run on
a machine where you only set up part of this.

Next: [01-CONCEPTS.md](01-CONCEPTS.md) for what the mesh actually is, or
[02-USAGE.md](02-USAGE.md) to start using it.
