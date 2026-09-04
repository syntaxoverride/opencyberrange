# OCR Sizing & Settings — Single Source of Truth

All memory in MiB (binary; the config's "GB"/"g"/"G" values are GiB, so
1 GiB = 1024 MiB). Defaults are from the code/compose as of 2026-07-03.

## 1. Host sizing per edition

Proxmox vCPU = sockets x cores. Use 1 socket and put the count in cores
(multiple sockets only help NUMA on very large hosts, not here).

| Edition | Profile | Sockets | Cores | vCPU | RAM (MiB) | RAM (GiB) |
|---|---|---|---|---|---|---|
| Lite | Minimum (boots, Docker labs, no RangeBox) | 1 | 2 | 2 | 4096 | 4 |
| Lite | Kick the tires (a few users + RangeBox) | 1 | 2-4 | 2-4 | 8192 | 8 |
| Lite | Recommended (a class) | 1 | 4 | 4 | 16384 | 16 |
| Lite | Comfortable | 1 | 6-8 | 6-8 | 24576-32768 | 24-32 |
| Enterprise | Minimum (1 AD lab set, 1 user) | 1 | 4 | 4 | 16384 | 16 |
| Enterprise | Recommended (a class, AD/OT) | 1 | 8 | 8 | 32768 | 32 |
| Enterprise | Comfortable | 1 | 16 | 16 | 65536 | 64 |

Backend workers stop scaling past 4 cores (worker count = (2xcores)+1, cap 9).
Beyond that, cores/RAM go to labs, RangeBoxes, and (Enterprise) Windows VMs.
Enterprise nested virt also needs the VM CPU type set to `host`.

## 2. Per-component footprint

| Component | Count | RAM each (MiB) | CPU each | Cap source |
|---|---|---|---|---|
| PostgreSQL 15 | 1 | ~150-200 | light | none |
| Backend (uvicorn) | (2xvCPU)+1, cap 9 workers | ~150-250 / worker | shares cores | Dockerfile |
| nginx frontend | 1 | ~50 | light | none |
| RangeBox (per student) | 0..N | 2048 (hard cap) | 0.5 vCPU | RANGEBOX_MEM_LIMIT / _CPU_QUOTA |
| Docker lab containers | per active lab | unbounded (no limit) | bursty | none set |
| Shared Windows/AD VM (Enterprise) | per definition | 4096 | 2 cores | shared VM ram / cpu_cores |

## 3. Tunable env knobs (set in .env or compose)

| Knob | Default | Meaning |
|---|---|---|
| RANGEBOX_MEM_LIMIT | 2g (2048 MiB) | hard RAM cap per browser desktop |
| RANGEBOX_CPU_QUOTA | 50000 (0.5 vCPU) | CPU cap per browser desktop |
| RANGEBOX_MEM_RESERVE_GB | 8 (8192 MiB) | free RAM kept before a new RangeBox is allowed |
| RANGEBOX_MAX_CEILING | 64 | absolute max concurrent RangeBoxes |
| MAX_CONCURRENT_RANGEBOXES | (dynamic) | pin a fixed cap; unset = computed from free RAM |
| uvicorn workers | (2xcores)+1, cap 9 | backend processes (auto) |
| shared VM `ram` | 4G (4096 MiB) | per Windows/AD VM (per definition or DB row) |
| shared VM `cpu_cores` | 2 | per Windows/AD VM |

## 4. Platform settings (DB-backed, admin-editable at runtime)

| Key | Default | Meaning |
|---|---|---|
| default_session_hours | 2 | lab session length before expiry |
| max_session_hours | 8 | ceiling for extensions |
| shared_vm_session_hours | 2 | shared-VM session length |
| shared_vm_max_extensions | 4 | max shared-VM extensions |
| shared_vm_max_uptime_hours | 8 | shared-VM hard uptime cap |
| shared_vm_idle_timeout_minutes | 30 | idle shutdown for shared VMs |

## 5. Entitlement / caps

| Setting | Lite | Enterprise |
|---|---|---|
| max_privileged_accounts | 1 | unlimited (null) |
| max_active_courses | 5 | unlimited (null) |
| students | unlimited | unlimited |

Set by `backend/data/entitlement.json`; no file = Lite defaults.

## 6. Ports & networks

| Item | Value | Env |
|---|---|---|
| HTTP | 80 | OCR_HTTP_PORT |
| HTTPS | 443 | OCR_HTTPS_PORT |
| Backend API | 127.0.0.1:8000 (localhost only) | OCR_BACKEND_PORT |
| WireGuard | 51820/udp | WG_SERVER_ENDPOINT |
| Lab subnets | 10.100.0.0/14 | WG_NETWORK_BASE (10.100) |
| VPN client base | 10.0.0.0 | WG_CLIENT_BASE |

## 7. Virtualization requirement

| Edition | KVM | Host type |
|---|---|---|
| Lite | Not needed (Docker-only) | Plain Linux VM (or, with plumbing, LXC) |
| Enterprise | /dev/kvm required for shared VMs; VM CPU type = host (nested virt) | Linux VM, NOT LXC |

## 8. Worked examples

- Lite, 4 vCPU / 16384 MiB: core stack ~2 GiB, leaves room for ~5 concurrent
  RangeBoxes (0.5 vCPU + 2 GiB cap each) or many lighter Docker labs.
- Enterprise, one student on an AD lab: core ~2 GiB + DC 4096 MiB + workstation
  4096 MiB + their RangeBox wants 8192 MiB free = ~18 GiB, ~5-6 vCPU. Shared
  VMs are shared class-wide (one DC); per-student workstations and RangeBoxes
  stack.
