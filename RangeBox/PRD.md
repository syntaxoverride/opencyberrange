# RangeBox: Browser-Based Attack Desktop for OpenCyberRange

**Product Requirements Document v1.1**
**Date:** 2026-03-01
**Status:** Implemented

---

## 1. Executive Summary

RangeBox is a browser-based Kali Linux desktop that eliminates the student setup
barrier for OpenCyberRange labs. Instead of requiring students to install a local
Kali VM and configure a WireGuard VPN, RangeBox spawns a pre-configured attacker
container directly on the lab network and streams a full XFCE desktop to the
browser via noVNC.

**The goal:** A student clicks "Start Lab", and within 10 seconds they have a
fully-equipped Kali desktop in their browser, already connected to the lab
targets. Zero local setup.

---

## 2. Problem Statement

### Current Student Experience

```
1. Download & install VirtualBox/VMware     (~30 min, 4GB download)
2. Download Kali VM image                   (~15 min, 3GB download)
3. Configure VM settings (RAM, CPU, network) (~10 min)
4. Boot Kali, log in                        (~2 min)
5. Download WireGuard config from platform  (~1 min)
6. Install & configure WireGuard in VM      (~5 min)
7. Test VPN connectivity                    (~2 min)
8. Finally start the actual lab             (~0 min... if nothing broke)
```

**Total setup time: 60+ minutes** before touching a single lab exercise.

### Failure Modes

