#!/usr/bin/env python3
"""OCR workbook standards linter.

Deterministic checker for OpenCyberRange workbook markdown. Encodes the
maintainer standards that previously lived in scattered feedback memories so a
fix run has a single, verifiable "done" gate: re-run with zero hard violations.

Scope: workbook markdown under Workbook/ and Workbook-Pentest/. lab.yaml is checked
by the sibling check_labyaml.py (read-only).

Rules
  HARD (fail the build, exit 1):
    unicode-dash       U+2013/U+2014 anywhere (breaks PowerShell + PDF gen)
    double-dash-prose  " -- " used as punctuation in prose (not in code)
    password-bang      "!" inside a credential/password value
    this-start         a prose sentence beginning with "This "
    broken-link        relative link/image target not found on disk
    link-url-path      directory/page URL link (ends "/"); breaks under
                       use_directory_urls -- use the ".md" target instead
  REVIEW (reported, do not fail unless --strict):
    flag-exposure      OCR{...} that looks like a concrete real flag value
    missing-admonition walkthrough file with command blocks but no kali/target
    fixed-path-prose   prose claiming a tool/wordlist "is available at /path"
    flag-no-submit-guidance  blank "**Flag:**" submission line with no flag
                       format/template or how-to-submit hint nearby

Usage
  check.py                         # scan Workbook/ and Workbook-Pentest/
  check.py path/to/file.md ...     # scan specific files (verify a single fix)
  check.py --json                  # machine-readable findings
  check.py --strict                # review findings also set exit code
  check.py --rules                 # list rule ids and exit
"""

import argparse
import json
import os
import re
import sys

DEFAULT_ROOTS = ["Workbook", "Workbook-Pentest"]

# ---------------------------------------------------------------------------
# Severity tiers
HARD = "hard"
REVIEW = "review"

# Regexes ------------------------------------------------------------------
UNICODE_DASH = re.compile(r"[–—]")
# prose em-dash substitute: word -- word. Excludes command syntax such as
# "tar ... -- *" or "cmd -- --flag" where a side is not an alphanumeric word.
DOUBLE_DASH = re.compile(r"[A-Za-z0-9] -- [A-Za-z0-9]")
INLINE_CODE = re.compile(r"`[^`]*`")
FENCE = re.compile(r"^\s*(```|~~~)")
ADMON_DECL = re.compile(r"^\s*(!!!|\?\?\?)\s+\S+")
HEADING = re.compile(r"^\s*#{1,6}\s")
# "This " starting a sentence (line start or after . ! ? plus space)
THIS_START = re.compile(r"(?:^|(?<=[.!?])\s)This\s+[a-z]")
# credential value carrying a "!" : an explicit assignment "Password: Foo!"
# or "pwd=Bar!". Deliberately strict: prose ABOUT the ! rule, CME's "Pwn3d!"
# marker, and spray-list examples must not trip it (penetration testing audit confirmed zero
# real !-passwords in workbooks, so any hit is high-signal).
CRED_BANG = re.compile(r"(?i)\bpass(?:word|wd)?\b\s*[:=`]\s*`?[^\s`|]*!")
FLAG_TOKEN = re.compile(r"OCR\{([^{}]*)\}")
# markdown link / image target: the (...) of ](...)
LINK = re.compile(r"\]\(([^)]+)\)")
# vocabulary that marks a flag token as a deliberate mask/placeholder.
# Tokens are delimited by start/end or _ + - / space (NOT \b, because "_" is a
# word char so \b never fires inside "part1_part2"). Trailing \d* covers
# "part1", "token2", "lvl3".
_VOCAB = (r"token|part|flag|value|here|your|example|sample|raw|lvl|level|"
          r"count|vendor|plant|interval|plc|name|user|host|ip|port|hash|xxx|"
          r"redacted|masked|placeholder|blank|fill|answer|format")
MASK_VOCAB = re.compile(
    r"(?i)(?:^|[\s_+/-])(?:" + _VOCAB + r")\d*(?=$|[\s_+/-])")
# runs of a repeated letter are fill-in placeholders: mcXXXX_vYYY, nnnn
PLACEHOLDER_RUN = re.compile(r"(?i)(x{3,}|y{3,}|z{3,}|n{4,}|q{3,})")
# availability claims in prose
FIXED_PATH = re.compile(
    r"(?i)(available|located|live|lives|installed|ready|pre-?installed|"
    r"you\s+have|find\s+(?:it|them|the))\b[^.\n]{0,60}?"
    r"(/usr/share|/opt/|/root/|/home/kali)"
)
CODE_FENCE_LANG = re.compile(r"^\s*(```|~~~)\s*([a-zA-Z0-9_+-]*)")
CMD_LANGS = {"bash", "sh", "shell", "console", "powershell", "ps1",
            "python", "py", "cmd", "bat", "text", ""}

