"""mesh_person — one person across mail and texts: who they are, and every item exchanged.

The shared core of `exo-mesh conversation` and `exo-mesh relationship` (and of any MCP tool
that serves them). Three things live here so the two commands cannot disagree about them:

  WHO    resolve_person(query, identities) turns a phone number, an email address or a full
         name into exactly one row of the mesh `identity` table, or fails naming why.
  WHAT   load_timeline(person, ...) reads that person's mail (the local notmuch index) and
         texts (the iMessage snapshot) into one list of items, oldest first, plus the
         tapback reactions kept apart from it.
  HOW    the envelope: ok_envelope / error_envelope / emit, with the exit codes exo-mail
         already uses (0 OK, 1 USAGE, 2 NOTFOUND, 8 AMBIGUOUS).

RESOLUTION. Three tiers, tried in order; the first tier with any match decides:
  1. phone  the query, stripped of spaces, dashes, dots and parentheses, is "+" and 8 to 15
            digits, or 10 or more digits. It matches identities whose phones share its last
            ten digits.
  2. email  the query contains "@". It matches identities that own that exact address,
            compared case-insensitively.
  3. name   the query, case-folded with runs of whitespace collapsed and the ends trimmed,
            equals an identity's name normalized the same way.
More than one identity at the deciding tier is AMBIGUOUS, listing every candidate. No match at
any tier is NOTFOUND. A substring or a first name never matches, and nothing is ranked by volume
to break a tie: a guess that is usually right is the failure this exists to prevent.

ITEMS. A mail item is a message FROM one of the person's addresses (received), or FROM one of
the owner's addresses TO, CC or BCC one of the person's (sent). A text item is a message in a
one-to-one chat whose single handle the person owns: phones compared by their last ten digits,
emails case-insensitively. Rows with associated_message_type 2000-3999 are reactions, never
items; types 2000-2006 add a tapback and 3000-3006 remove the same type. A text's words come
from imsg_text, so text held only in the packed body is read, and a body that cannot be decoded
leaves the item with empty text rather than dropping it.

TIME. Every instant is an integer epoch second taken from a store. Nothing here reads the wall
clock: a window is anchored on --until, which defaults to the person's newest item or reaction
on the channels read.

READ-ONLY. Every SQLite store is opened with mode=ro, and the only process launched is the local
notmuch binary, with read-only subcommands. Stdlib only, like exomail_config.
"""

import datetime
import email.utils
import html
import json
import os
import re
import sqlite3
import subprocess
import time

import exomail_config as CFG
import imsg_text

__all__ = [
    "EXIT", "APPLE_EPOCH", "TAPBACKS", "UNTRUSTED", "MeshError",
    "ok_envelope", "error_envelope", "emit", "parse_args",
    "norm_name", "phone_key", "key_of", "phone_values", "phones_of",
    "query_tier", "load_identities", "resolve_person",
    "mesh_path", "snapshot_path", "mail_path", "Zone", "parse_duration", "parse_day",
    "resolve_window", "in_window", "load_timeline", "fetch_mail_details", "iso_day", "utc_day",
]

EXIT = {"OK": 0, "USAGE": 1, "NOTFOUND": 2, "AMBIGUOUS": 8}
APPLE_EPOCH = 978307200
NS = 1000000000
REACTION_LO, REACTION_HI = 2000, 3999
TAPBACKS = ("love", "like", "dislike", "laugh", "emphasize", "question", "emoji")
UNTRUSTED = "untrusted"
SNIPPET_CHARS = 500
ID_BATCH = 100                       # message ids per notmuch query when fetching details

DUR = re.compile(r"^(\d+)\s*([mhdw])$", re.I)
UNIT = {"m": 60, "h": 3600, "d": 86400, "w": 604800}
ISO_DAY = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
PHONE_STRIP = re.compile(r"[\s\-.()]")
PHONE_E164 = re.compile(r"^\+\d{8,15}$")
PHONE_BARE = re.compile(r"^\d{10,}$")
NM_ID = re.compile(r'id:(?:"((?:[^"]|"")*)"|(\S+))')


