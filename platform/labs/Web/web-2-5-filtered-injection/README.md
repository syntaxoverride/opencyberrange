# Web 2.5: Filtered Injection

## Overview

TrueNorth Hosting provides a web-based DNS lookup tool that filters common shell
metacharacters (semicolons, pipes, ampersands) from user input before passing it
to a system command. Students must discover that newline characters (`%0a`) bypass
the filter, enabling OS command injection.

## Learning Objectives

- Understand how input filtering differs from proper input validation
- Recognize that blocklist-based filtering can miss edge cases
- Learn to use URL-encoded newlines (`%0a`) to bypass character filters
- Practice chaining injected commands to explore a filesystem

## Attack Path

1. Use the DNS lookup tool normally to understand its behavior
2. Attempt classic injection characters (`;`, `|`, `&`) and observe they are stripped
3. Discover that `%0a` (URL-encoded newline) is not filtered
4. Inject commands via newline to explore the server filesystem
5. Locate and read both token files to assemble the flag

## Tokens

- **Token 1:** Located in a hidden configuration directory under `/opt/truenorth/`
- **Token 2:** Located in a restricted file on the system

## Key Takeaway

Blocklist-based input filtering is inherently fragile. Developers should use
allowlist validation or parameterized command execution instead of stripping
known-bad characters.