# a "**Flag:** <blank>" submission line: an empty OCR{} or an underscore run.
FLAG_SUBMIT_BLANK = re.compile(r"\*\*Flag:\*\*\s*`?\s*(?:OCR\{[_\s]*\}|_{4,})")
# nearby evidence the student is told WHAT/HOW to submit: a templated flag
# OCR{<...>}, or guidance vocabulary about obtaining/assembling/submitting it.
FLAG_SUBMIT_GUIDE = re.compile(
    r"OCR\{[^}]*<[^}]*\}"
    r"|the flag is\b|submit it\b|submit the\b|assemble\b|join\b|decoded?\b"
    r"|exactly as\b|marker\b|wrapper\b|template\b|read it off\b", re.I)

# files that are not step-by-step walkthroughs (admonition rule exempt)
NON_WALKTHROUGH = re.compile(
    r"(?i)(00_intro|introduction|index|chapter_review|review|cheat|"
    r"mock|timed_challenge|summary|overview)"
)


def strip_inline_code(text):
    return INLINE_CODE.sub("", text)


def scan_file(path):
    """Return list of finding dicts for one markdown file."""
    findings = []
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.readlines()
    except (OSError, UnicodeDecodeError) as exc:
        return [{"rule": "read-error", "tier": HARD, "line": 0,
                 "snippet": str(exc), "file": path}]

    in_fence = False
    has_cmd_block = False
    has_admonition = False
    base = os.path.basename(path)
    is_walkthrough = bool(re.match(r"^\d", base)) and not NON_WALKTHROUGH.search(path)

    def add(rule, tier, lineno, snippet):
        findings.append({"rule": rule, "tier": tier, "line": lineno,
                        "snippet": snippet.strip()[:160], "file": path})

    for i, raw in enumerate(lines, 1):
        line = raw.rstrip("\n")
        fence_m = FENCE.match(line)
        if fence_m:
            if not in_fence:
                lang_m = CODE_FENCE_LANG.match(line)
                lang = (lang_m.group(2) or "").lower() if lang_m else ""
                if lang in CMD_LANGS:
                    has_cmd_block = True
            in_fence = not in_fence
            continue

        # unicode dash: applies EVERYWHERE, even inside code (PowerShell/PDF)
        if UNICODE_DASH.search(line):
            add("unicode-dash", HARD, i, line)

        if ADMON_DECL.match(line):
            kw = line.strip().split()[1].strip('"').lower()
            if kw in ("kali", "target", "example"):
                has_admonition = True

        if in_fence:
            continue  # remaining rules are prose-only

        prose = strip_inline_code(line)

        if DOUBLE_DASH.search(prose):
            add("double-dash-prose", HARD, i, line)

        if CRED_BANG.search(line):
            add("password-bang", HARD, i, line)

        if THIS_START.search(prose):
            add("this-start", HARD, i, line)

        for m in FLAG_TOKEN.finditer(line):
            inner = m.group(1)
            if _is_real_flag(inner):
                add("flag-exposure", REVIEW, i, line)

        if FIXED_PATH.search(prose):
            add("fixed-path-prose", REVIEW, i, line)

        for m in LINK.finditer(prose):
            res = _check_link(m.group(1), os.path.dirname(path))
            if res:
                rule, target = res
                add(rule, HARD, i, f"{rule}: {target}")

    # file-level: a blank "**Flag:**" submission line must carry the flag format
    # (a template, or a how-to-submit hint) within a few lines, so the student
    # knows how to build and submit it. Missing this was a recurring gap.
    for i, raw in enumerate(lines, 1):
        if FLAG_SUBMIT_BLANK.search(raw):
            window = "".join(lines[max(0, i - 15):i + 1])
            if not FLAG_SUBMIT_GUIDE.search(window):
                add("flag-no-submit-guidance", REVIEW, i,
                    "blank flag at submission with no format/template or "
                    "how-to-submit guidance nearby")

    # file-level: walkthrough with command blocks but no kali/target/example
    if is_walkthrough and has_cmd_block and not has_admonition:
        findings.append({"rule": "missing-admonition", "tier": REVIEW,
                        "line": 0, "snippet": "command blocks present, no "
                        "!!! kali/target/example admonition", "file": path})
    return findings


def _check_link(target, src_dir):
    """Validate a relative markdown link/image target against the source file's
    directory (mkdocs resolves relative links relative to the source .md, not
    the output URL). Returns (rule, target) for a defect, else None.

    Skips external/absolute/anchor/template targets. Flags:
      broken-link    a relative file ref that does not exist on disk
      link-url-path  a directory/page URL form (ends '/'); mkdocs neither
                     validates nor rewrites it, so it breaks under
                     use_directory_urls -- use the '.md' target instead.
    """
    t = target.strip()
    if t.startswith("<") and ">" in t:
        t = t[1:t.index(">")]
    else:
        parts = t.split()
        t = parts[0] if parts else t
    if not t:
        return None
    if re.match(r"^(?:https?:|ftp:|mailto:|tel:|data:|#|//|/|\{)", t):
        return None
    t = t.split("#", 1)[0].split("?", 1)[0]
    if not t:
        return None
    # Skip code-looking targets: a real link/asset path never contains quotes,
    # braces, parens, pipes or backslashes. Guards against ](...) matches inside
    # code/payloads (e.g. SSTI __globals__['popen']('id')) that the fence
    # tracker misses when the fence is inside a blockquote.
    if re.search(r"""[`'"{}()*|\\]""", t):
        return None
    if t.endswith("/"):
        return ("link-url-path", t)
    resolved = os.path.normpath(os.path.join(src_dir, t))
    if not os.path.exists(resolved):
        return ("broken-link", t)
    return None