| Problem | Frequency | Impact |
|---------|-----------|--------|
| VM won't boot (BIOS virtualization disabled) | ~15% of students | Blocks entirely until IT fixes BIOS |
| VPN config errors (wrong keys, firewall) | ~20% of students | Hours of debugging |
| Chromebook/tablet users (can't run VMs) | ~10% of students | Cannot participate at all |
| Insufficient RAM for VM + host OS | ~10% of students | Severe performance issues |
| Corporate/campus firewall blocks WireGuard UDP | ~5% of students | Requires wstunnel workaround |

### With RangeBox

```
1. Click "Start Lab"                        (~1 click)
2. Wait for containers to spawn             (~10 seconds)
3. Kali desktop appears in browser          (~0 additional steps)
4. Start hacking                            (immediate)
```

**Total setup time: ~10 seconds.** Works on any device with a modern browser.

---

## 3. User Stories

### P0: Must Have

| ID | Story | Acceptance Criteria |
|----|-------|---------------------|
| US-1 | As a student, I want to launch a Kali desktop in my browser when I start a lab, so I don't need to set up a local VM. | Desktop loads within 15s of lab spawn. XFCE desktop is interactive. |
| US-2 | As a student, I want the RangeBox to already be connected to the lab network, so I can immediately scan and attack targets. | `ping 10.100.{uid}.17` works from RangeBox terminal. No VPN setup required. |
| US-3 | As a student, I want common pentesting tools pre-installed (nmap, gobuster, hydra, etc.), so I can complete labs without installing anything. | All tools listed in the lab's `tools` field are available in the RangeBox. |
| US-4 | As a student, I want to copy/paste text between my host browser and the RangeBox, so I can transfer flags, commands, and notes. | Clipboard sync works via noVNC clipboard panel or keyboard shortcuts. |
| US-5 | As a student, I want the RangeBox to be cleaned up when I stop the lab, so server resources aren't wasted. | Container and network are destroyed on lab stop, session expiry, or manual stop. |
| US-6 | As an instructor, I want RangeBox to use the same network isolation model as the existing VPN approach, so one student can't access another's lab. | Each RangeBox is on its own `10.100.{uid}.0/24` subnet. No cross-subnet routing. |

### P1: Should Have

| ID | Story | Acceptance Criteria |
|----|-------|---------------------|
| US-7 | As a student, I want to resize the RangeBox viewport or go fullscreen, so I can work comfortably. | Fullscreen button works. Resolution scales to browser window. |
| US-8 | As a student, I want my RangeBox working directory to persist across lab restarts within the same session, so I don't lose my notes and scripts. | A Docker volume mounts at `~/data` and survives container restarts within the same lab session. |
| US-9 | As an instructor, I want to see which students are using RangeBox vs. local VPN, so I can monitor engagement. | Dashboard shows connection method per student. |
| US-10 | As a student, I want to choose between RangeBox (browser desktop) and VPN (local Kali) for any lab, so power users aren't forced into the browser. | Both options available on the lab start page. VPN flow unchanged. |

### P2: Nice to Have

| ID | Story | Acceptance Criteria |
|----|-------|---------------------|
| US-11 | As a student, I want to upload/download files to/from RangeBox, so I can transfer exploit scripts or loot. | File upload/download panel in the noVNC toolbar or a dedicated button. |
| US-12 | As an instructor, I want to set per-lab resource limits for RangeBox containers, so heavy labs don't starve the server. | CPU/RAM limits configurable in lab metadata. |
| US-13 | As a student on a slow connection, I want a terminal-only RangeBox mode, so I get lower latency without the desktop overhead. | Toggle between "Desktop" and "Terminal" mode. Terminal mode uses xterm.js + ttyd instead of VNC. |

---

## 4. Architecture

### 4.1 System Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Student Browser                                            │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Vue.js SPA                                           │  │
│  │                                                       │  │
│  │  ┌─LabWorkspace.vue─────────────────────────────────┐ │  │
│  │  │                                                   │ │  │
│  │  │  ┌─RangeBox.vue (noVNC viewer)──────────────────┐  │ │  │
│  │  │  │                                             │  │ │  │
│  │  │  │  Kali XFCE Desktop                         │  │ │  │
│  │  │  │  - Terminal, file manager, browser          │  │ │  │
│  │  │  │  - All pentesting tools pre-installed       │  │ │  │
│  │  │  │  - Connected to 10.100.{uid}.0/24           │  │ │  │
│  │  │  │                                             │  │ │  │
│  │  │  └─────────────────────────────────────────────┘  │ │  │
│  │  │                                                   │ │  │
│  │  │  ┌─LabPanel.vue──────────────┐                    │ │  │
│  │  │  │ Targets | Flags | Hints   │                    │ │  │
│  │  │  └───────────────────────────┘                    │ │  │
│  │  └───────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │  HTTPS + WSS (WebSocket Secure)
                     │
┌────────────────────▼────────────────────────────────────────┐
│  Server                                                     │
│                                                             │
│  ┌─Nginx──────────────────────────────────────────────────┐ │
│  │  /                  → Vue SPA (static)                 │ │
│  │  /api/*             → FastAPI backend (:8000)          │ │
│  │  /api/rangebox/*/vnc  → WebSocket proxy to container    │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌─FastAPI Backend────────────────────────────────────────┐ │
│  │                                                        │ │
│  │  POST /api/labs/spawn/{slug}                           │ │
│  │    → create Docker network 10.100.{uid}.0/24           │ │
│  │    → start lab target containers                       │ │
│  │    → start RangeBox attacker container (NEW)             │ │
│  │    → return VNC connection URL                         │ │
│  │                                                        │ │
│  │  WebSocket /api/rangebox/{session_id}/vnc                │ │
│  │    → authenticate JWT                                  │ │
│  │    → proxy to container's websockify port (6080)       │ │
│  │                                                        │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌─Docker────────────────────────────────────────────────┐  │
│  │  Network: lab_{uid}_{slug} (10.100.{uid}.0/24)        │  │
│  │                                                       │  │
│  │  ┌─rangebox_{uid}_{slug}──┐  ┌─target containers──┐   │  │
│  │  │ 10.100.{uid}.254     │  │ 10.100.{uid}.17    │   │  │
│  │  │                      │  │ 10.100.{uid}.18    │   │  │
│  │  │ Xvfb → XFCE Desktop │  │ ...                │   │  │
│  │  │ x11vnc → VNC :5900   │  │                    │   │  │
│  │  │ websockify → WS :6080│  │ (existing lab      │   │  │
│  │  │ noVNC web client     │  │  containers,       │   │  │
│  │  │                      │  │  unchanged)        │   │  │
│  │  │ nmap, gobuster,      │  │                    │   │  │
│  │  │ hydra, metasploit,   │  └────────────────────┘   │  │
│  │  │ python3, curl, etc.  │                            │  │
│  │  └──────────────────────┘                            │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Technology Choices

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **VNC Server** | x11vnc | Lightweight, attaches to existing X display (vs. TigerVNC which creates its own) |
| **Display Server** | Xvfb | Virtual framebuffer; no physical display needed in container |
| **Desktop Environment** | XFCE4 | Lightest full DE (~200MB RAM). Familiar to Kali users. |
| **WebSocket Bridge** | websockify | Standard VNC-to-WebSocket proxy. Used by noVNC, OpenStack, Proxmox. |
| **Browser Client** | noVNC | De facto standard HTML5 VNC client. MIT license. Used by Proxmox, OpenStack. |
| **Base Image** | kalilinux/kali-rolling | Official Kali Docker image. Students expect Kali tooling. |
| **Container IP** | .254 on lab subnet | Convention: last usable IP, avoids conflict with lab targets (.1-.250) |

### 4.3 Why noVNC Over Alternatives

| Alternative | Why Not |
|-------------|---------|
| **Apache Guacamole** | Requires separate Java/Tomcat server + guacd daemon. Over-engineered for this use case; we only need VNC, not RDP/SSH multiplexing. |
| **Kasm Workspaces** | Full platform with its own user management, auth, and container orchestration. Conflicts with our existing FastAPI/Docker architecture. Good product, wrong integration point. |
| **xterm.js (terminal only)** | No GUI; can't run Burp Suite, Wireshark, or a browser for web exploitation labs. Good as a P2 "lightweight mode" addition. |
| **RDP (xrdp)** | Higher overhead, more complex setup, no clear advantage over VNC for this use case. |

---

## 5. Technical Design

### 5.1 RangeBox Container Image

**Image name:** `opencyberrange/rangebox`
**Base:** `kalilinux/kali-rolling`
**Target size:** ~3-4 GB (compressed ~1.5 GB)

#### Layer Breakdown

```dockerfile
FROM kalilinux/kali-rolling

# Layer 1: Desktop environment (~400MB)
# Xvfb (virtual framebuffer), XFCE4 (lightweight DE),
# x11vnc (VNC server), websockify + noVNC (browser bridge)

# Layer 2: Core pentesting tools (~1.5GB)
# Reconnaissance: nmap, masscan, gobuster, dirb, nikto, enum4linux
# Exploitation: metasploit-framework, sqlmap, searchsploit
# Password attacks: hydra, john, hashcat (CPU-only)
# Web: burpsuite (community), firefox-esr
# Networking: netcat, socat, tcpdump, wireshark (CLI)
# Scripting: python3, python3-pip, ruby, perl
# Utilities: curl, wget, vim, nano, tmux, git, ssh, jq

# Layer 3: Configuration (~10MB)
# XFCE panel layout, terminal defaults, wallpaper/branding
# Entrypoint script, health check
```

#### Entrypoint Script (`entrypoint.sh`)

```bash
#!/bin/bash
set -e

RESOLUTION="${RESOLUTION:-1280x800}"
VNC_PORT="${VNC_PORT:-5900}"
NOVNC_PORT="${NOVNC_PORT:-6080}"
DEPTH="${DEPTH:-16}"

# 1. Start virtual display
Xvfb :1 -screen 0 ${RESOLUTION}x${DEPTH} -ac &
export DISPLAY=:1
sleep 1

# 2. Start XFCE desktop
startxfce4 &
sleep 2

# 3. Start VNC server (no password: auth handled by FastAPI JWT proxy)
x11vnc -display :1 -forever -shared -rfbport ${VNC_PORT} -nopw \
       -xkb -noxrecord -noxfixes -noxdamage &

# 4. Start noVNC websockify bridge
websockify --web /usr/share/novnc ${NOVNC_PORT} localhost:${VNC_PORT}
```

**Security note:** The VNC server runs with no password (`-nopw`). Authentication
is handled at the FastAPI layer; the WebSocket connection requires a valid JWT.
The container's port 6080 is never exposed to the host network; it is only
reachable via Docker's internal network from the FastAPI backend.

#### Health Check

```dockerfile
HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
    CMD curl -sf http://localhost:6080/vnc.html || exit 1
```

### 5.2 Backend Changes

#### 5.2.1 Modified Lab Spawn Flow

**File:** `platform/backend/app/services/docker_manager.py`

```python
async def create_lab_environment(user_id, lab, compose_content, ...):
    # === EXISTING (unchanged) ===
    # 1. Clean up any existing networks for this user
    # 2. Create Docker network: 10.100.{user_id}.0/24
    # 3. docker compose up target containers
    # 4. Connect targets to network with assigned IPs

    # === NEW: Spawn RangeBox container ===
    if rangebox_enabled:
        rangebox_container = docker_client.containers.run(
            image="opencyberrange/rangebox",
            name=f"rangebox_{user_id}_{lab_slug}",
            detach=True,
            network=network.name,
            shm_size="256m",           # Required for browser/GUI rendering
            mem_limit="2g",            # Hard memory cap
            cpu_period=100000,
            cpu_quota=100000,          # 1.0 CPU core limit
            environment={
                "RESOLUTION": "1280x800",
            },
            labels={
                "ocr.role": "rangebox",
                "ocr.user_id": str(user_id),
                "ocr.lab_slug": lab_slug,
                "ocr.session_id": str(session_id),
            },
        )
        # Assign IP .254 on the lab subnet
        network.connect(rangebox_container, ipv4_address=f"10.100.{user_id}.254")

    # === EXISTING (unchanged) ===
    # 5. Enforce VPN firewall rules
    # 6. Return container info
```

#### 5.2.2 New API Endpoints

**File:** `platform/backend/app/routers/rangebox.py` (new file)

```
POST   /api/rangebox/{session_id}/start     Start RangeBox for an active lab session
DELETE /api/rangebox/{session_id}/stop       Stop RangeBox (keep lab running)
GET    /api/rangebox/{session_id}/status     Health check, resolution, container stats
WS     /api/rangebox/{session_id}/vnc        WebSocket proxy to noVNC
```

#### 5.2.3 WebSocket Proxy

The critical piece; proxying the browser's WebSocket to the container's
websockify instance. This keeps authentication centralized in FastAPI and avoids
exposing container ports to the host.

```python
@router.websocket("/api/rangebox/{session_id}/vnc")
async def rangebox_vnc_proxy(websocket: WebSocket, session_id: int):
    """
    Proxy WebSocket traffic between the browser (noVNC client)
    and the RangeBox container's websockify server.
    """
    # 1. Authenticate; extract and validate JWT from query param or cookie
    user = await authenticate_websocket(websocket)
    if not user:
        await websocket.close(code=4401)
        return

    # 2. Look up session; verify user owns this session and it's running
    session = await get_lab_session(session_id)
    if not session or session.user_id != user.id or session.status != "running":
        await websocket.close(code=4404)
        return

    # 3. Find RangeBox container and its internal IP
    container = find_rangebox_container(session)
    rangebox_ip = f"10.100.{user.id}.254"
    rangebox_ws_url = f"ws://{rangebox_ip}:6080/websockify"

    # 4. Establish upstream WebSocket to container
    await websocket.accept(subprotocol="binary")
    async with aiohttp.ClientSession() as http_session:
        async with http_session.ws_connect(rangebox_ws_url) as upstream:
            # 5. Bidirectional relay
            await asyncio.gather(
                relay(websocket, upstream),   # browser → container
                relay(upstream, websocket),   # container → browser
            )
```

**FastAPI can reach `10.100.{uid}.254:6080`** because the FastAPI backend
container needs to be connected to the lab networks, OR the backend runs on the
host and can route to Docker bridge networks natively. The existing architecture
has the backend running as a Docker container with access to the Docker socket,
so it can inspect container IPs and connect to them.

**Note on network access:** The FastAPI backend container must be able to reach
the lab Docker networks. Options:

- **Option A (simplest):** Run FastAPI on the host (not in Docker); it can
  reach all Docker bridge networks via the host's routing table.
- **Option B:** Connect the FastAPI container to each lab network when a RangeBox
  is spawned. Disconnect on cleanup.
- **Option C:** Use Docker's `host` network mode for the backend container.

The existing architecture uses Option A or B (backend has Docker socket access
and communicates via `host.docker.internal`). Option B is cleanest for isolation.

#### 5.2.4 Modified Cleanup Flow

**File:** `platform/backend/app/services/docker_manager.py`

```python
async def destroy_lab_environment(user_id, lab_slug, ...):
    # === EXISTING (unchanged) ===
    # 1. Stop target containers (graceful 30s timeout)
    # 2. Force remove if needed

    # === NEW: Also stop RangeBox ===
    rangebox = find_container_by_name(f"rangebox_{user_id}_{lab_slug}")
    if rangebox:
        rangebox.stop(timeout=10)  # RangeBox can be killed quickly
        rangebox.remove(force=True)

    # === EXISTING (unchanged) ===
    # 3. Disconnect and remove Docker network
    # 4. Clean up orphans
```

### 5.3 Database Changes

#### New Column on LabSession

```sql
ALTER TABLE lab_sessions ADD COLUMN rangebox_enabled BOOLEAN DEFAULT FALSE;
```

This tracks whether the student chose RangeBox vs. VPN for this session. Used for
analytics and to know whether to spawn/cleanup a RangeBox container.

#### Updated LabSession Model

```python
class LabSession(Base):
    # ... existing fields ...
    rangebox_enabled = Column(Boolean, default=False)  # NEW
```

No new tables required. The RangeBox container is ephemeral and tracked by Docker
labels, not database rows.

### 5.4 Frontend Changes

#### 5.4.1 Lab Start Flow Update

**File:** `platform/frontend/src/views/LabStart.vue` (or wherever lab launch UI lives)

Add a connection method chooser before spawning the lab:

```
┌────────────────────────────────────────┐
│  How do you want to connect?           │
│                                        │
│  ┌──────────────┐  ┌──────────────┐   │
│  │  🖥️ RangeBox   │  │  🔒 VPN      │   │
│  │  Browser      │  │  Local Kali  │   │
│  │  Desktop      │  │  + WireGuard │   │
│  │              │  │              │   │
│  │ (Recommended) │  │ (Advanced)   │   │
│  └──────────────┘  └──────────────┘   │
│                                        │
│  RangeBox gives you a full Kali desktop  │
│  in your browser. No setup needed.     │
└────────────────────────────────────────┘
```

The spawn API call includes the choice:

```javascript
await axios.post(`/api/labs/spawn/${labSlug}`, {
  rangebox_enabled: true  // or false for VPN mode
})
```

#### 5.4.2 RangeBox Vue Component

**File:** `platform/frontend/src/components/RangeBox.vue` (new file)

```vue
<template>
  <div class="rangebox-container" :class="{ fullscreen: isFullscreen }">
    <!-- Toolbar -->
    <div class="rangebox-toolbar">
      <span class="rangebox-label">RangeBox; Kali Linux</span>
      <div class="rangebox-actions">
        <button @click="toggleClipboard">Clipboard</button>
        <button @click="toggleFullscreen">Fullscreen</button>
        <button @click="reconnect" v-if="disconnected">Reconnect</button>
      </div>
    </div>

    <!-- noVNC Canvas -->
    <div ref="vncContainer" class="vnc-viewport"></div>

    <!-- Clipboard Sync Panel (toggleable) -->
    <div v-if="showClipboard" class="clipboard-panel">
      <textarea v-model="clipboardText" placeholder="Paste here to send to RangeBox..."/>
      <button @click="sendClipboard">Send to RangeBox</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import RFB from '@novnc/novnc/core/rfb'

const props = defineProps({
  sessionId: { type: Number, required: true },
  token: { type: String, required: true }
})

const vncContainer = ref(null)
let rfb = null

onMounted(() => {
  const wsUrl = `wss://${window.location.host}/api/rangebox/${props.sessionId}/vnc?token=${props.token}`

  rfb = new RFB(vncContainer.value, wsUrl, {
    wsProtocols: ['binary'],
    credentials: { password: '' }
  })

  rfb.viewOnly = false
  rfb.scaleViewport = true
  rfb.resizeSession = true
  rfb.clipViewport = false
  rfb.showDotCursor = true

  rfb.addEventListener('disconnect', () => { disconnected.value = true })
  rfb.addEventListener('connect', () => { disconnected.value = false })
})