# ----------------------------------------------------------------------------- envelope
class MeshError(Exception):
    """A failure that becomes an error envelope: code is a key of EXIT."""

    def __init__(self, code, error, hint="", **extra):
        Exception.__init__(self, error)
        self.code, self.error, self.hint, self.extra = code, error, hint, extra

    def envelope(self):
        return error_envelope(self.code, self.error, self.hint, **self.extra)


def error_envelope(code, error, hint="", **extra):
    """exo-mail's error shape. AMBIGUOUS adds candidates; a missing store adds path. No person,
    no data."""
    env = {"ok": False, "error": error, "code": code, "hint": hint, "retryable": False}
    env.update(extra)
    return env


def ok_envelope(person, data, sources, summary, content_trust):
    return {"ok": True, "person": {"identity_id": person["identity_id"], "name": person["name"]},
            "data": data, "sources": sources, "summary": summary, "content_trust": content_trust}


def emit(env):
    """Print the envelope as one JSON line; return its exit code."""
    print(json.dumps(env))
    return EXIT["OK"] if env.get("ok") else EXIT.get(env.get("code"), 1)


def parse_args(argv, options, usage_hint):
    """(positional words joined by one space, {option: value}, wants_help). `options` maps each
    --name to its default. --json is accepted and ignored: the output is always the envelope."""
    opts = dict(options)
    words = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("-h", "--help"):
            return "", opts, True
        if a == "--json":
            i += 1
            continue
        if a.startswith("--"):
            name, eq, val = a[2:].partition("=")
            if name not in opts:
                raise MeshError("USAGE", "unknown option: --%s" % name, usage_hint)
            if not eq:
                if i + 1 >= len(argv):
                    raise MeshError("USAGE", "--%s needs a value" % name, usage_hint)
                val = argv[i + 1]
                i += 1
            opts[name] = val
            i += 1
            continue
        if a.startswith("-") and len(a) > 1 and not a[1].isdigit():
            raise MeshError("USAGE", "unknown option: %s" % a, usage_hint)
        words.append(a)
        i += 1
    return " ".join(w for w in words if w.strip()), opts, False


# ----------------------------------------------------------------------------- normalizing
def norm_name(s):
    return " ".join((s or "").casefold().split())


def digits(s):
    return re.sub(r"\D", "", s or "")


def phone_key(s):
    """The last ten digits of a phone-like string, or all of them when it has fewer."""
    d = digits(s)
    return d[-10:] if d else ""


def handle_key(h):
    """The key a text handle is owned by: a lower-cased email, or a phone's last ten digits."""
    h = (h or "").strip()
    return h.lower() if "@" in h else phone_key(h)


# ----------------------------------------------------------------------------- card phone keys
# The one rule every surface keys an address-book card's numbers by: the mesh resolver, which
# writes identity.phones, and each text surface that names a text by its card. One rule, so the name
# a text carries and the identity it belongs to cannot disagree.
#
# master.phones holds a person's phone values one per line, each exactly as its address-book field
# stored it (exo-mail-contacts-merge writes it that way). A card's numbers are keyed one stored value
# at a time and never across two, because a formatted number has spaces of its own and a string
# joined from several numbers cannot say where one ends. A key a card should have and does not get
# is recoverable: the person is still found by email or name, and a two-way texter from that number
# gets an identity of their own. A fused or truncated key is not: it attaches another person's number
# and text counts to the wrong card. So a value this rule cannot read keys nothing.
#
# A value that lists several numbers splits only at an explicit list separator, in any letter case:
# a comma or semicolon followed by a space and another number, a slash (with or without spaces), or
# `or`, `and`, `&` or `|` with a space on each side. A number never holds one of these.
_LIST_SEP = re.compile(r"(?i)[,;]\s+(?=[\d+(])|\s*/\s*|\s+(?:or|and|&|\|)\s+")
# A comma or semicolon with no space after it splits two numbers only when the text after it is
# written as a number (opening with `+` or `(`, or with a group of up to four digits and a dash, a
# dot or a space) and keys on its own. Otherwise it is a pause: `,123` is dialled after the number,
# and so is a packed run (`,5550000419`), which is how a conference code is dialled.
_BARE_SEP = re.compile(r"[,;](?=\S)")
_WRITTEN_NUMBER = re.compile(r"[+(]|\d{1,4}[-. ]")
# An extension or a pause, cut from it on: an `x` or `ext` that no letter comes before (so the `x`
# of a `Fax:` label cuts nothing), a `#`, a comma or semicolon left inside the value, or a `p` or
# `w` right after a digit, as a phone dials a pause or a wait.
_EXT = re.compile(r"(?i)(?<![^\W\d_])(?:ext|x)|[#,;]|(?<=\d)\s*[pw]")
# An international dialling prefix before a country code (1-9). `0011` is an exit code of its own
# and is tried first: no country code but 1 opens with 1 and no North American area code opens with
# 0 or 1, so digits opening `0011` can be nothing else.
_INTL = re.compile(r"^(?:0011|00|011)(?=[1-9])")
_TRUNK = re.compile(r"\(\s*0\s*\)")   # a trunk zero after the country code: dialled at home, never in a handle