def _is_real_flag(inner):
    """True if an OCR{...} inner string looks like a concrete real flag."""
    if not inner:
        return False
    if "<" in inner or ">" in inner or "." in inner:
        return False  # <placeholder> or OCR{...}
    if set(inner) <= set("_ -"):
        return False  # OCR{____} blank
    if MASK_VOCAB.search(inner):
        return False  # token1_token2, part1+part2, your_flag_here, etc.
    if PLACEHOLDER_RUN.search(inner):
        return False  # mcXXXX_vYYY: repeated-letter fill-in placeholders
    if not re.fullmatch(r"[A-Za-z0-9_]+", inner):
        return False  # jinja {{ }}, weird chars: not our concern
    # a real flag value: has a digit OR a vowel-heavy real-looking word and
    # is long enough to be a value, not a 1-2 char token
    if len(inner) < 4:
        return False
    return True


def collect_targets(args):
    files = []
    roots = args.paths or DEFAULT_ROOTS
    for root in roots:
        if os.path.isfile(root):
            if root.endswith(".md"):
                files.append(root)
        elif os.path.isdir(root):
            for dirpath, _dirs, names in os.walk(root):
                for n in names:
                    if n.endswith(".md"):
                        files.append(os.path.join(dirpath, n))
        else:
            print(f"warning: {root} not found", file=sys.stderr)
    return sorted(files)


RULE_DOC = {
    "unicode-dash": "U+2013/U+2014 anywhere (breaks PowerShell + PDF gen)",
    "double-dash-prose": "' -- ' used as punctuation in prose",
    "password-bang": "'!' inside a credential/password value",
    "this-start": "a prose sentence beginning with 'This '",
    "flag-exposure": "OCR{...} that looks like a concrete real flag",
    "missing-admonition": "walkthrough with command blocks, no kali/target",
    "fixed-path-prose": "prose claiming a tool/wordlist lives at a fixed path",
    "broken-link": "relative link/image target not found on disk",
    "link-url-path": "directory/page URL link (ends '/'); use the .md target",
}


def main():
    ap = argparse.ArgumentParser(description="OCR workbook standards linter")
    ap.add_argument("paths", nargs="*", help="files or dirs (default: %s)"
                    % ", ".join(DEFAULT_ROOTS))
    ap.add_argument("--json", action="store_true", help="machine output")
    ap.add_argument("--strict", action="store_true",
                    help="review findings also set non-zero exit")
    ap.add_argument("--rules", action="store_true", help="list rules and exit")
    args = ap.parse_args()

    if args.rules:
        for rid, doc in RULE_DOC.items():
            print(f"  {rid:20s} {doc}")
        return 0

    all_findings = []
    for path in collect_targets(args):
        all_findings.extend(scan_file(path))

    hard = [f for f in all_findings if f["tier"] == HARD]
    review = [f for f in all_findings if f["tier"] == REVIEW]

    if args.json:
        print(json.dumps({"hard": hard, "review": review,
                          "counts": _counts(all_findings)}, indent=2))
    else:
        _print_human(all_findings, hard, review)

    if hard:
        return 1
    if review and args.strict:
        return 1
    return 0


def _counts(findings):
    out = {}
    for f in findings:
        out[f["rule"]] = out.get(f["rule"], 0) + 1
    return out


def _print_human(all_findings, hard, review):
    by_file = {}
    for f in all_findings:
        by_file.setdefault(f["file"], []).append(f)
    for path in sorted(by_file):
        print(f"\n{path}")
        for f in sorted(by_file[path], key=lambda x: (x["line"], x["rule"])):
            tag = "HARD  " if f["tier"] == HARD else "review"
            loc = f":{f['line']}" if f["line"] else ""
            print(f"  {tag} {f['rule']:20s}{loc}: {f['snippet']}")
    print("\n" + "=" * 60)
    print("RULE COUNTS")
    for rule, n in sorted(_counts(all_findings).items(),
                        key=lambda kv: -kv[1]):
        print(f"  {n:5d}  {rule}")
    print(f"\n  {len(hard)} hard violation(s), {len(review)} review flag(s) "
        f"across {len(by_file)} file(s)")


if __name__ == "__main__":
    sys.exit(main())
