#!/usr/bin/env bash
# public-gate.sh — scan a tree that is about to become public for content that must not be
# published. Also ships inside the public repository as tests/publish-checks.sh,
# where CI runs it on every push and pull request.
#
# TWO TIERS, ONE SCANNER.
#   built-in   = pattern CLASSES only: path shapes, email shapes, phone and key shapes, and
#                left-over TODO markers. This file contains no value that identifies anyone,
#                so the file itself can be public.
#   --patterns = VALUES as data — names, numbers, handles, house vocabulary — kept in a file
#                that never ships. Format: severity<TAB>label<TAB>perl-regex. `#` comments allowed.
#
# The scanner is Perl so the same regex dialect works on macOS (BSD grep has no \b) and on
# Linux CI. Binary files and the usual build/cache dirs are skipped, and so is this script
# (under either name): it legitimately contains every class as a regex and as a self-test sample.
#
# USAGE
#   public-gate.sh --root <dir> [--patterns <tsv>] [--allow <file>] [--quiet]
#   public-gate.sh --self-test
#
# EXIT  0 = no ERROR hits · 1 = ERROR hits (or self-test failure) · 2 = usage / unreadable input
#
# --allow <file>: one Perl regex per line, matched against the hit line `path:line: content`;
# matching hits are suppressed and counted. --self-test builds a temp tree containing one
# SYNTHETIC sample per built-in class and asserts every class fires — a gate that has silently
# stopped matching is the failure this exists to catch.

set -uo pipefail

ROOT="" ; PATTERNS="" ; ALLOW="" ; QUIET=0 ; SELFTEST=0
while [ $# -gt 0 ]; do
  case "$1" in
    --root)      ROOT="$2"; shift 2 ;;
    --patterns)  PATTERNS="$2"; shift 2 ;;
    --allow)     ALLOW="$2"; shift 2 ;;
    --quiet)     QUIET=1; shift ;;
    --self-test) SELFTEST=1; shift ;;
    -h|--help)   sed -n '2,26p' "$0"; exit 0 ;;
    *) echo "public-gate: unknown argument: $1" >&2; exit 2 ;;
  esac
done

# ---------------------------------------------------------------------------------------------
# Built-in classes. Format: severity<TAB>label<TAB>regex. Add a class here only if it carries
# no identifying value; a value belongs in the --patterns file.
# ---------------------------------------------------------------------------------------------
BUILTIN=$(cat <<'EOF'
ERROR	abs-home-path	(?<![\w./-])/(Users|home)/[A-Za-z][\w.-]*
ERROR	icloud-path	iCloud~md~obsidian
ERROR	workspace-slug	-Users-[A-Za-z0-9_-]+
ERROR	gmail-address	[A-Za-z0-9._%+-]+@gmail\.com
ERROR	phone-shape	(?<![\d-])(\+?1[ .-]?)?\(?[0-9]{3}\)?[ .-][0-9]{3}[ .-][0-9]{4}(?![\d-])
ERROR	secret-shape	\b(AKIA[0-9A-Z]{16}|sk-ant-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{32,}|ghp_[A-Za-z0-9]{36}|xox[abp]-[0-9A-Za-z-]{10,})\b
WARN	todo-marker	\b(TODO|FIXME|TBD|XXX)\b
EOF
)