def key_of(value):
    """The last-ten-digit key of one number, or "" when it keys nothing. The extension or pause is
    cut first. A `+`, or digits opening with `0011`, `00` or `011` before a country code, is read as
    an international number whatever its length, with any `(0)` trunk zero dropped. Digits after the
    prefix that open with `1` are a North American number: exactly eleven key the ten after the `1`,
    and any other count keys nothing, since the last ten of a longer run is no number on the card.
    Other digits after the prefix are read when there are 8 to 15 of them, an international number's
    length, and key their last ten, so fewer than ten key nothing. Without a prefix, ten digits are
    the key, eleven opening with `1` key their last ten, and anything else keys nothing."""
    v = _EXT.split(value or "", 1)[0].strip()
    d = digits(v)
    if v.startswith("+") or _INTL.match(d):
        d = digits(_TRUNK.sub("", v))
        intl = d if v.startswith("+") else _INTL.sub("", d, 1)
        if intl[:1] == "1":
            return intl[1:] if len(intl) == 11 else ""
        if not 8 <= len(intl) <= 15:          # no international number is shorter or longer
            return ""
        return intl[-10:] if len(intl) >= 10 else ""   # every key is ten digits
    if len(d) == 10:
        return d
    return d[1:] if len(d) == 11 and d[0] == "1" else ""


def phone_values(line):
    """One stored value split into the numbers it lists, at its list separators only."""
    out = []
    for v in _LIST_SEP.split(line or ""):
        start = 0
        for m in _BARE_SEP.finditer(v):
            rest = v[m.end():]
            if _WRITTEN_NUMBER.match(rest) and key_of(rest):
                out.append(v[start:m.start()])
                start = m.end()
        out.append(v[start:])
    return out


def phones_of(s):
    """Every key on a card, in order: the phones field split into its stored values (one per line),
    each value split into the numbers it lists, and each number keyed alone. Never split on a bare
    space, never read across two values."""
    return [k for line in (s or "").splitlines() for v in phone_values(line) for k in [key_of(v)] if k]


def query_tier(query):
    """(tier, key) for a person query: ("phone", last ten digits), ("email", lower-cased
    address) or ("name", normalized name). A query that is neither phone- nor email-shaped
    is only ever a name."""
    q = (query or "").strip()
    bare = PHONE_STRIP.sub("", q)
    if PHONE_E164.match(bare) or PHONE_BARE.match(bare):
        return "phone", phone_key(bare)
    if "@" in q:
        return "email", q.lower()
    return "name", norm_name(q)


# ----------------------------------------------------------------------------- stores
def _ro_uri(path):
    return "file:%s?mode=ro" % path.replace("%", "%25").replace("?", "%3f").replace("#", "%23")


def ro_connect(path):
    return sqlite3.connect(_ro_uri(path), uri=True)


def mesh_path():
    return CFG.store_path("mesh.db")


def snapshot_path():
    return CFG.store_path("imessage", "snapshot.db")


def mail_path():
    return CFG.mail_root()