onUnmounted(() => {
  if (rfb) rfb.disconnect()
})
</script>
```

**npm dependency:** `@novnc/novnc` (MIT license, installable via npm)

#### 5.4.3 Lab Workspace Layout

The RangeBox viewer integrates into the existing lab exercise page:

```
┌─────────────────────────────────────────────────────────────┐
│  Header: Lab Name │ Timer │ Status │ Stop Lab               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─ RangeBox (resizable, ~70% width) ──────────────────────┐ │
│  │                                                        │ │
│  │  [Kali XFCE Desktop via noVNC]                        │ │
│  │                                                        │ │
│  │                                                        │ │
│  │                                                        │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌─ Lab Panel (collapsible) ─────────────────────────────┐ │
│  │  📋 Briefing │ 🎯 Targets │ 🚩 Flags │ 💡 Hints      │ │
│  │                                                        │ │
│  │  Target: 10.100.42.17 (webserver)                     │ │
│  │  Target: 10.100.42.18 (database)                      │ │
│  │                                                        │ │
│  │  Flag: OCR{____________}  [Submit]                     │ │
│  │                                                        │ │
│  │  Hint 1: ► Try anonymous FTP access  (revealed)       │ │
│  │  Hint 2: ► ●●●●●●●●●●●●●●●●●●●●●●●  (locked)        │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 5.5 Nginx Changes