run_scan() {  # $1=root  $2=patterns-file-or-empty  $3=allow-file-or-empty
  BUILTIN_PATTERNS="$BUILTIN" perl - "$1" "$2" "$3" <<'PERL'
use strict; use warnings; use File::Find;
my ($root, $pfile, $afile) = @ARGV;
my @rules;  # [severity, label, qr]
for my $line (split /\n/, $ENV{BUILTIN_PATTERNS}) {
  next if $line =~ /^\s*(#|$)/;
  my ($sev, $label, $re) = split /\t/, $line, 3;
  push @rules, [$sev, $label, qr/$re/];
}
if ($pfile ne '') {
  open my $fh, '<', $pfile or do { print STDERR "public-gate: cannot read patterns file $pfile\n"; exit 2 };
  while (my $line = <$fh>) {
    chomp $line; next if $line =~ /^\s*(#|$)/;
    my ($sev, $label, $re) = split /\t/, $line, 3;
    unless (defined $re && $re ne '') { print STDERR "public-gate: bad patterns row (need severity<TAB>label<TAB>regex): $line\n"; exit 2 }
    push @rules, [$sev, $label, qr/$re/];
  }
  close $fh;
}
my @allow;
if ($afile ne '') {
  open my $fh, '<', $afile or do { print STDERR "public-gate: cannot read allow file $afile\n"; exit 2 };
  while (my $line = <$fh>) { chomp $line; next if $line =~ /^\s*(#|$)/; push @allow, qr/$line/; }
  close $fh;
}
my %skipdir = map { $_ => 1 } qw(.git out .venv node_modules __pycache__ .pytest_cache);
my ($errors, $warns, $allowed, $files) = (0, 0, 0, 0);
find({ no_chdir => 1, wanted => sub {
  my $p = $File::Find::name;
  if (-d $p) { my $b = (split m{/}, $p)[-1]; $File::Find::prune = 1 if $skipdir{$b} && $p ne $root; return; }
  return unless -f $p; return if -B $p;
  # Never scan this scanner (under either of its names): it carries every class as a regex.
  return if $p =~ m{/(public-gate\.sh|publish-checks\.sh)$};
  $files++;
  my $rel = $p; $rel =~ s{^\Q$root\E/?}{};
  open my $fh, '<', $p or return;
  my $n = 0;
  while (my $line = <$fh>) {
    $n++; chomp $line;
    for my $r (@rules) {
      next unless $line =~ $r->[2];
      my $hit = "$rel:$n: $line";
      if (grep { $hit =~ $_ } @allow) { $allowed++; next; }
      if ($r->[0] eq 'ERROR') { $errors++ } else { $warns++ }
      printf "%-5s %-20s %s\n", $r->[0], $r->[1], substr($hit, 0, 220) unless $ENV{GATE_QUIET};
    }
  }
  close $fh;
}}, $root);
print "public-gate: files=$files errors=$errors warnings=$warns allowed=$allowed rules=" . scalar(@rules) . "\n";
exit($errors ? 1 : 0);
PERL
}

if [ "$SELFTEST" -eq 1 ]; then
  T=$(mktemp -d "${TMPDIR:-/tmp}/public-gate-selftest.XXXXXX")
  [ -n "$T" ] && [ -d "$T" ] || { echo "SELF-TEST FAIL: mktemp produced no directory" >&2; exit 2; }
  mkdir -p "$T/tree/out" "$T/tree/docs"
  # Every value below is SYNTHETIC. One line per built-in class, in order.
  cat > "$T/tree/docs/sample.md" <<'EOF'
path: /Users/example/dev/thing
icloud: iCloud~md~obsidian/Documents/x
slug: -Users-example-dev-thing
mail: someone@gmail.com
phone: 555-123-4567
key: AKIAAAAAAAAAAAAAAAAA
todo: TODO fix this
EOF
  echo "this must never be scanned: /Users/example/out" > "$T/tree/out/ignored.txt"
  OUT=$(run_scan "$T/tree" "" "")
  rc=$?
  echo "$OUT"
  fail=0
  for label in abs-home-path icloud-path workspace-slug gmail-address phone-shape secret-shape todo-marker; do
    echo "$OUT" | grep -q " $label " || { echo "SELF-TEST FAIL: class '$label' produced no hit"; fail=1; }
  done
  echo "$OUT" | grep -q 'out/ignored.txt' && { echo "SELF-TEST FAIL: out/ was scanned"; fail=1; }
  [ "$rc" -eq 1 ] || { echo "SELF-TEST FAIL: expected exit 1 on a tree with ERROR hits, got $rc"; fail=1; }
  rm -rf "$T"
  if [ "$fail" -eq 0 ]; then echo "public-gate self-test: every class fires, out/ skipped, exit code correct"; exit 0; fi
  exit 1
fi

[ -n "$ROOT" ] || { echo "public-gate: --root <dir> is required (or --self-test)" >&2; exit 2; }
[ -d "$ROOT" ] || { echo "public-gate: root is not a directory: $ROOT" >&2; exit 2; }
ROOT="$(cd "$ROOT" && pwd -P)"
if [ -n "$PATTERNS" ] && [ ! -r "$PATTERNS" ]; then echo "public-gate: patterns file unreadable: $PATTERNS" >&2; exit 2; fi
if [ -n "$ALLOW" ] && [ ! -r "$ALLOW" ]; then echo "public-gate: allow file unreadable: $ALLOW" >&2; exit 2; fi
GATE_QUIET=$QUIET run_scan "$ROOT" "$PATTERNS" "$ALLOW"