def load_identities(path=None):
    """Every identity as {identity_id, name, emails, phones}. Raises NOTFOUND naming the path
    when the mesh or its identity table is absent."""
    path = path or mesh_path()
    if not os.path.exists(path):
        raise MeshError("NOTFOUND", "no mesh at %s" % path, "run exo-mesh-resolve", path=path)
    con = ro_connect(path)
    try:
        rows = con.execute("SELECT id, name, emails, phones FROM identity ORDER BY id").fetchall()
    except sqlite3.DatabaseError:
        raise MeshError("NOTFOUND", "no identity table in %s" % path, "run exo-mesh-resolve", path=path)
    finally:
        con.close()
    return [{"identity_id": i, "name": n or "",
             "emails": sorted(set(e.lower() for e in (em or "").split() if "@" in e)),
             "phones": sorted(set(p for p in (ph or "").split() if phone_key(p)))}
            for i, n, em, ph in rows]


def resolve_person(query, identities):
    """The one identity `query` names, by the three tiers. Raises MeshError: USAGE for an empty
    query, AMBIGUOUS (with candidates) for more than one match at the deciding tier, NOTFOUND
    for none at any tier."""
    q = (query or "").strip()
    if not q:
        raise MeshError("USAGE", "no person given", "pass a full name, an exact email or a phone number")
    tier, key = query_tier(q)
    tiers = []
    if tier == "phone":
        tiers.append(("phone", lambda p: any(phone_key(x) == key for x in p["phones"])))
    if "@" in q:
        em = q.lower()
        tiers.append(("email", lambda p: em in p["emails"]))
    nn = norm_name(q)
    if nn:
        tiers.append(("name", lambda p: norm_name(p["name"]) == nn))
    for name, match in tiers:
        hit = [p for p in identities if match(p)]
        if len(hit) == 1:
            return dict(hit[0], matched_by=name)
        if len(hit) > 1:
            raise MeshError("AMBIGUOUS", "%r matches %d identities by %s" % (q, len(hit), name),
                            "pass one of their emails or phone numbers to choose",
                            candidates=[{"identity_id": p["identity_id"], "name": p["name"],
                                         "emails": p["emails"], "phones": p["phones"]}
                                        for p in sorted(hit, key=lambda p: p["identity_id"])])
    raise MeshError("NOTFOUND", "no identity matches %r by phone, email or full name" % q,
                    "pass a full name, an exact email or a phone number; "
                    "exo-mail contact search <text> lists near matches")


# ----------------------------------------------------------------------------- time
class Zone(object):
    """Calendar arithmetic in one timezone without the wall clock. name=None is the process's
    local zone (TZ); "UTC" or an IANA name is that zone."""

    def __init__(self, name=None):
        self.name = name
        self.tz = None
        if name:
            if name.upper() in ("UTC", "Z", "GMT"):
                self.tz = datetime.timezone.utc
            else:
                try:
                    from zoneinfo import ZoneInfo
                    self.tz = ZoneInfo(name)
                except Exception:
                    raise MeshError("USAGE", "unknown timezone: %s" % name,
                                    "an IANA name such as UTC or America/Los_Angeles")

    def parts(self, t):
        """(date ordinal, weekday Mon=0, hour) of epoch second t in this zone."""
        if self.tz is not None:
            dt = datetime.datetime.fromtimestamp(t, self.tz)
            return dt.toordinal(), dt.weekday(), dt.hour
        lt = time.localtime(t)
        return datetime.date(lt.tm_year, lt.tm_mon, lt.tm_mday).toordinal(), lt.tm_wday, lt.tm_hour

    def effective_name(self):
        """The zone actually in force, for an envelope to report: the name it was given, or --
        when none was -- the process's TZ environment variable, or "local" when even that is
        unset. Never reads the clock; this names a zone, not an instant."""
        return self.name or os.environ.get("TZ") or "local"

    def day_start(self, ordinal):
        """The epoch second at which the local calendar day `ordinal` begins."""
        d = datetime.date.fromordinal(ordinal)
        if self.tz is not None:
            return int(datetime.datetime(d.year, d.month, d.day, tzinfo=self.tz).timestamp())
        return int(time.mktime((d.year, d.month, d.day, 0, 0, 0, 0, 0, -1)))


def iso_day(ordinal):
    return datetime.date.fromordinal(ordinal).isoformat() if ordinal else None


