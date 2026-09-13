"""exomail_config — one place every exo-mail tool asks for a path or an identity.

Stdlib only, on purpose: some tools are loaded with SourceFileLoader under the
system python3 (not the venv) by the test suites, so this module must import
there too.

RESOLUTION ORDER, for every setting:
    environment variable  ->  config file  ->  derived default

Config file, first readable wins:
    $EXO_MAIL_CONFIG
    <bin>/../config.env          (beside a checkout, or beside the install dir)
    ~/.config/exo-mail/config.env
    $EXO_MAIL_HOME/config.env

Format is `KEY=value`, `#` comments, optional quotes -- deliberately a subset of
shell syntax so exo-mail-sync.sh can `.` the same file.

WHY IDENTITY IS DERIVED, NOT CONFIGURED. notmuch already knows who you are:
`user.primary_email`, `user.other_email`, `user.name` and `database.mail_root`
are set up when you configure notmuch, which every exo-mail install does anyway.
Deriving from there means a fresh install needs no config at all, and no address,
name or home directory has to live in a tracked file.

Nothing here raises on a missing setting. A feature whose directory is unset
degrades (and says so); it never crashes.
"""

import os
import subprocess

__all__ = [
    "get", "bin_dir", "home", "mail_root", "store", "store_path", "config_dir",
    "accounts", "email_for", "emails", "self_emails", "owner_name", "owner_short",
    "signoff", "notes_dir", "people_dir", "workdir", "archdoc_out", "caps_url",
    "notmuch_bin", "col_of", "row_get", "account_maildir", "describe",
    "observations_dir",
]

BIN = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------------------- config file


def _expand(v):
    return os.path.expanduser(os.path.expandvars(v)) if v else v


_FILE = None


