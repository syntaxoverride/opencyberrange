#!/usr/bin/env python3
"""OCR lab.yaml standards checker (read-only).

Audits platform/labs/<Track>/<lab>/lab.yaml for the conventions that the
data-smoke harness does NOT cover. Purely read-only: prints findings, never
edits. lab.yaml edits change future lab spawns, so fixes are a deliberate,
separate step from this audit.

Checks
  workbook-path-missing   workbook: points at a directory that does not exist
  workbook-no-slash       workbook: value lacks a trailing slash
  difficulty-too-long     difficulty: exceeds varchar(20) or is multi-word
  relative-bind-mount     compose bind mount uses a relative path, not
                          ${LABS_HOST_PATH}/...
  cred-bang               a credential/scenario password contains "!"
  unicode-dash            U+2013/U+2014 anywhere in the yaml
  flag-in-prose           the exact flag: value appears in a student-visible
                          field (scenario/description/objectives/hints or a
                          comment), leaking the answer. Mask it instead:
                          OCR{<describe>_<the>_<parts>}. Only flag: and test:
                          may hold the literal value.
"""

import os
import re
import sys

LABS_ROOT = "platform/labs"
# workbook dir lives under one of the wiki source trees, resolved from repo root
WIKI_SRC = ["Workbook", "Workbook-Pentest"]

DASH = re.compile(r"[–—]")
CRED_BANG = re.compile(r"(?i)\b(pass(?:word|wd)?|pwd)\b\s*[:=]\s*\S*!")
WORKBOOK = re.compile(r"^\s*workbook:\s*[\"']?([^\"'\n]+?)[\"']?\s*$")
DIFFICULTY = re.compile(r"^\s*difficulty:\s*[\"']?([^\"'\n]+?)[\"']?\s*$")
FLAG_VALUE = re.compile(r"^flag:\s*[\"']?(OCR\{[^\"'\n}]*\})")
TOP_KEY = re.compile(r"^([A-Za-z_][\w]*):")
# blocks that legitimately hold the literal flag; every other block is prose
FLAG_OK_BLOCKS = {"flag", "test"}


def resolve_workbook_dir(value):
    """Return True if the workbook path resolves to an existing directory."""
    # values look like "wiki-pentestprep/CH_PENTEST01.../01_Full_Port_Scanning/" or
    # "CH_X/00_Intro/". Strip a leading wiki-* url prefix and probe the source
    # trees for the chapter directory.
    v = value.strip().strip("/")
    v = re.sub(r"^wiki[\w-]*/", "", v)
    parts = v.split("/")
    # chapter dir is the first path segment after any wiki prefix
    chapter = parts[0] if parts else ""
    if not chapter:
        return True  # nothing to check
    for src in WIKI_SRC:
        if os.path.isdir(os.path.join(src, chapter)):
            return True
        # also accept full nested path existence
        if os.path.isdir(os.path.join(src, v)):
            return True
    return False


def scan(path):
    findings = []
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except (OSError, UnicodeDecodeError) as exc:
        return [(path, 0, "read-error", str(exc))]
    # pre-extract the concrete flag value so we can detect it leaking into prose
    flag_value = None
    for line in text.splitlines():
        fm = FLAG_VALUE.match(line)
        if fm:
            flag_value = fm.group(1)
            break
    cur_block = None
    for i, line in enumerate(text.splitlines(), 1):
        km = TOP_KEY.match(line)
        if km:
            cur_block = km.group(1)
        if flag_value and flag_value in line and cur_block not in FLAG_OK_BLOCKS:
            findings.append((path, i, "flag-in-prose", line.strip()[:90]))
        if DASH.search(line):
            findings.append((path, i, "unicode-dash", line.strip()[:90]))
        if CRED_BANG.search(line):
            findings.append((path, i, "cred-bang", line.strip()[:90]))
        m = WORKBOOK.match(line)
        if m:
            val = m.group(1)
            if not val.endswith("/"):
                findings.append((path, i, "workbook-no-slash", val))
            if not resolve_workbook_dir(val):
                findings.append((path, i, "workbook-path-missing", val))
        m = DIFFICULTY.match(line)
        if m:
            val = m.group(1).strip()
            if len(val) > 20 or " " in val or "-" in val:
                findings.append((path, i, "difficulty-too-long",
                                f"{val} (len {len(val)})"))
        # bind mounts: a "- ./x:/y" or "- x/y:/z" relative source (compose files
        # are sometimes inlined; lab.yaml may reference them). Flag obvious
        # relative host paths in volume-like lines.
        if re.search(r"^\s*-\s*\.{0,2}/?[\w./-]+:/", line) and \
                "${LABS_HOST_PATH}" not in line and \
                not line.lstrip().startswith("- /"):
            if re.search(r"^\s*-\s*\.", line):
                findings.append((path, i, "relative-bind-mount",
                                line.strip()[:90]))
    return findings


def main():
    roots = sys.argv[1:] or [LABS_ROOT]
    yamls = []
    for root in roots:
        if os.path.isfile(root):
            yamls.append(root)
        else:
            for dp, _d, names in os.walk(root):
                for n in names:
                    if n == "lab.yaml":
                        yamls.append(os.path.join(dp, n))
    all_f = []
    for y in sorted(yamls):
        all_f.extend(scan(y))
    by_rule = {}
    for path, line, rule, snip in all_f:
        by_rule.setdefault(rule, []).append((path, line, snip))
        print(f"{rule:24s} {path}:{line}  {snip}")
    print("\n" + "=" * 60)
    for rule in sorted(by_rule):
        print(f"  {len(by_rule[rule]):4d}  {rule}")
    print(f"\n  {len(all_f)} finding(s) across {len(yamls)} lab.yaml file(s)")
    return 1 if all_f else 0


if __name__ == "__main__":
    sys.exit(main())
