# Template: SSH File Discovery (linux-ssh-file-discovery)

De-identified seed for Exercise Studio Phase 0. Source lab:
`platform/labs/Linux/linux-2-3-ssh-file-discovery`.

## What is structural (locked)

- SSH authentication on port 22.
- File discovery in `/var/www/html/`; flag lives in
  `/var/www/html/backups/deployment_notes.txt`.
- The three tester steps (port check, banner, SSH login and flag retrieval).
- The single-node topology (target at ip_offset 10).

## What is cosmetic (skinnable)

Declared in `template.yaml` under `cosmetic_schema`:

- `company`, `persona`, `scenario`, `objectives` (narrative branding)
- `hostname` (container hostname)
- `credentials[ssh-user].user` / `.pass` (the role id `ssh-user` is locked)
- `flag.value` and `flag.mode` (`fixed` or `auto`)
- `difficulty`

## Per-instance injection

`containers/target/entrypoint.sh` reads, with baked fallbacks:

| Env var               | Fallback              |
|-----------------------|-----------------------|
| `CRED_ssh-user_USER`  | `webadmin`            |
| `CRED_ssh-user_PASS`  | `WebServer2024#`      |
| `FLAG`                | `OCR{f1l3_d1sc0v3ry}` |

The hyphenated credential env vars are read with `printenv` because they are not
valid POSIX shell identifiers. All passwords use `#`, never `!` (bash history
expansion breaks the Exercise Tester).

## Standalone build

The image is fully runnable without the platform: the baked Dockerfile defaults
match the fallbacks, so a bare `docker compose up` yields the original lab.