**File:** `platform/frontend/nginx.conf`

Add WebSocket proxy for RangeBox VNC connections:

```nginx
# RangeBox VNC WebSocket proxy
location ~ ^/api/rangebox/.*/vnc$ {
    proxy_pass http://backend:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # VNC sessions are long-lived; extend timeouts
    proxy_read_timeout 3600s;
    proxy_send_timeout 3600s;

    # Disable buffering for real-time VNC traffic
    proxy_buffering off;
}
```

The existing `/api` location block already proxies to the backend, but the
default `proxy_read_timeout` (60s) will kill VNC sessions. The dedicated
location block above ensures long-lived WebSocket connections survive.

### 5.6 Security Model

#### Threat Model

| Threat | Mitigation |
|--------|------------|
| **Student breaks out of container** | Docker container isolation (namespaces, cgroups). RangeBox runs as non-root user inside container. seccomp and AppArmor profiles applied. |
| **Student attacks host via Docker socket** | Docker socket is NOT mounted in RangeBox container. Only the FastAPI backend has socket access. |
| **Student attacks other students' labs** | Network isolation: each lab has its own Docker bridge network. No inter-network routing. iptables rules enforced by Peer Manager. |
| **Unauthenticated VNC access** | VNC server has no password but is only reachable via Docker internal network. All access goes through FastAPI WebSocket proxy which requires valid JWT. |
| **WebSocket hijacking** | JWT validated on WebSocket upgrade. Session ownership verified (user_id must match). |
| **Resource exhaustion (fork bomb, crypto mining)** | Container resource limits: `mem_limit=2g`, `cpu_quota=100000` (1 core), `pids_limit=256`. |
| **Persistent malware in container** | Containers are ephemeral; destroyed on lab stop. No writable volumes except optional `~/data`. |
| **Clipboard exfiltration** | Clipboard sync is manual (via noVNC panel), not automatic. Students must explicitly paste. |