def utc_day(t):
    return time.strftime("%Y-%m-%d", time.gmtime(t)) if t is not None else None


def parse_duration(s, flag):
    m = DUR.match((s or "").strip())
    if not m:
        raise MeshError("USAGE", "%s: expected a duration like 12h, 90d or 2w, or a date "
                        "YYYY-MM-DD; got %r" % (flag, s), "durations: m h d w; dates: YYYY-MM-DD")
    return int(m.group(1)) * UNIT[m.group(2).lower()]


def parse_day(s, flag):
    """A calendar day YYYY-MM-DD as a date ordinal."""
    m = ISO_DAY.match((s or "").strip())
    if not m:
        raise MeshError("USAGE", "%s: expected a date YYYY-MM-DD; got %r" % (flag, s),
                        "dates are YYYY-MM-DD")
    try:
        return datetime.date(*(int(x) for x in m.groups())).toordinal()
    except ValueError:
        raise MeshError("USAGE", "%s: not a calendar date: %r" % (flag, s), "dates are YYYY-MM-DD")


def resolve_window(since, until, zone, newest):
    """(lo, hi): inclusive epoch seconds, either may be None.

    until  a date ends at that day's last second in `zone`; absent, it is `newest` (the
           person's newest item or reaction), never now.
    since  a duration is measured back from until; a date starts at that day's first second;
           absent (None), the window reaches back to the first item.
    With no until and no newest item there is nothing to anchor on: (None, None)."""
    if until:
        hi = zone.day_start(parse_day(until, "--until") + 1) - 1
    else:
        hi = newest
    lo = None
    if since:
        if ISO_DAY.match(since.strip()):
            lo = zone.day_start(parse_day(since, "--since"))
            if until and lo > hi:
                raise MeshError("USAGE", "--since %s is after --until %s" % (since, until),
                                "a window runs forwards: --since before --until")
        else:
            dur = parse_duration(since, "--since")
            lo = (hi - dur) if hi is not None else None
    if hi is None:
        return None, None
    return lo, hi


def in_window(t, lo, hi):
    return hi is not None and t <= hi and (lo is None or t >= lo)


# ----------------------------------------------------------------------------- mail
def _nm(*args):
    """(ok, stdout) of a read-only notmuch subcommand."""
    try:
        r = subprocess.run([CFG.notmuch_bin()] + list(args), capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, timeout=300)
    except Exception:
        return False, ""
    return r.returncode == 0, r.stdout


def _nm_quote(s):
    return '"%s"' % s.replace('"', '""')


def _addrs(*headers):
    return set(a.lower() for _, a in email.utils.getaddresses([h for h in headers if h]) if "@" in a)


def _walk_messages(node, out):
    """Collect the message dicts in notmuch show JSON: threads -> [message|null, replies]."""
    if isinstance(node, dict):
        if "headers" in node and "id" in node:
            out.append(node)
        return
    if isinstance(node, list):
        for x in node:
            _walk_messages(x, out)


def mail_items(person, selves):
    """(available, items) — the person's mail as items, without bodies. available is False when
    the local mail index cannot be read."""
    emails = [e for e in person["emails"] if e not in selves]
    if not emails:
        ok, _ = _nm("count", "--", "*")
        return ok, []
    q = " or ".join("from:%s or to:%s" % (_nm_quote(e), _nm_quote(e)) for e in emails)
    ok, out = _nm("show", "--format=json", "--body=false", "--entire-thread=false", "--", q)
    if not ok:
        return False, []
    try:
        tree = json.loads(out or "[]")
    except ValueError:
        return False, []
    msgs = []
    _walk_messages(tree, msgs)
    mine = set(emails)
    items, seen = [], set()
    for m in msgs:
        mid = m.get("id") or ""
        if not m.get("match", True) or m.get("excluded") or mid in seen:
            continue
        t = int(m.get("timestamp") or 0)
        if t <= 0:
            continue
        h = m.get("headers") or {}
        frm = _addrs(h.get("From"))
        if frm & mine:
            direction = "received"
        elif frm & selves and _addrs(h.get("To"), h.get("Cc"), h.get("Bcc")) & mine:
            direction = "sent"
        else:
            continue
        seen.add(mid)
        items.append({"channel": "mail", "direction": direction, "t": t,
                      "sort": (t, 0, 0, mid), "id": mid, "subject": h.get("Subject") or ""})
    return True, items


