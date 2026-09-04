# Shared Virtual Machines - Admin Guide

Shared VMs are persistent Windows or Linux virtual machines that run alongside the platform and are used by lab exercises. Unlike per-student RangeBox containers, shared VMs are long-lived infrastructure that all students connect to during exercises.

---

## Architecture

Shared VMs run inside Docker containers using [Dockur](https://github.com/dockur/windows), which runs a full Windows (or Linux) OS inside QEMU. Each VM gets:

- Its own Docker network (isolated subnet)
- A persistent storage volume (survives container restarts)
- A built-in noVNC web viewer on port 8006

### Containers

| Container | Purpose | Network |
|-----------|---------|---------|
| `ocr-windows-ad` | Windows Server 2022 Domain Controller (AD DS, DNS, DHCP) | `10.150.1.0/24` |
| `ocr-windows-target` | Windows 10 Target for forensics/enumeration labs | `10.150.0.0/24` |

### How Students Access Shared VMs

Students connect to shared VMs through their own Kali machine (via VPN) or a RangeBox. When a lab exercise starts, the backend creates a per-user lab network and attaches the shared VM container to it with a lab-facing IP.

### Port Forwarding (iptables DNAT)

Dockur runs Windows inside QEMU on an internal bridge network (172.30.0.0/24). The Windows guest IP is `172.30.0.3`. To make Windows services reachable on the lab network, the platform adds iptables rules inside the container:

- **PREROUTING DNAT**: Forwards specific TCP ports (e.g., 135, 139, 445, 3389, 5985) and all UDP from the lab-facing IP to the QEMU guest at `172.30.0.3`.
- **POSTROUTING MASQUERADE**: Rewrites the source IP so the Windows guest sees traffic from its own subnet gateway (`172.30.0.1`). Without this, Windows Firewall blocks SMB/RPC from "unknown" source networks.
- **INPUT DROP**: Blocks QEMU management ports (5700, 5900, 7100, 8006, 8004) on lab-facing IPs so students cannot access the VNC console or hypervisor interfaces.

This uses kernel-level forwarding (not socat), so nmap service detection and other fingerprinting tools work transparently.

---

## First-Time Provisioning

### Important: Initial Setup Takes Time

The **first time** a Windows VM is provisioned, Dockur must install Windows from an ISO image. This process includes:

1. Extracting the ISO
2. Building a virtual disk
3. Running the Windows installer inside QEMU
4. Applying automated configuration (unattended install)
5. Running OEM setup scripts (role install, AD DS promotion, etc.)
6. For two-phase VMs (AD): reboot, Phase 2 creates AD objects
7. WinRM verification confirms roles and objects before committing

**With KVM acceleration**: ~8-15 minutes
**Without KVM (software emulation)**: ~1-3 hours

> **Why so slow without KVM?** Dockur uses QEMU to emulate x86 hardware. With KVM, the host CPU runs VM instructions natively. Without KVM, every CPU instruction is software-emulated at roughly 1/10th speed. If your server is itself a virtual machine, KVM passthrough (nested virtualization) must be enabled by your hypervisor.

### Checking KVM Availability

```bash
# On the host machine
ls -la /dev/kvm
# If this file exists, KVM is available

# Check if running inside a VM
systemd-detect-virt
# If this returns "kvm", "vmware", etc., you're in a VM
# and need nested virtualization enabled
```

### Subsequent Provisions Are Fast

After the first successful provision, the system commits a snapshot of the configured VM as a Docker image (`ocr-windows-ad:configured`). Future provisions use this pre-built image, which means:

- **First provision**: 15 min (KVM) or 1-3 hours (no KVM)
- **Subsequent provisions**: Under 1 minute (just boots from snapshot)

This means if a VM gets corrupted or needs resetting, Delete + Provision is quick and safe.

---

## Managing Shared VMs

### Admin Panel (Shared VMs Tab)

Navigate to **Admin > System > Shared VMs** to manage all shared VMs.

#### VM Status Indicators

| Status | Badge | Meaning |
|--------|-------|---------|
| Ready | Green | VM is running, Windows is up, RDP is accessible |
| Booting | Yellow | Container is running but Windows is still starting |
| Stopped | Grey | Container exists but is not running (normal shutdown) |
| Stopped | Red | Container exited with an error code |
| Not Provisioned | Grey | No container exists, needs provisioning |

#### Health Notes

The platform automatically detects common issues and displays guidance below each VM card:

| Scenario | Guidance |
|----------|----------|
| Booting without KVM (<2 hours) | "VM is installing without KVM acceleration - this is normal but slow" |
| Booting without KVM (>2 hours) | "Check Logs for progress. Try Stop -> Start. Last resort: Delete and Provision" |
| Booting with KVM (>15 min) | "Check Logs for errors. Try Stop -> Start" |
| Stopped (normal exit 0/137/143) | No banner; grey badge is sufficient |
| Stopped (error exit) | "VM exited with error (code X). Check Logs for details..." |

#### Actions

| Button | When Available | What It Does |
|--------|---------------|--------------|
| **Provision** | Not Provisioned | Creates container and starts Windows install |
| **Start** | Stopped | Starts the existing container |
| **Stop** | Running/Booting | Stops the container (preserves data) |
| **VNC** | Running | Opens a browser-based console to see the Windows desktop |
| **Logs** | Any state | Shows container logs for troubleshooting |
| **Delete** | Running/Stopped | Removes the container (volume preserved for re-provision) |
| **Full Delete** | When image or volume exists | Removes container, committed image, AND storage volume (forces full fresh provision) |

### VNC Console

The VNC button opens a browser-based remote desktop viewer powered by noVNC. This connects through the platform's WebSocket proxy, so it works from any browser with access to the platform (no direct network access to the VM required).

Features:
- **Clipboard**: Paste text into the VM
- **Ctrl+Alt+Del**: Send the key combination to the VM
- **Auto-scaling**: Desktop resizes to fit the browser window

### Creating a New VM Definition

Click **+ New Shared VM** to open the definition form:

1. Choose **Windows** or **Linux** type
2. Set the container name (e.g., `ocr-windows-dc2`)
3. Configure resources (RAM, CPU cores)
4. Set the subnet (must not overlap with existing VMs)
5. For Windows: specify OS version, local ISO path, setup script
6. Click **Save**, then **Provision**

### Editing a VM Definition

Click the pencil icon on a VM card to edit its definition. Note:
- Fields are **locked** while the VM is running; stop it first
- Changes to resources (RAM, CPU) require a Delete + Provision to take effect

---

## Troubleshooting

### VM Stuck on "Booting" Forever

**Cause**: The backend container wasn't connected to the VM's Docker network, so port probes can't reach the VM.

**Fix**: The platform auto-connects the backend to VM networks during status checks. If this fails, manually connect:

```bash
docker network connect ocr-windows-ad ocr-backend
docker network connect ocr-windows-target ocr-backend
```

### VM Shows "Booting" But Desktop Is Actually Up

Same networking issue as above. After connecting the backend to the VM network, the status should update to "Ready" on the next poll.

### Windows Install Takes Hours

**Cause**: No KVM acceleration. The VM is running in pure software emulation.

**Options**:
1. **Wait**: first install is slow, but subsequent provisions use the committed image and are fast
2. **Enable KVM**: if your server's hypervisor supports nested virtualization, enable it and ensure `/dev/kvm` exists
3. **Pre-build on another machine**: install on a KVM-enabled machine, commit the image, export/import the Docker image to your server

### AD Server Credentials Don't Work After Interrupted Setup

**Cause**: If the AD container was killed during DC promotion (Phase 1 of AD setup), the local SAM database has been converted to Active Directory but AD DS didn't fully initialize. No authentication method will work.

**Fix**: Delete the container AND its storage volume, then re-provision:

```bash
docker stop ocr-windows-ad
docker rm ocr-windows-ad
docker volume rm ocr-windows-ad-storage
# Then click "Provision" in the UI
```

### VNC Shows Blank Screen

**Cause**: Windows hasn't finished booting yet, or the QEMU display server hasn't initialized.

**Fix**: Wait a few minutes. For first-time installs, the display may take 5-10 minutes to appear even after the container starts.

---

## VM Definitions (Database)

VM definitions are stored in the `shared_vm_definitions` table:

| Field | Purpose |
|-------|---------|
| `container_name` | Docker container name (e.g., `ocr-windows-ad`) |
| `display_name` | Human-readable name shown in UI |
| `vm_type` | `windows` or `linux` |
| `os_version` | Dockur VERSION env (e.g., `win2022-eval`, `win10`) |
| `image` | Docker image (default: `dockurr/windows`) |
| `ram` | RAM allocation (e.g., `4G`, `6G`) |
| `cpu_cores` | Virtual CPU cores (e.g., `2`, `4`) |
| `subnet` | Docker network subnet (e.g., `10.150.1.0/24`) |
| `local_iso` | Path to local ISO file (avoids in-container download) |
| `setup_script` | Path to PowerShell setup script |
| `two_phase` | Whether setup uses two-phase reboot (e.g., AD DS promotion) |
| `committed_tag` | Tag for the committed image snapshot (default: `configured`) |

### Current Definitions

| VM | RAM | CPU | Subnet | Notes |
|----|-----|-----|--------|-------|
| `ocr-windows-ad` | 8G | 6 | `10.150.1.0/24` | AD DS, DNS, DHCP. Heavier workload needs more resources |
| `ocr-windows-target` | 4G | 2 | `10.150.0.0/24` | Windows 10 target for forensics labs |

---

## Server Requirements

### Minimum (tested and working)

10 CPU cores, 24 GB RAM, 80 GB free storage. The shared VMs alone use 6+2=8 cores and 8+4=12 GB RAM, but the server also runs the platform, database, VPN, SOC environment, and student lab containers. Suitable for small labs with under ~15 concurrent students. First-time provisioning takes 1–3 hours without KVM but only happens once; subsequent provisions use the committed snapshot and complete in under a minute.

### Recommended

12–16 CPU cores, 32–64 GB RAM, 150 GB+ free storage. Provides headroom for concurrent student sessions, SOC environments, and future VMs.

### KVM / Nested Virtualization

If the server is a VM (Proxmox, VMware, Hyper-V), setting CPU type to `host` (Proxmox) or enabling "Expose hardware assisted virtualization" (VMware/Hyper-V) enables KVM inside the VM. This reduces first-time provisioning from hours to ~15–20 minutes and improves runtime VM performance.

```bash
ls -la /dev/kvm    # If this exists, KVM is active
```

### Resource Allocation Bar

The admin UI Shared VMs panel shows a resource allocation summary (CPU cores and RAM) comparing total VM allocations to the server's capacity. The bar turns yellow above 50% and red above 75%, with a warning when running all VMs simultaneously may impact platform performance.

---

## API Reference

### Admin Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/shared-vms` | List all shared VMs with status |
| GET | `/api/admin/shared-vm-definitions` | List all VM definitions |
| POST | `/api/admin/shared-vm-definitions` | Create a new VM definition |
| PUT | `/api/admin/shared-vm-definitions/{id}` | Update a VM definition |
| DELETE | `/api/admin/shared-vm-definitions/{id}` | Delete a VM definition |
| POST | `/api/admin/shared-vms/provision` | Start provisioning a VM |
| POST | `/api/admin/shared-vms/{name}/start` | Start a stopped VM |
| POST | `/api/admin/shared-vms/{name}/stop` | Stop a running VM |
| DELETE | `/api/admin/shared-vms/{name}` | Delete a VM container (add `?purge=true` for Full Delete) |
| POST | `/api/admin/shared-vms/provision/cancel` | Cancel a running provisioning job |
| GET | `/api/admin/shared-vms/provision/active` | Get active provisioning run status |
| GET | `/api/admin/shared-vm-definitions/server-resources` | Get server CPU/RAM vs VM allocations |
| GET | `/api/admin/shared-vms/{name}/logs` | Get container logs |
| GET | `/api/admin/shared-vms/{name}/vnc-url` | Get direct VNC URL (lab server only) |
| WS | `/api/admin/shared-vms/{name}/vnc` | WebSocket VNC proxy (works remotely) |

### Status Response Fields

```json
{
  "name": "ocr-windows-ad",
  "exists": true,
  "status": "running",
  "guest_status": "ready",
  "native_ip": "10.150.1.2",
  "vnc_available": true,
  "uptime_seconds": 3600,
  "exit_code": null,
  "health_note": null,
  "has_purge_data": true
}
```