#### Container Hardening

```python
docker_client.containers.run(
    "opencyberrange/rangebox",
    security_opt=["no-new-privileges:true"],
    cap_drop=["ALL"],
    cap_add=["NET_RAW", "NET_ADMIN"],  # Required for nmap, tcpdump
    pids_limit=256,
    mem_limit="2g",
    memswap_limit="2g",       # No swap; hard limit
    cpu_period=100000,
    cpu_quota=100000,          # 1.0 CPU core
    read_only=False,           # Tools need /tmp, /var
    shm_size="256m",           # For browser/GUI shared memory
)
```

**`NET_RAW` and `NET_ADMIN`** are required because pentesting tools need raw
sockets (nmap SYN scan, tcpdump packet capture). This is an intentional tradeoff;
students need these capabilities to complete labs. The container's network is
isolated to the lab subnet, limiting the blast radius.

---

## 6. Resource Sizing

### Per-RangeBox Container

| Resource | Idle (desktop only) | Light use (nmap, gobuster) | Heavy use (Metasploit + Burp) |
|----------|--------------------|-----------------------------|-------------------------------|
| **RAM** | ~350 MB | ~600 MB | ~1.5 GB |
| **CPU** | ~0.05 cores | ~0.3 cores | ~0.8 cores |
| **Disk** | 0 (image layers shared) | ~50 MB temp files | ~200 MB temp files |
| **Network** | ~1 KB/s (VNC idle) | ~50 KB/s (VNC active typing) | ~200 KB/s (VNC heavy GUI) |

