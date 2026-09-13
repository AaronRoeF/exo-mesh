#!/bin/bash
# exo-mail recurring sync — pull-only, every account, incremental.
# Never pushes, never sends. Run it on ONE machine only: it is a single writer.
#
# Everything below resolves from exomail_config.py, so this script works from any
# checkout and honours the same env vars and config.env the Python tools do.
set -uo pipefail

BIN="${0%/*}"; [ "$BIN" = "$0" ] && BIN="."
BIN="$(cd "$BIN" && pwd -P)"
eval "$("$BIN/exo-mail-python" "$BIN/exomail_config.py" --sh)"

PY="$BIN/exo-mail-python"
export PATH="$EXO_MAIL_HOME/venv/bin:$(dirname "$EXO_NOTMUCH"):/usr/bin:/bin:/usr/sbin:/sbin"
LOG="${EXO_MAIL_SYNC_LOG:-$EXO_MAIL_HOME/sync.log}"
AUDIT="$EXO_MAIL_STORE/audit.jsonl"
LOCKDIR="$EXO_MAIL_STORE/.sync.lock.d"
NOTMUCH="$EXO_NOTMUCH"
# Soft cap on the whole mail tree, in MB. Over it, the log gets a ranked list of
# ways to reclaim space (it never deletes anything by itself).
CAP_MB="${EXO_MAIL_STORAGE_CAP_MB:-14336}"

mkdir -p "$EXO_MAIL_STORE"
# job-level lock (portable, atomic): mkdir succeeds only if not held
if ! mkdir "$LOCKDIR" 2>/dev/null; then echo "$(date '+%F %T') skip: previous sync still running" >>"$LOG"; exit 0; fi
trap 'rmdir "$LOCKDIR" 2>/dev/null' EXIT
ts(){ date -u '+%FT%TZ'; }

# Per-account Gmail query. EXO_GMI_QUERY_<ACCT> (upper-cased, - to _) overrides;
# the default drops chats, spam, trash and anything over 250K.
acct_query(){
  local up; up=$(printf '%s' "$1" | tr '[:lower:]-' '[:upper:]_')
  local var="EXO_GMI_QUERY_$up"
  printf '%s' "${!var:-${EXO_GMI_QUERY:--in:chats -in:spam -in:trash -larger:250K}}"
}

run(){
  local acct="$1" q t0 rc hid
  q=$(acct_query "$acct")
  t0=$(date +%s)
  ( cd "$EXO_MAIL_ROOT/$acct" && EXO_GMI_QUERY="$q" "$BIN/exo-gmi" pull ) >>"$LOG" 2>&1; rc=$?
  hid=$("$PY" -c "import json,sys;print(json.load(open(sys.argv[1])).get('last_historyId'))" \
        "$EXO_MAIL_ROOT/$acct/.state.gmailieer.json" 2>/dev/null)
  printf '{"at":"%s","action":"sync.pull","account":"%s","rc":%d,"secs":%d,"last_historyId":%s}\n' \
    "$(ts)" "$acct" "$rc" "$(( $(date +%s)-t0 ))" "${hid:-null}" >>"$AUDIT"
  return $rc
}

step(){  # step <label> <cmd...> — a failed step logs and never aborts the sync
  local label="$1"; shift
  "$@" >>"$LOG" 2>&1 || echo "$(date '+%F %T') $label step failed" >>"$LOG"
}

echo "=== $(date '+%F %T') sync start ===" >>"$LOG"

IFS=',' read -r -a ACCTS <<< "$EXO_MAIL_ACCOUNTS"
for acct in "${ACCTS[@]}"; do
  [ -d "$EXO_MAIL_ROOT/$acct" ] && run "$acct"
done
"$NOTMUCH" new >>"$LOG" 2>&1

# incremental semantic embed of new mail (skips already-embedded)
step index    "$BIN/exo-mail-index"
step calendar "$BIN/exo-cal" pull-all
step imessage "$BIN/exo-imsg" snapshot
step mesh-resolve "$BIN/exo-mesh-resolve"
EXO_LABEL_PUSH=1 "$BIN/exo-mail-classify" >>"$LOG" 2>&1 || echo "$(date '+%F %T') classify step failed" >>"$LOG"
step needs-reply "$BIN/exo-mail-needsreply"

# rebuild the correspondent index once a day (~2min; skip if <20h old)
CDB="$EXO_MAIL_STORE/contacts.db"
if [ ! -f "$CDB" ] || [ $(( $(date +%s) - $(stat -f %m "$CDB") )) -gt 72000 ]; then
  step mesh "$BIN/exo-mail-contacts"
fi

printf '{"at":"%s","action":"sync.index","total":%s}\n' "$(ts)" "$("$NOTMUCH" count '*')" >>"$AUDIT"
MB=$(du -sm "$EXO_MAIL_ROOT" | cut -f1)
printf '{"at":"%s","action":"sync.storage","mail_mb":%s}\n' "$(ts)" "$MB" >>"$AUDIT"
if [ "$MB" -gt "$CAP_MB" ]; then
  { echo "$(date '+%F %T') STORAGE: mail store ${MB}MB > ${CAP_MB}MB soft-cap. Ranked ways to reclaim:";
    "$BIN/exo-mail" storage --json 2>/dev/null | "$PY" -c "import json,sys
try:
  d=json.load(sys.stdin)['data']
  for r in d['recommendations'][:3]:
    print('    ~%dMB  %s  (%s)'%(r['reclaims_mb'],r['action'],r['how']))
except Exception: pass"; } >>"$LOG"
fi

# regenerate the architecture doc from the live tool surface
# (cheap; best-effort -- a failure here logs and never breaks the sync)
step archdoc "$BIN/exo-mail-archdoc"

# Copy the NON-reproducible state (hand-authored rules + manual corrections) into a
# directory you back up or version. The Maildir and the rebuildable .db files are
# deliberately NOT copied. Unset EXO_MAIL_STATE_BACKUP to skip this step.
STATE_BK="${EXO_MAIL_STATE_BACKUP:-}"
if [ -n "$STATE_BK" ]; then
  mkdir -p "$STATE_BK"
  for f in sender-rules.tsv mesh-suppress.tsv contacts-master-strip.tsv; do
    [ -f "$EXO_MAIL_STORE/$f" ] && cp "$EXO_MAIL_STORE/$f" "$STATE_BK/$f"
  done
  echo "$(date '+%F %T') state-backup: $(ls "$STATE_BK" | wc -l | tr -d ' ') files" >>"$LOG"
fi
echo "=== $(date '+%F %T') sync done (total $("$NOTMUCH" count '*')) ===" >>"$LOG"
