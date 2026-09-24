"""imsg_text — the words of an iMessage/SMS/RCS row, including words held only in its packed body.

WHY THIS EXISTS. Messages keeps a row's words in two places: the plain `text` column and
`attributedBody`, an archived NSAttributedString. Newer macOS releases often write only the
second, so many rows have an empty `text` and carry their words only in `attributedBody`.
Anything that reads `text` alone (phrase search, a conversation, relationship counts) misses
them.

THE FORMAT. `attributedBody` is Apple's `typedstream` (NSArchiver), little-endian, magic
`\\x04\\x0bstreamtyped`. The string sits in the first NSString class record: after the class
name come its version byte, its superclass (usually a back-reference to NSObject), then the
type encoding `\\x84\\x01+` and the length-prefixed UTF-8:

    0x00-0x7f        the length itself, one byte
    0x81 + 2 bytes   little-endian length
    0x82 + 4 bytes   little-endian length

Every other lead byte is a typedstream tag or a negative number, so it cannot start a length.
This reads the format by that one rule; it is not a general typedstream parser, and the
attribute runs after the string are ignored.

THE FAILURE CONTRACT. `decode()` never raises. A body with no header, no NSString record, no
type marker, a bad or overrunning length, or invalid UTF-8 returns None. The caller keeps the
row with empty text and still counts it: one bad row never fails a sync or a query. The format
is reverse-engineered, so a future macOS may change it: after an upgrade, measure the share of
packed bodies that decode, against a copy of the store rather than the live one.

What comes out is the message as Messages stored it, including U+FFFC where an attachment sits.
It is untrusted content, so whoever surfaces it labels it that way.

Stdlib only, like exomail_config: the analysis commands and the test suites may load this under
the system python3 rather than the venv.

    import imsg_text
    imsg_text.decode(body)            -> str | None
    imsg_text.message_text(text, body) -> str   (never None)
    imsg_text.register(con)           # SQL: imsg_text(text, attributedBody)
"""

__all__ = ["decode", "message_text", "register"]

MAGIC = b"\x04\x0bstreamtyped"
NSSTRING = b"\x08NSString"   # the class record: its name, prefixed by its length
PLUS = b"\x84\x01+"          # a new type encoding "+": a length-prefixed byte string follows
MARKER_WINDOW = 32           # the "+" marker must sit this close after the class record
INT2, INT4 = 0x81, 0x82      # typedstream's 2- and 4-byte integer tags


def decode(body):
    """The text of an `attributedBody`, or None when it cannot be read. Never raises."""
    if not isinstance(body, (bytes, bytearray, memoryview)):
        return None
    b = bytes(body)
    if not b.startswith(MAGIC):
        return None
    at = b.find(NSSTRING, len(MAGIC))
    if at < 0:
        return None
    start = at + len(NSSTRING)
    mark = b.find(PLUS, start, start + MARKER_WINDOW)
    if mark < 0:
        return None
    i = mark + len(PLUS)
    if i >= len(b):
        return None
    lead = b[i]
    if lead < 0x80:
        n, i = lead, i + 1
    elif lead == INT2 and i + 3 <= len(b):
        n, i = int.from_bytes(b[i + 1:i + 3], "little"), i + 3
    elif lead == INT4 and i + 5 <= len(b):
        n, i = int.from_bytes(b[i + 1:i + 5], "little"), i + 5
    else:
        return None
    if i + n > len(b):
        return None
    try:
        return b[i:i + n].decode("utf-8")
    except UnicodeDecodeError:
        return None


def message_text(text, body):
    """The text a message shows: its `text` column when that holds any, else the words decoded
    from its packed body, else "". Never None, so a row always survives with a string."""
    if isinstance(text, str) and text:
        return text
    return decode(body) or ""


def register(con, name="imsg_text"):
    """Make `message_text` callable from SQL on `con`, as name(text, attributedBody).

    Works on a read-only connection, so a query can filter or index on recovered text:
        imsg_text.register(con)
        con.execute("select ROWID, imsg_text(text, attributedBody) from message")
    """
    con.create_function(name, 2, message_text, deterministic=True)
    return con