def _file():
    """Parse the first readable config file. Cached; {} when there is none."""
    global _FILE
    if _FILE is not None:
        return _FILE
    _FILE = {}
    candidates = [
        os.environ.get("EXO_MAIL_CONFIG"),
        os.path.join(BIN, os.pardir, "config.env"),
        os.path.expanduser("~/.config/exo-mail/config.env"),
        os.path.join(_home_raw(), "config.env"),
    ]
    for c in candidates:
        if not c:
            continue
        c = os.path.abspath(_expand(c))
        if not os.path.isfile(c):
            continue
        try:
            with open(c, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    if line.startswith("export "):
                        line = line[len("export "):].lstrip()
                    k, _, v = line.partition("=")
                    k = k.strip()
                    v = v.strip()
                    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                        v = v[1:-1]
                    if k:
                        _FILE[k] = v
        except OSError:
            continue
        break
    return _FILE


def get(key, default=""):
    """Env var, then config file, then `default`. Always a str."""
    v = os.environ.get(key)
    if v is None:
        v = _file().get(key)
    return v if v not in (None, "") else default


def _path(key, default):
    return _expand(get(key, default))


# --------------------------------------------------------------------------- notmuch


_NM_CONF = None


def _notmuch_conf():
    """`notmuch config list` as a dict. Cached; {} if notmuch is unavailable."""
    global _NM_CONF
    if _NM_CONF is not None:
        return _NM_CONF
    _NM_CONF = {}
    try:
        r = subprocess.run([notmuch_bin(), "config", "list"],
                           capture_output=True, text=True, timeout=10)
        for line in (r.stdout or "").splitlines():
            k, _, v = line.partition("=")
            if k:
                _NM_CONF[k.strip()] = v.strip()
    except Exception:
        pass
    return _NM_CONF


def notmuch_bin():
    """The notmuch executable. $EXO_NOTMUCH wins; then the usual install sites."""
    v = get("EXO_NOTMUCH")
    if v:
        return _expand(v)
    for c in ("/opt/homebrew/bin/notmuch", "/usr/local/bin/notmuch", "/usr/bin/notmuch"):
        if os.path.exists(c):
            return c
    return "notmuch"


# --------------------------------------------------------------------------- locations


def _home_raw():
    return _expand(get("EXO_MAIL_HOME", "~/.local/share/exo-mail"))


def bin_dir():
    """Where the tools live. Tools invoke each other through this."""
    return _path("EXO_MAIL_BIN", os.path.join(_home_raw(), "bin"))


def home():
    """Runtime dir: the venv, the sync log, machine-local state."""
    return _home_raw()


def mail_root():
    """Maildir root. notmuch's own database.mail_root is the source of truth."""
    v = get("EXO_MAIL_ROOT")
    if v:
        return _expand(v)
    nm = _notmuch_conf().get("database.mail_root") or _notmuch_conf().get("database.path")
    return nm or os.path.expanduser("~/Mail")


def store():
    """exo-mail's own data dir: every .db, the audit log, the rule files."""
    return _path("EXO_MAIL_STORE", os.path.join(mail_root(), "exo"))


def store_path(*parts):
    return os.path.join(store(), *parts)


def config_dir():
    """Where OAuth client secrets and tokens live."""
    return _path("EXO_MAIL_CONFIG_DIR", "~/.config/exo-mail")


def account_maildir(acct):
    return os.path.join(mail_root(), acct)


# --------------------------------------------------------------------------- identity


def accounts():
    """Ordered account names. These are also the maildir names under mail_root()."""
    raw = get("EXO_MAIL_ACCOUNTS", "work,personal")
    return [a.strip() for a in raw.split(",") if a.strip()]


def _nm_addresses():
    c = _notmuch_conf()
    out = []
    p = c.get("user.primary_email", "").strip()
    if p:
        out.append(p)
    for o in c.get("user.other_email", "").split(";"):
        o = o.strip()
        if o and o not in out:
            out.append(o)
    return out


def email_for(acct):
    """The From: address for one account. EXO_MAIL_EMAIL_WORK etc., else notmuch."""
    v = get("EXO_MAIL_EMAIL_%s" % acct.upper().replace("-", "_"))
    if v:
        return v
    accs = accounts()
    addrs = _nm_addresses()
    if acct in accs:
        i = accs.index(acct)
        if i < len(addrs):
            return addrs[i]
    return addrs[0] if addrs else ""


def emails():
    """{account: address} for every configured account, skipping unresolved ones."""
    return dict((a, e) for a, e in ((a, email_for(a)) for a in accounts()) if e)


def self_emails():
    """Every address that is you. Used to tell 'sent by me' from 'sent to me'."""
    s = set(e.lower() for e in emails().values() if e)
    s.update(e.lower() for e in _nm_addresses())
    extra = get("EXO_MAIL_SELF_EMAILS")
    if extra:
        s.update(x.strip().lower() for x in extra.replace(";", ",").split(",") if x.strip())
    return s


def owner_name():
    """Your full name, for review banners and own-contact detection."""
    return get("EXO_MAIL_OWNER") or _notmuch_conf().get("user.name", "")


def owner_short():
    """First name, upper-cased, for the 'READ BEFORE SENDING' banner."""
    n = owner_name().split()
    return n[0].upper() if n else "YOU"


def signoff():
    """How you sign mail. Defaults to ~ plus your lower-case initials."""
    v = get("EXO_MAIL_SIGNOFF")
    if v:
        return v
    parts = [p for p in owner_name().split() if p]
    return ("~" + "".join(p[0].lower() for p in parts)) if parts else ""


# --------------------------------------------------------------------------- optional dirs


def notes_dir():
    """A markdown notes vault, if you keep one. Unset = the feature is skipped."""
    return _path("EXO_MAIL_NOTES", "")


def people_dir():
    """One markdown file per person, named <first-last>.md. Optional enrichment."""
    v = _path("EXO_MAIL_PEOPLE", "")
    if v:
        return v
    n = notes_dir()
    return os.path.join(n, "people") if n else ""


def observations_dir():
    """Where a tool drops a note when it decided something on its own. Unset falls back
    to the workdir, so an unconfigured install still records its own decisions somewhere
    rather than silently discarding them."""
    v = _path("EXO_MAIL_OBS", "")
    return v or os.path.join(workdir(), "observations")


def workdir():
    """Scratch/report dir for the tools that write JSON or markdown reports."""
    return _path("EXO_MAIL_WORKDIR", os.path.join(store(), "work"))


def archdoc_out():
    """Where exo-mail-archdoc writes the generated architecture section."""
    return _path("EXO_MAIL_ARCHDOC_OUT", os.path.join(workdir(), "exo-mail.md"))


def caps_url():
    """Optional URL of a self-hosted capabilities page, printed by `exo-mesh caps`."""
    return get("EXO_MAIL_CAPS_URL", "")


# --------------------------------------------------------------------------- sqlite compat


def col_of(con, table, *names):
    """First of `names` that exists as a column on `table`, else ''.

    Lets a reader name a column that an older store may not have yet: a store
    written by an earlier build degrades to "not present" and self-heals on its
    next rebuild (contacts.db daily, mesh.db every sync) instead of raising.
    """
    try:
        cols = set(r[1] for r in con.execute("PRAGMA table_info(%s)" % table))
    except Exception:
        return ""
    for n in names:
        if n in cols:
            return n
    return ""


def row_get(row, *names):
    """First present column among `names` on a sqlite3.Row, else None."""
    for n in names:
        try:
            return row[n]
        except (IndexError, KeyError, TypeError):
            continue
    return None


# --------------------------------------------------------------------------- self-report


def describe():
    return {
        "bin": BIN,
        "home": home(),
        "mail_root": mail_root(),
        "store": store(),
        "config_dir": config_dir(),
        "accounts": accounts(),
        "emails": emails(),
        "self_emails": sorted(self_emails()),
        "owner": owner_name(),
        "signoff": signoff(),
        "notes_dir": notes_dir(),
        "people_dir": people_dir(),
        "workdir": workdir(),
        "archdoc_out": archdoc_out(),
        "caps_url": caps_url(),
        "notmuch": notmuch_bin(),
        "config_file_keys": sorted(_file().keys()),
    }


def _sh_quote(v):
    return "'" + str(v).replace("'", "'\\''") + "'"


def emit_sh():
    """Shell assignments for the resolved core settings plus every config-file key.

    Lets a shell script share this module's resolution instead of re-implementing
    it:  eval "$("$BIN/exo-mail-python" "$BIN/exomail_config.py" --sh)"
    """
    out = [
        ("EXO_MAIL_HOME", home()),
        ("EXO_MAIL_BIN", BIN),
        ("EXO_MAIL_ROOT", mail_root()),
        ("EXO_MAIL_STORE", store()),
        ("EXO_MAIL_CONFIG_DIR", config_dir()),
        ("EXO_MAIL_ACCOUNTS", ",".join(accounts())),
        ("EXO_MAIL_WORKDIR", workdir()),
        ("EXO_MAIL_ARCHDOC_OUT", archdoc_out()),
        ("EXO_NOTMUCH", notmuch_bin()),
    ]
    seen = set(k for k, _ in out)
    for k, v in sorted(_file().items()):
        if k not in seen:
            out.append((k, _expand(v)))
    return "\n".join("%s=%s; export %s" % (k, _sh_quote(v), k) for k, v in out)


if __name__ == "__main__":
    import json
    import sys
    if "--sh" in sys.argv:
        print(emit_sh())
    else:
        print(json.dumps(describe(), indent=2))
    sys.exit(0)
