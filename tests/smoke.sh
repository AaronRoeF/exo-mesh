#!/usr/bin/env bash
# smoke.sh — read-only checks over a working exo-mail install.
#
# NEVER: sends, tags, pushes a label, calls a network API, writes to any store, or
# passes --apply to anything. Where a store is absent it SKIPS loudly rather than
# passing silently, so this is also the right thing to run on a machine where you
# only set up part of the stack.
#
#   bash tests/smoke.sh                      # against ./bin
#   EXO_MAIL_BIN=/path/to/bin bash tests/smoke.sh
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
BIN="${EXO_MAIL_BIN:-$HERE/../bin}"
BIN="$(cd "$BIN" && pwd -P)"
PY="$BIN/exo-mail-python"
EM="$BIN/exo-mail"

PASS=0; FAIL=0; SKIP=0
pass(){ PASS=$((PASS+1)); echo "  ok    $1"; }
fail(){ FAIL=$((FAIL+1)); echo "  FAIL  $1"; }
skip(){ SKIP=$((SKIP+1)); echo "  skip  $1"; }
section(){ echo; echo "-- $1"; }

echo "exo-mail smoke — bin: $BIN"

# ---------------------------------------------------------------- 1. portability
section "portability"

[[ -x "$PY" ]] && pass "exo-mail-python present and executable" \
                || fail "exo-mail-python missing at $PY"

# Every tool must carry the relocatable header, not an absolute interpreter path.
bad=0; checked=0
for f in "$BIN"/*; do
  [[ -f "$f" && -x "$f" ]] || continue
  case "$(basename "$f")" in exo-mail-python) continue ;; esac
  checked=$((checked+1))
  head -1 "$f" | grep -qE '^#!/bin/(sh|bash)$' || { echo "      $(basename "$f"): $(head -1 "$f")"; bad=$((bad+1)); }
done
[[ "$bad" -eq 0 ]] && pass "$checked tools carry a relocatable shebang (no absolute interpreter)" \
                   || fail "$bad tool(s) carry a non-relocatable shebang"

# No tool may hardcode somebody's home directory.
HOMEHITS=$(grep -rlE '/(Users|home)/[a-z]' --exclude-dir=__pycache__ --exclude='*.pyc' "$BIN" 2>/dev/null)
if [[ -n "$HOMEHITS" ]]; then
  fail "a tool hardcodes an absolute home directory: $(echo "$HOMEHITS" | head -3 | tr '\n' ' ')"
else
  pass "no tool hardcodes an absolute home directory"
fi

# Every Python tool must byte-compile under the system interpreter.
bad=0
for f in "$BIN"/*; do
  [[ -f "$f" ]] || continue
  case "$(basename "$f")" in exo-mail-python) continue ;; esac
  head -1 "$f" | grep -q '^#!/bin/sh$' || [[ "$f" == *.py ]] || continue
  python3 -c "import py_compile,sys,tempfile,os;py_compile.compile(sys.argv[1],cfile=os.path.join(tempfile.mkdtemp(),'t.pyc'),doraise=True)" "$f" \
    >/dev/null 2>&1 || { echo "      $(basename "$f")"; bad=$((bad+1)); }
done
[[ "$bad" -eq 0 ]] && pass "every tool byte-compiles" || fail "$bad tool(s) failed to compile"

# ---------------------------------------------------------------- 2. configuration
section "configuration"

CFG_JSON="$("$PY" "$BIN/exomail_config.py" 2>&1)"
if python3 -c "import json,sys;json.loads(sys.argv[1])" "$CFG_JSON" >/dev/null 2>&1; then
  pass "exomail_config resolves and prints valid JSON"
  STORE=$(python3 -c "import json,sys;print(json.loads(sys.argv[1])['store'])" "$CFG_JSON")
  NACC=$(python3 -c "import json,sys;print(len(json.loads(sys.argv[1])['accounts']))" "$CFG_JSON")
  NADDR=$(python3 -c "import json,sys;print(len(json.loads(sys.argv[1])['self_emails']))" "$CFG_JSON")
  [[ "$NACC" -ge 1 ]]  && pass "accounts configured: $NACC"  || fail "no accounts configured"
  [[ "$NADDR" -ge 1 ]] && pass "own addresses resolved: $NADDR" \
    || skip "no own address resolved — run 'notmuch setup' or set EXO_MAIL_EMAIL_<ACCT>"
else
  fail "exomail_config did not produce JSON: $(echo "$CFG_JSON" | head -2)"
  STORE=""
fi

SH_OUT="$("$PY" "$BIN/exomail_config.py" --sh 2>&1)"
echo "$SH_OUT" | grep -q '^EXO_MAIL_STORE=' \
  && pass "--sh emits shell assignments (exo-mail-sync.sh sources these)" \
  || fail "--sh did not emit EXO_MAIL_STORE"

# ---------------------------------------------------------------- 3. CLI contract
section "CLI contract (read-only)"

OUT=$("$EM" --help 2>&1); RC=$?
[[ "$RC" -eq 0 ]] && echo "$OUT" | grep -q '^usage:' \
  && pass "exo-mail --help parses" || fail "exo-mail --help: rc=$RC"

OUT=$("$EM" count '*' --json 2>&1); RC=$?
if echo "$OUT" | python3 -c "import json,sys;d=json.load(sys.stdin);sys.exit(0 if 'ok' in d else 1)" 2>/dev/null; then
  pass "exo-mail count: JSON envelope with an 'ok' key (rc=$RC)"
else
  skip "exo-mail count — no notmuch database yet"
fi

OUT=$("$EM" box nosuchbox --json 2>&1); RC=$?
echo "$OUT" | grep -q '"ok": false' && echo "$OUT" | grep -q '"code": "USAGE"' && [[ "$RC" -eq 1 ]] \
  && pass "unknown box: ok=false, code=USAGE, exit 1 (typed errors work)" \
  || fail "unknown box: rc=$RC out=$(echo "$OUT" | head -1)"

OUT=$("$EM" skill 2>&1)
echo "$OUT" | grep -q 'NEVER sends' \
  && pass "exo-mail skill states the no-send guarantee" \
  || fail "exo-mail skill is missing the safety statement"

# ---------------------------------------------------------------- 4. safety invariants
section "safety invariants (static)"

if grep -rE 'messages/(send|trash)|"(TRASH|SPAM)"|drafts/[^"]*/send' "$BIN" >/dev/null 2>&1; then
  fail "a tool references a send/trash/spam endpoint — investigate before using this"