### Server Capacity Planning

| Server Spec | Max Concurrent RangeBoxes | Notes |
|-------------|------------------------|-------|
| 8 GB RAM, 4 cores | ~5-8 students | Development/testing only |
| 16 GB RAM, 8 cores | ~12-15 students | Small class |
| 32 GB RAM, 16 cores | ~25-30 students | Medium class |
| 64 GB RAM, 32 cores | ~50-60 students | Large class or multiple sections |

**Note:** These numbers include headroom for target containers (typically
128-256 MB each). The RangeBox image layers are shared across all instances via
Docker's copy-on-write filesystem, so disk usage scales minimally.

### Image Build & Pull Times

| Operation | Time | Notes |
|-----------|------|-------|
| Initial `docker build` | ~10-15 min | One-time, cached after |
| `docker pull` (compressed) | ~3-5 min | ~1.5 GB compressed |
| Container start (image cached) | ~3-5 seconds | Xvfb + XFCE + VNC startup |
| noVNC usable in browser | ~8-12 seconds total | From "Start Lab" click to interactive desktop |

---

## 7. Implementation Plan

### Phase 1: Core RangeBox (MVP)

**Goal:** Student can start a lab and get a working Kali desktop in the browser.

| Step | Task | Files Modified/Created | Effort |
|------|------|----------------------|--------|
| 1.1 | Build RangeBox Docker image | `RangeBox/Dockerfile`, `RangeBox/entrypoint.sh` | 1 day |
| 1.2 | Test image locally (manual `docker run`) |; | 0.5 day |
| 1.3 | Modify `docker_manager.py` to spawn RangeBox alongside labs | `docker_manager.py` | 1 day |
| 1.4 | Add `rangebox_enabled` column to LabSession model | `models.py`, migration | 0.5 day |
| 1.5 | Create `/api/rangebox/` router with WebSocket proxy | `routers/rangebox.py` (new) | 2 days |
| 1.6 | Update Nginx config for WebSocket proxy | `nginx.conf` | 0.5 day |
| 1.7 | Build `RangeBox.vue` component with noVNC | `RangeBox.vue` (new), `package.json` | 2 days |
| 1.8 | Integrate RangeBox into lab exercise view | `Curriculum.vue` or exercise views | 1 day |
| 1.9 | Add connection method chooser to lab start UI | exercise view modification | 0.5 day |
| 1.10 | Modify lab cleanup to destroy RangeBox containers | `docker_manager.py` | 0.5 day |
| 1.11 | End-to-end testing |; | 1 day |

**Total Phase 1: ~10 days**

### Phase 2: Polish & UX

| Step | Task | Effort |
|------|------|--------|
| 2.1 | Fullscreen mode with proper scaling | 0.5 day |
| 2.2 | Clipboard sync panel | 0.5 day |
| 2.3 | Connection status indicator (connected/reconnecting/disconnected) | 0.5 day |
| 2.4 | Auto-reconnect on WebSocket drop | 0.5 day |
| 2.5 | RangeBox container health monitoring in admin dashboard | 1 day |
| 2.6 | Instructor view: which students are using RangeBox vs. VPN | 0.5 day |

**Total Phase 2: ~3.5 days**

### Phase 3: Hardening & Scale