_QUOTE_CUTS = [re.compile(p, re.I) for p in (
    r"\n[ \t]*On [^\n]*?(?:\n[^\n]*?)?wrote:[ \t]*(?:\n|$)",
    r"\n[ \t]*>",
    r"\n[ \t]*-{2,}[ \t]*Original Message[ \t]*-{2,}",
    r"\n[ \t]*-{2,}[ \t]*Forwarded message[ \t]*-{2,}",
    r"\n[ \t]*_{8,}[ \t]*\n",
    r"\n[ \t]*From:[^\n]*\n[ \t]*(?:Sent|Date):",
)]


def strip_quoted(txt):
    """The part of a plain-text body above its quoted history."""
    txt = "\n" + (txt or "").replace("\r\n", "\n")
    cut = len(txt)
    for rx in _QUOTE_CUTS:
        m = rx.search(txt)
        if m:
            cut = min(cut, m.start())
    return txt[:cut]


def _body_text(parts):
    """(plain, html) — the first text/plain and the first text/html content in a body tree."""
    plain = htm = None
    stack = list(parts or [])[::-1]
    while stack:
        p = stack.pop()
        if not isinstance(p, dict):
            continue
        c = p.get("content")
        ct = (p.get("content-type") or "").lower()
        if isinstance(c, list):
            stack.extend(c[::-1])
        elif isinstance(c, str):
            if ct == "text/plain" and plain is None:
                plain = c
            elif ct == "text/html" and htm is None:
                htm = c
    return plain, htm


def snippet_of(parts):
    plain, htm = _body_text(parts)
    if plain is None and htm is not None:
        htm = re.sub(r"(?is)<(style|script)\b.*?</\1\s*>", " ", htm)
        htm = re.sub(r"(?i)<br\s*/?>|</p\s*>|</div\s*>", "\n", htm)
        plain = html.unescape(re.sub(r"<[^>]+>", " ", htm))
    return " ".join(strip_quoted(plain or "").split())[:SNIPPET_CHARS]


def fetch_mail_details(items):
    """Fill thread and snippet on the given mail items, in place: two notmuch reads per batch
    of message ids, for the selected items only."""
    by_id = dict((it["id"], it) for it in items if it["channel"] == "mail")
    for it in by_id.values():
        it.setdefault("thread", None)
        it.setdefault("snippet", "")
    ids = sorted(by_id)
    for i in range(0, len(ids), ID_BATCH):
        q = " or ".join("id:%s" % _nm_quote(x) for x in ids[i:i + ID_BATCH])
        ok, out = _nm("search", "--format=json", "--output=summary", "--exclude=false", "--", q)
        if ok:
            try:
                for th in json.loads(out or "[]"):
                    matched = (th.get("query") or [None])[0] or ""
                    for a, b in NM_ID.findall(matched):
                        mid = a.replace('""', '"') if a else b
                        if mid in by_id:
                            by_id[mid]["thread"] = th.get("thread")
            except ValueError:
                pass
        ok, out = _nm("show", "--format=json", "--entire-thread=false", "--include-html",
                      "--exclude=false", "--", q)
        if ok:
            try:
                msgs = []
                _walk_messages(json.loads(out or "[]"), msgs)
                for m in msgs:
                    it = by_id.get(m.get("id"))
                    if it is not None and m.get("body") is not None:
                        it["snippet"] = snippet_of(m.get("body"))
            except ValueError:
                pass
    return items


# ----------------------------------------------------------------------------- texts
def _target(guid):
    """The message a tapback points at: its guid without the part prefix (p:N/ or bp:)."""
    return re.sub(r"^(?:p:\d+/|bp:)", "", guid or "")