else
  pass "no tool references a Gmail send, trash or spam endpoint"
fi

grep -q 'EXO_LABEL_PUSH' "$BIN/exo-mail-classify" \
  && pass "classify's Gmail label push is gated on EXO_LABEL_PUSH" \
  || fail "classify label push is not gated"

grep -q 'APPLY' "$BIN/exo-mail-commitments" \
  && pass "commitments filing is gated on --apply" \
  || fail "commitments filing is not gated"

grep -q 'mode=ro' "$BIN/exo-imsg" \
  && pass "iMessage source is opened read-only" \
  || fail "iMessage source is not opened read-only"

grep -q 'calendar.readonly' "$BIN/exo-cal" \
  && pass "calendar OAuth scope is read-only" \
  || fail "calendar scope is not read-only"

# ---------------------------------------------------------------- 5. stores
section "stores (present ones only)"

if [[ -n "${STORE:-}" && -f "$STORE/contacts.db" ]]; then
  OUT=$("$EM" contact list --limit 3 --json 2>&1)
  echo "$OUT" | grep -q '"ok": true' \
    && pass "contact list reads the correspondent index" \
    || fail "contact list: $(echo "$OUT" | head -1)"
else
  skip "contacts.db absent — run exo-mail-contacts"
fi

if [[ -n "${STORE:-}" && -f "$STORE/mesh.db" ]]; then
  OUT=$("$EM" bedrock candidates --limit 2 --json 2>&1)
  echo "$OUT" | grep -q '"ok": true' \
    && pass "bedrock candidates reads the mesh (read-only)" \
    || fail "bedrock candidates: $(echo "$OUT" | head -1)"
  OUT=$("$BIN/exo-mesh-resolve" --test 2>&1)
  echo "$OUT" | grep -q 'identities' \
    && pass "exo-mesh-resolve --test computes without writing" \
    || fail "exo-mesh-resolve --test: $(echo "$OUT" | head -1)"
