# Template: Firewall Fundamentals (network-firewall-fundamentals)

De-identified seed for Exercise Studio Phase 0. Source lab:
`platform/labs/Network/network-12-1-firewall-fundamentals`.

## Topology (structural, locked)

| Node       | Role               | ip_offset |
|------------|--------------------|-----------|
| firewall   | iptables router    | 10        |
| devserver  | traffic generator  | 23        |
| webserver  | Apache + listeners | 47        |

The `monitor` and `traffic-loop.sh` scripts discover peers dynamically from the
assigned subnet at these offsets, so the peer offsets are locked. The iptables
FORWARD exploit path (allow 80/443, drop the rest) and the four tester steps are
structural.

## What is cosmetic (skinnable)

Declared in `template.yaml` under `cosmetic_schema`:

- `company`, `contractor`, `persona`, `scenario`, `objectives` (narrative)
- `hostname` (array: firewall, dev, web)
- `credentials[analyst].user` / `.pass` (the role id `analyst` is locked)
- `flag.value` and `flag.mode`
- `difficulty`

## Per-instance injection (firewall container)

`containers/firewall/start.sh` reads, with baked fallbacks:

| Env var             | Fallback                |
|---------------------|-------------------------|
| `CRED_analyst_USER` | `analyst`               |
| `CRED_analyst_PASS` | `M3r1d14n_Fw#`          |
| `FLAG`              | `OCR{tr4ff1c_c0ntr0ll3d}` |

The flag is written to `/root/flag.txt` and revealed only by `sudo check-rules`
once the student's FORWARD rules are correct. All passwords use `#`, never `!`.

## De-identification note

Display-only company strings in `monitor`, `check-rules`, `index.html` and
`traffic-loop.sh` were neutralized (Lab Firewall / Example Health / Dev Server).
The cosmetic layer re-skins them at instantiate time. The traffic-gen and
web-server containers are otherwise functionally identical to the seed.