def text_items(person, path):
    """(available, items, reactions, error). items are the person's messages in one-to-one
    chats; reactions are the tapback rows kept apart: {side, type, target, t, sort}."""
    if not os.path.exists(path):
        return False, [], [], None
    keys = set(person["emails"]) | set(phone_key(p) for p in person["phones"])
    keys.discard("")
    try:
        con = ro_connect(path)
    except sqlite3.Error as e:
        return False, [], [], str(e)[:160]
    try:
        imsg_text.register(con)
        part = {}
        for cid, h in con.execute("SELECT chj.chat_id, h.id FROM chat_handle_join chj "
                                  "JOIN handle h ON h.ROWID = chj.handle_id"):
            part.setdefault(cid, set()).add(h)
        chats = dict((cid, next(iter(hs))) for cid, hs in part.items()
                     if len(hs) == 1 and handle_key(next(iter(hs))) in keys)
        if not chats:
            return True, [], [], None

        def col(name):
            return ("m.%s" % name) if CFG.col_of(con, "message", name) else "NULL"
        amt = "coalesce(%s, 0)" % col("associated_message_type")
        sql = ("SELECT m.ROWID, m.date, m.is_from_me, %s, %s, coalesce(%s, 0), coalesce(%s, 0), "
               "CASE WHEN %s BETWEEN %d AND %d THEN NULL ELSE imsg_text(m.text, m.attributedBody) END, "
               "cmj.chat_id FROM chat_message_join cmj JOIN message m ON m.ROWID = cmj.message_id "
               "WHERE cmj.chat_id IN (%s)" % (
                   amt, col("associated_message_guid"), col("date_read"), col("date_edited"),
                   amt, REACTION_LO, REACTION_HI, ",".join("?" * len(chats))))
        items, reactions, seen = [], [], set()
        for rowid, date, fromme, typ, target, dread, dedit, txt, cid in con.execute(sql, sorted(chats)):
            if rowid in seen or not date:
                continue
            seen.add(rowid)
            ns = int(date) if int(date) > 10 ** 12 else int(date) * NS   # pre-2017 stores kept seconds
            t = APPLE_EPOCH + ns // NS
            key = (t, ns % NS, 1, rowid)
            side = "owner" if fromme else "other"
            if REACTION_LO <= int(typ or 0) <= REACTION_HI:
                reactions.append({"side": side, "type": int(typ), "target": _target(target),
                                  "t": t, "sort": key})
                continue
            it = {"channel": "texts", "direction": "sent" if fromme else "received", "t": t,
                  "sort": key, "text": txt or "", "handle": chats[cid], "edited": int(dedit or 0) > 0,
                  "read_latency_s": None}
            if fromme and int(dread or 0) > 0:
                rns = int(dread) if int(dread) > 10 ** 12 else int(dread) * NS
                it["read_latency_s"] = (rns - ns) / float(NS)
            items.append(it)
        return True, items, reactions, None
    except sqlite3.Error as e:
        return False, [], [], str(e)[:160]
    finally:
        con.close()


# ----------------------------------------------------------------------------- the timeline
def load_timeline(person, channels=("mail", "texts")):
    """{items, reactions, sources, newest}: every item of the person on the requested channels,
    oldest first; the reactions kept apart; sources.<channel> = {available, path, requested}
    for BOTH channels (a channel that was not requested is not read, and its availability is
    null, not false); and newest, the latest instant of any item or reaction, which is where a
    window without --until ends."""
    selves = set(e.lower() for e in CFG.self_emails())
    items, reactions = [], []
    sources = {"mail": {"available": None, "path": mail_path(), "requested": "mail" in channels},
               "texts": {"available": None, "path": snapshot_path(), "requested": "texts" in channels}}
    if "mail" in channels:
        ok, mail = mail_items(person, selves)
        sources["mail"]["available"] = ok
        items += mail
    if "texts" in channels:
        ok, texts, reactions, err = text_items(person, sources["texts"]["path"])
        sources["texts"]["available"] = ok
        if err:
            sources["texts"]["error"] = err
        items += texts
    items.sort(key=lambda it: it["sort"])
    reactions.sort(key=lambda r: r["sort"])
    stamps = [x[-1]["t"] for x in (items, reactions) if x]
    return {"items": items, "reactions": reactions, "sources": sources,
            "newest": max(stamps) if stamps else None}