| Step | Task | Effort |
|------|------|--------|
| 3.1 | Container resource limits (per-lab configurable) | 0.5 day |
| 3.2 | Graceful handling of server resource exhaustion | 1 day |
| 3.3 | RangeBox container image pre-pull on server startup | 0.5 day |
| 3.4 | Persistent `~/data` volume across lab restarts | 1 day |
| 3.5 | File upload/download integration | 1 day |
| 3.6 | Security audit: container escape testing, network isolation verification | 2 days |

**Total Phase 3: ~6 days**

### Phase 4: Terminal-Only Mode (Optional)

| Step | Task | Effort |
|------|------|--------|
| 4.1 | Add xterm.js + ttyd to RangeBox image | 0.5 day |
| 4.2 | Build `RangeBoxTerminal.vue` component | 1 day |
| 4.3 | Add mode toggle (Desktop / Terminal) to UI | 0.5 day |

**Total Phase 4: ~2 days**

---

## 8. Testing Strategy

### Unit Tests

| Test | Description |
|------|-------------|
| `test_rangebox_spawn` | RangeBox container created with correct image, network, labels, resource limits |
| `test_rangebox_ip_assignment` | Container gets IP `.254` on the correct subnet |
| `test_rangebox_cleanup` | Container destroyed on lab stop, session expiry |
| `test_rangebox_auth` | WebSocket connection rejected without valid JWT |
| `test_rangebox_session_ownership` | User A cannot connect to User B's RangeBox |

### Integration Tests

| Test | Description |
|------|-------------|
| `test_rangebox_network_access` | RangeBox can reach lab targets (ping, nmap) |
| `test_rangebox_network_isolation` | RangeBox cannot reach other users' subnets |
| `test_rangebox_tools_available` | nmap, gobuster, hydra, python3, etc. are installed and executable |
| `test_rangebox_vnc_connects` | noVNC client successfully renders desktop |
| `test_rangebox_survives_lab_extend` | Session extension doesn't restart RangeBox |

### Manual QA Checklist

