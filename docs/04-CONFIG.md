# 04 — Configuration

Start here: **you probably need none of this.**

```sh
./bin/exo-mail-python bin/exomail_config.py
```

That prints every setting and what it resolved to, as JSON. If it looks right, you
are done. Add a config file only to change something it got wrong.

---

## How a setting resolves

```
  environment variable   >   config file   >   derived default
```

The config file is the first readable one of:

1. `$EXO_MAIL_CONFIG`
2. `<checkout>/config.env` — beside `bin/`
3. `~/.config/exo-mail/config.env`
4. `$EXO_MAIL_HOME/config.env`

Format is `KEY=value`, `#` comments, optional quotes; `~` and `$HOME` expand. It is a
deliberate subset of shell syntax, so `exo-mail-sync.sh` sources the same file rather
than re-implementing the resolution.

Copy [`config.env.example`](../config.env.example) to one of those paths and
uncomment what you need. **Do not commit your copy** — `config.env` is in
`.gitignore` precisely because it names directories on your machine.

---

## Why identity is derived rather than configured

Your addresses, your name and your mail root are read from `notmuch config`, which
you set up when you installed notmuch:

| exo-mail setting | notmuch key |
|---|---|
| address of account 1 | `user.primary_email` |
| addresses of accounts 2..n, in order | `user.other_email` |
| owner name | `user.name` |
| mail root | `database.mail_root` |

So a fresh install needs no identity configuration, and no address or home directory
has to live in a tracked file. If `notmuch config get user.other_email` does not
list your accounts in the same order as `EXO_MAIL_ACCOUNTS`, either fix notmuch or
set `EXO_MAIL_EMAIL_<ACCOUNT>` explicitly.

---

## Every setting

### Locations

| Variable | Default | What it is |
|---|---|---|
| `EXO_MAIL_HOME` | `~/.local/share/exo-mail` | runtime dir — the venv it falls back to, the sync log |
| `EXO_MAIL_ROOT` | notmuch `database.mail_root` | maildir root; one directory per account beneath it |
| `EXO_MAIL_STORE` | `$EXO_MAIL_ROOT/exo` | every `.db`, the audit log, the rule files |
| `EXO_MAIL_CONFIG_DIR` | `~/.config/exo-mail` | OAuth client secrets and tokens (mode 600) |
| `EXO_MAIL_WORKDIR` | `$EXO_MAIL_STORE/work` | scratch dir for tools that write reports |
| `EXO_MAIL_BIN` | `$EXO_MAIL_HOME/bin` | where tools look for their siblings |
| `EXO_NOTMUCH` | first found of the usual paths | the notmuch executable |
| `EXO_MAIL_PYTHON` | `<bin>/../venv/bin/python` | the interpreter every tool re-execs into |

### Accounts

| Variable | Default | What it is |
|---|---|---|
| `EXO_MAIL_ACCOUNTS` | `work,personal` | ordered account names; each is a directory under `EXO_MAIL_ROOT` and a valid `--account` value |
| `EXO_MAIL_EMAIL_<ACCT>` | from notmuch | that account's `From:` address. Uppercase the name, `-` becomes `_` |
| `EXO_MAIL_SELF_EMAILS` | — | extra addresses that are also you (old domains, aliases), comma separated |
| `EXO_GMI_QUERY` | `-in:chats -in:spam -in:trash -larger:250K` | default Gmail pull query |
| `EXO_GMI_QUERY_<ACCT>` | the above | per-account override |

### Identity

| Variable | Default | What it is |
|---|---|---|
| `EXO_MAIL_OWNER` | notmuch `user.name` | your name; first word, uppercased, heads the draft review banner |
| `EXO_MAIL_SIGNOFF` | `~` + lowercase initials | how the review block reminds you to sign |

### Optional features — unset means "skip", never "crash"

| Variable | Enables |
|---|---|
| `EXO_MAIL_NOTES` | the journal line in `exo-day`, and the default location of the people dir |
| `EXO_MAIL_PEOPLE` | person-file enrichment across the mesh; `exo-mesh-bedrock-apply` |
| `EXO_MAIL_BEDROCK_STAGE` | where `exo-mesh-bedrock-apply` reads its confirmed list (default `<workdir>/bedrock-confirmed.tsv`) |
| `EXO_MAIL_ARCHDOC_OUT` | where `exo-mail-archdoc` writes (default `<workdir>/exo-mail.md`) |
| `EXO_MAIL_STATE_BACKUP` | the sync copies hand-authored rule files here. Unset = step skipped |
| `EXO_MAIL_BUCKETS` | which `exo/*` namespaces the label tools keep in sync |
| `EXO_MAIL_STORAGE_CAP_MB` | soft cap (default `14336`); over it the sync log gets a ranked list of ways to reclaim space. It never deletes |
| `EXO_MAIL_SYNC_JOB` | the scheduler label `exo-mail doctor` checks is loaded. Unset = check skipped |
| `EXO_MAIL_CAPS_URL` | a page `exo-mesh caps` points at. Unset = the line is omitted |
| `EXO_MAIL_SYNC_LOG` | sync log path (default `$EXO_MAIL_HOME/sync.log`) |
| `EXO_OAUTH_PORT` | loopback port for `exo-cal auth` (default `55871`) |

### Per-run flags, not config

| Variable | Effect |
|---|---|
| `EXO_DRY=1` | `exo-mail-classify`, `exo-mail-filter`, `exo-mail-label-backfill`, `exo-mail-ensure-labels` print intended calls and perform none |
| `EXO_LABEL_PUSH=1` | lets `exo-mail-classify` push labels to Gmail. Without it, classification is local-only |
| `EXO_LIMIT=N` | caps `exo-mail-classify`'s candidate set, for sampling |

---

## Worked example: a second machine, a different layout

You keep mail on an external volume, name your accounts after the domains, and keep
notes in iCloud. `~/.config/exo-mail/config.env`:

```sh
EXO_MAIL_ROOT=/Volumes/Archive/Mail
EXO_MAIL_ACCOUNTS=acme,personal
EXO_MAIL_EMAIL_ACME=jordan@acmerobotics.example.com
EXO_MAIL_EMAIL_PERSONAL=jordan.rivera@example.com
EXO_GMI_QUERY_PERSONAL=(label:^smartlabel_personal OR from:me) -in:chats -in:spam -in:trash
EXO_MAIL_NOTES=$HOME/Documents/Notes
EXO_MAIL_PEOPLE=$HOME/Documents/Notes/people
EXO_MAIL_STATE_BACKUP=$HOME/Documents/Notes/exo-mail-state
```

Check it:

```sh
./bin/exo-mail-python bin/exomail_config.py | grep -E 'mail_root|accounts|emails|people'
./bin/exo-mail --account acme box imbox --limit 5
```

`--account acme` now exists as a choice, and `exo-mail-sync.sh` pulls
`/Volumes/Archive/Mail/acme` and `/Volumes/Archive/Mail/personal` with different
queries.

---

## Relocating the whole thing

There is no install step to redo. Each tool is a two-line `sh` header that re-execs
through `bin/exo-mail-python`, which resolves the interpreter relative to `bin/` —
so moving, renaming or symlinking the checkout just works. Move it, then:

```sh
./bin/exo-mail-python bin/exomail_config.py    # confirm
./bin/exo-mail doctor
```

If you point a scheduler at the old path, update that too.