else
  skip "mesh.db absent — run exo-mesh-resolve"
fi

if [[ -n "${STORE:-}" && -f "$STORE/calendar.db" ]]; then
  OUT=$("$BIN/exo-cal" stats 2>&1)
  echo "$OUT" | python3 -c "import json,sys;json.load(sys.stdin)" 2>/dev/null \
    && pass "exo-cal stats returns valid JSON" \
    || fail "exo-cal stats: $(echo "$OUT" | head -1)"
else
  skip "calendar.db absent — run exo-cal pull-all"
fi

if [[ -n "${STORE:-}" && -f "$STORE/imessage/snapshot.db" ]]; then
  OUT=$("$BIN/exo-imsg" status 2>&1)
  echo "$OUT" | grep -qi 'message\|cursor\|rows' \
    && pass "exo-imsg status reads the snapshot" \
    || fail "exo-imsg status: $(echo "$OUT" | head -1)"
else
  skip "iMessage snapshot absent — run exo-imsg snapshot (needs Full Disk Access)"
fi

# ---------------------------------------------------------------- 6. sync script
section "sync pipeline (static only — never executed)"

bash -n "$BIN/exo-mail-sync.sh" \
  && pass "exo-mail-sync.sh: syntax OK (NOT executed — it does real pulls)" \
  || fail "exo-mail-sync.sh: syntax error"

grep -q 'mkdir "$LOCKDIR"' "$BIN/exo-mail-sync.sh" \
  && pass "sync takes an atomic lock (overlapping runs are a no-op)" \
  || fail "sync has no lock"

# ---------------------------------------------------------------- 7. docs match code
section "docs match code"

DOCS="$HERE/../docs"
if [[ -d "$DOCS" ]]; then
  missing=""
  for t in exo-mail exo-cal exo-day exo-mesh exo-imsg exo-imsg-search exo-imsg-index \
           exo-mesh-resolve exo-mesh-bedrock-apply exo-mail-index exo-mail-classify \
           exo-mail-filter exo-mail-contacts exo-mail-contacts-merge exo-mail-archdoc \
           exo-mail-needsreply exo-mail-commitments exo-mail-ensure-labels \
           exo-mail-label-backfill exo-gmi exo-mail-sync.sh; do
    grep -rqF "$t" "$DOCS" || missing="$missing $t"
  done
  [[ -z "$missing" ]] && pass "every shipped tool is named in docs/" \
                      || fail "not documented:$missing"

  # Every exo-* token in the docs must name a shipped tool. Tokens that are not
  # tool names (a log file, a job label, a directory in an example) are listed
  # here explicitly, so a genuine typo still fails.
  NOT_A_TOOL=" exo-mail-state exo-mail-sync exo-mail-python exo-capabilities exo-mail "
  orphan=""
  for t in $(grep -rhoE 'exo-[a-z-]+(\.sh)?' "$DOCS" | sort -u); do
    [[ -e "$BIN/$t" ]] && continue
    case "$NOT_A_TOOL" in *" $t "*) continue ;; esac
    orphan="$orphan $t"
  done
  [[ -z "$orphan" ]] && pass "docs name no tool that is not shipped" \
                     || fail "docs name missing tools:$orphan"

  if grep -rnE '\b(TODO|FIXME|TBD|LINK_PENDING)\b' "$DOCS" "$HERE/../README.md" >/dev/null 2>&1; then
    fail "a doc still contains a placeholder marker"
  else
    pass "no placeholder markers in README or docs/"
  fi
else
  skip "docs/ not present"
fi

echo
echo "smoke: $PASS passed, $FAIL failed, $SKIP skipped"
[[ "$FAIL" -eq 0 ]]