- [ ] Start lab with RangeBox → desktop appears in <15 seconds
- [ ] Run `nmap -sV 10.100.{uid}.17` → scans target successfully
- [ ] Submit flag from browser (alongside RangeBox) → flag accepted
- [ ] Stop lab → RangeBox container destroyed, no orphans
- [ ] Session expires → RangeBox container destroyed
- [ ] Two students start same lab → each has isolated RangeBox, can't see each other
- [ ] Clipboard copy/paste works (host → RangeBox and RangeBox → host)
- [ ] Fullscreen mode works and scales properly
- [ ] Reconnect after network blip (close laptop lid, reopen)
- [ ] Browser refresh reattaches to running RangeBox (doesn't create new one)

---

## 9. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Server RAM exhaustion with many concurrent RangeBoxes** | Medium | High; all students lose access | Enforce max concurrent RangeBoxes server-wide. Queue excess requests. Show "server busy" message. |
| **WebSocket drops behind Cloudflare/corporate proxies** | Medium | Medium; student must reconnect | Auto-reconnect in noVNC client. Cloudflare WebSocket timeout is 100s idle; send keepalive pings. |
| **Slow image pull on first deploy** | Low | Low; one-time 5-min delay | Pre-pull image during server provisioning. Include in `prebuild-labs.sh`. |
| **noVNC latency on slow connections** | Medium | Medium; poor UX | Offer terminal-only mode (Phase 4) as fallback. Compress VNC with ZRLE encoding. |
| **Student container escape via pentesting tools** | Low | High; host compromise | seccomp profile, AppArmor, drop all caps except NET_RAW/NET_ADMIN. Regular Docker security updates. |
| **Metasploit uses too much RAM, OOM kills container** | Medium | Low; only affects that student | Set `mem_limit=2g`. Metasploit is optional; lighter labs don't need it. |

---

## 10. Success Metrics

| Metric | Current (VPN) | Target (RangeBox) | How to Measure |
|--------|--------------|-----------------|----------------|
| **Time from "Start Lab" to first command** | ~60 min (with setup) | <15 seconds | Timestamp: lab spawn → first VNC frame rendered |
| **Students completing setup without help** | ~60% | ~99% | Support ticket count for setup issues |
| **Students blocked by hardware/network** | ~15% | ~0% (browser only) | Survey / support tickets |
| **Lab completion rate** | Baseline | +20% improvement | LabCompletion records / enrolled students |
| **Server cost per concurrent student** | $0 (student's hardware) | ~$0.05-0.10/hr (RAM+CPU) | Infrastructure monitoring |

---

## 11. Open Questions

| # | Question | Options | Recommendation |
|---|----------|---------|----------------|
| 1 | Should RangeBox be the default, or should students choose? | (a) Default to RangeBox, VPN as advanced option. (b) Always ask. | (a); Default to RangeBox. Minimize friction. |
| 2 | Should RangeBox auto-start with the lab, or be a separate button? | (a) Auto-start with lab. (b) "Launch RangeBox" button after lab starts. | (a); Auto-start. One click should get you hacking. |
| 3 | Should we include Metasploit in the base image? | (a) Always. (b) Only for advanced labs. (c) Separate "heavy" image variant. | (c); Two image tiers: `rangebox:lite` (~1.5GB) and `rangebox:full` (~3GB with Metasploit+Burp). Labs specify which they need. |
| 4 | Maximum concurrent RangeBoxes per server? | Depends on hardware. | Start with 20, monitor RAM usage, adjust. Expose as admin setting. |
| 5 | Should instructors be able to view/observe student RangeBoxes? | (a) Yes; live view for debugging. (b) No; privacy. | (a); But only for instructors of the student's enrolled course. Useful for office hours. |

---

## 12. Appendix

### A. Tool Inventory for RangeBox Lite Image

The lite image includes 47 tools covering all 8 tracks and 151 exercises.
Students using their own Kali VM will have these tools available natively.
RangeBox provides the same toolset in a browser-based environment for
students who prefer not to maintain a local VM.

**Reconnaissance & Enumeration:**
nmap, masscan, gobuster, dirb, nikto, whatweb, enum4linux, smbclient,
smbmap, rpcclient, dnsrecon, ldapsearch

**Active Directory & Windows:**
netexec (CrackMapExec successor), evil-winrm, rpcclient

**Exploitation:**
metasploit-framework (full image only), sqlmap

**Remote Access:**
xfreerdp, evil-winrm, openssh-client (ssh, scp, sftp), sshpass, ftp

**Password Attacks:**
hydra, medusa, john, hashcat

**Web & Networking:**
curl, wget, netcat-openbsd, ncat, socat, tcpdump, firefox-esr

**Packet Analysis:**
tshark, wireshark

**Database Clients:**
mysql (default-mysql-client), mssqlclient.py (via Impacket)

**SNMP:**
snmpwalk, snmpget, onesixtyone

**Forensics & Analysis:**
binwalk, foremost, exiftool, sleuthkit (mmls, fls, icat, tsk_recover),
volatility3 (vol3)

**Network Defense:**
suricata

**Scripting & Development:**
python3, python3-pip, impacket, requests, beautifulsoup4, git

**Editors & Terminal:**
vim, nano, tmux

**Utilities:**
jq, xxd, file, unzip, strings, base64, grep, sed, awk

> **Note on Autopsy:** The GUI forensic tool Autopsy is not included in
> the RangeBox due to its size (~500MB+, requires Java). Forensics exercises
> use Sleuth Kit CLI tools (pre-installed) as the primary path. Students
> working from their own machine can optionally install Autopsy locally.

> **Note on Internet Access:** RangeBox containers are network-isolated to
> the lab environment. External internet access is disabled by design.
> All required tools are pre-installed. Students cannot use apt install
> or pip install to add packages at runtime.

### B. Estimated Bandwidth Per Student

| Activity | Bandwidth | Notes |
|----------|-----------|-------|
| Idle desktop (cursor blinks) | ~1-5 KB/s | ZRLE encoding, minimal updates |
| Active terminal (typing/scrolling) | ~10-50 KB/s | Text regions compress well |
| Scrolling web page in Firefox | ~100-500 KB/s | Many pixel changes |
| Full screen video/animation | ~1-5 MB/s | Worst case, unlikely in labs |
| **Typical lab usage** | **~20-100 KB/s average** | Mix of terminal + occasional GUI |

For 30 concurrent students at typical usage: ~1-3 MB/s total server egress.

### C. UbuntuBox: General-Purpose Desktop Variant

In addition to the Kali-based RangeBox, OpenCyberRange provides an **UbuntuBox**: a browser-based Ubuntu 22.04 XFCE desktop for exercises that don't require pentesting-specific tools.

**Use cases:**
- Blue-team / SOC exercises (log analysis, SIEM work)
- Programming and scripting labs
- System administration exercises
- Students who prefer a standard Ubuntu environment

**Image:** `opencyberrange/ubuntubox:latest`
**Base:** `ubuntu:22.04`
**Size:** ~1 GB (compressed)
**User:** `student` (passwordless sudo)

**Build:**
```bash
docker build -t opencyberrange/ubuntubox:latest UbuntuBox/
```

**Pre-installed tools:** nmap, curl, wget, netcat, socat, tcpdump, python3, git, build-essential, vim, nano, tmux, firefox, htop, tree, jq, openssh-client.

The UbuntuBox uses the same noVNC architecture (Xvfb → XFCE4 → x11vnc → websockify) and shares the same spawn, networking, and lifecycle management as RangeBox. Select it by passing `image="ubuntu"` to the spawn functions or by setting the `UBUNTUBOX_IMAGE` environment variable.
