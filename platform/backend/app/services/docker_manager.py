"""
Docker container and network management for lab environments
Handles creation, management, and cleanup of Docker containers and networks
"""

import docker
import yaml
import logging
import os
import subprocess
import tempfile
import time
import threading
from typing import Dict, List, Optional
from datetime import datetime, timedelta, timezone


logger = logging.getLogger(__name__)

# Backend container name (env-overridable so a renamed/standalone instance
# attaches ITSELF to lab/rangebox networks for the VNC proxy, not the live one).
import os as _os
_BACKEND_CONTAINER = _os.environ.get("OCR_BACKEND_CONTAINER", "ocr-backend")


def _shared_container_native_subnet(client, container_name: str) -> str | None:
    """Look up the IPAM subnet of a shared VM's native Docker network."""
    try:
        net = client.networks.get(container_name)
        configs = net.attrs.get("IPAM", {}).get("Config") or []
        if configs:
            return configs[0].get("Subnet")
    except Exception:
        return None
    return None

# ── Shared container status cache ───────────────────────────────────
# Prevents multiple concurrent polls from each doing slow socket checks.
# TTL of 5 seconds — stale data is acceptable for a status indicator.
_shared_status_cache: Dict[str, dict] = {}
_shared_status_cache_lock = threading.Lock()
_SHARED_STATUS_TTL = 5  # seconds


class RangeBoxCapacityError(Exception):
    """Raised when the server has reached its maximum concurrent RangeBox limit."""
    pass


_host_kvm_available: Optional[bool] = None


def host_kvm_available() -> bool:
    """Whether the host exposes /dev/kvm (needed by shared-VM labs).

    Probed once per process via a throwaway container (the backend container
    itself has no /dev/kvm mount, so a direct stat cannot answer this). KVM
    presence does not change while the host runs, so the result is cached.
    """
    global _host_kvm_available
    if _host_kvm_available is None:
        try:
            client = docker.from_env()
            client.containers.run(
                "alpine", "test -e /dev/kvm",
                devices=["/dev/kvm"], remove=True,
            )
            _host_kvm_available = True
        except Exception:
            _host_kvm_available = False
    return _host_kvm_available


def get_track_directory_name(track_slug: str) -> str:
    """
    Find the actual track directory name by matching track slug.
    Handles cases where directory name doesn't match slug (e.g., "Capital Flow" vs "capitalflow").
    
    Args:
        track_slug: Track slug from lab (e.g., "capitalflow", "web", "windows")
        
    Returns:
        Actual directory name (e.g., "Capital Flow", "Web", "Windows")
    """
    track_slug = track_slug.lower()
    labs_dir = "/labs"
    
    # First, try to find by scanning directories
    if os.path.exists(labs_dir):
        for dir_name in os.listdir(labs_dir):
            dir_path = os.path.join(labs_dir, dir_name)
            if not os.path.isdir(dir_path) or dir_name.startswith('.'):
                continue
            
            # Check if this directory contains a lab subdirectory with matching track slug
            try:
                for lab_dir_name in os.listdir(dir_path):
                    if lab_dir_name.startswith(f"{track_slug}-") and os.path.isdir(os.path.join(dir_path, lab_dir_name)):
                        return dir_name
            except (OSError, PermissionError):
                continue
    
    # Fallback to mapping for known tracks
    track_name_map = {
        "capitalflow": "Capital Flow",
        "refinery": "Refinery",
        "web": "Web",
        "windows": "Windows",
        "linux": "Linux",
        "network": "Network"
    }
    return track_name_map.get(track_slug, track_slug.capitalize())


def get_vpn_client_suffix(user_id: int) -> int:
    """
    Calculate the host-part octet for a user inside their isolated lab /24 subnet.
    Returns a value between 10-249 to stay within valid IP range.

    This is ONLY used for container IPs within per-user lab networks (each user
    gets their own /24).  Collisions across users (e.g. user 1 and 241 both
    mapping to .11) are harmless because they live in different subnets.

    NOT used for the global WireGuard VPN client IP — see labs.py
    get_vpn_client_ip() for that, which guarantees uniqueness across all users.
    """
    return (user_id % 240) + 10


def get_subnet_id(user_id: int, lab_slug: str = None) -> tuple:
    """
    Calculate subnet octets for a user's lab network.
    Returns a tuple (second_octet, third_octet) for building subnet 10.X.Y.0/24

    Uses both the second and third octets to support up to ~57,000 unique
    user subnets without collisions.  The usable range for each octet is
    1-254 (avoiding 0 and 255), giving 254*254 = 64,516 unique pairs.

    For backward compatibility, user_ids 1-250 keep their original mapping
    (second_octet=100, third_octet=user_id).  Higher IDs spread across
    the full 10.{second}.{third}.0/24 space within the 10.100.0.0/16
    firewall-allowed block — second_octet stays in 100-254, third_octet
    in 1-254.

    Individual container IPs within the subnet are determined by each
    service's ip_offset label in docker-compose.yml, so students still
    need to run nmap to discover which hosts are up.

    Since only one lab runs at a time per user, there are no IP conflicts.

    Examples:
      user_id=6   -> 10.100.6.0/24   (containers at 10.100.6.{ip_offset})
      user_id=42  -> 10.100.42.0/24  (containers at 10.100.42.{ip_offset})
      user_id=300 -> 10.101.46.0/24  (spreads into second octet)
    """
    if user_id <= 250:
        # Original mapping — preserves existing lab networks
        second_octet = 100
        third_octet = user_id
    else:
        # Spread across both octets: 155 values (100-254) * 254 values (1-254)
        idx = user_id - 251          # 0-based offset from first "new" user
        third_octet = (idx % 254) + 1       # 1-254
        second_octet = 100 + (idx // 254)   # starts at 100, grows upward
        # Clamp second_octet to valid range (extremely unlikely to exceed)
        if second_octet > 254:
            second_octet = 100 + (second_octet % 155)

    return (second_octet, third_octet)


class DockerManager:
    def __init__(self):
        try:
            self.client = docker.from_env()
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            self.client = None

    # Lab subnets that need isolation from the host management LAN.
    # 10.50.0.0/16 covers standalone RangeBox subnets (10.50.{x}.0/24).
    # 10.100.0.0-10.254.0.0 covers lab subnets (user_ids > 250 use 10.101+).
    # 10.200.0.0/16 covers RangeBox proxy subnets (10.200.x.0/30).
    _LAB_SUBNETS = [
        "10.100.0.0/14",   # 10.100-10.103 (user_ids 1-1265)
        "10.104.0.0/13",   # 10.104-10.111 (user_ids 1266-3795)
        "10.112.0.0/12",   # 10.112-10.127 (user_ids 3796-7875)
        "10.128.0.0/9",    # 10.128-10.255 (user_ids 7876+, also covers 10.200 proxy)
        "10.50.0.0/16",    # RangeBox standalone networks
    ]

    # Docker-internal subnets that must never be reachable from external
    # (non-Docker) interfaces.  Includes _LAB_SUBNETS plus the shared
    # container native network.
    _PROTECTED_SUBNETS = [
        "10.150.0.0/24",  # Shared containers (e.g. Dockur Windows target)
        "10.100.0.0/14",  # Student lab networks (10.100-10.103)
        "10.104.0.0/13",  # Student lab networks (10.104-10.111)
        "10.112.0.0/12",  # Student lab networks (10.112-10.127)
        "10.128.0.0/9",   # Student lab networks (10.128-10.255, includes 10.200 proxy)
        "10.50.0.0/16",   # RangeBox standalone networks
    ]

    # Maximum time (seconds) to wait for a QEMU-based shared container to boot
    _SHARED_CONTAINER_BOOT_TIMEOUT = 300  # 5 minutes

    # Default per-container resource caps for lab services, applied through the
    # compose override at spawn time so one runaway lab container cannot starve
    # the host. A compose file that declares its own mem_limit / cpus / deploy
    # limits keeps them. Env-overridable for bigger or smaller hosts.
    LAB_MEM_LIMIT = os.environ.get("LAB_MEM_LIMIT", "1g")
    LAB_CPU_LIMIT = os.environ.get("LAB_CPU_LIMIT", "1.0")

    def _ensure_shared_container_running(self, container_name: str) -> bool:
        """
        Ensure a shared container is running.  If it's stopped, start it and
        wait for the guest OS to become reachable (QEMU/Windows boot).

        Returns True if the container is running (or was started), False on error.
        """
        if not self.client:
            return False

        try:
            container = self.client.containers.get(container_name)
        except docker.errors.NotFound:
            logger.warning(f"Shared container {container_name} does not exist")
            return False

        container.reload()
        if container.status == "running":
            return True

        # Container exists but is not running — start it
        logger.info(f"Starting shared container {container_name} (was {container.status})")
        try:
            container.start()
        except Exception as e:
            logger.error(f"Failed to start shared container {container_name}: {e}")
            return False

        # Wait for the guest OS to boot by polling WinRM (port 5985) on the
        # container's native-network IP.  This works for Dockur Windows VMs
        # where the internal QEMU bridge DNATs traffic to the guest.
        container.reload()
        native_ip = None
        for net_name, net_info in container.attrs.get("NetworkSettings", {}).get("Networks", {}).items():
            if net_name == container_name:
                native_ip = net_info.get("IPAddress")
                break
        if not native_ip:
            # Fall back to first available IP
            for net_info in container.attrs.get("NetworkSettings", {}).get("Networks", {}).values():
                native_ip = net_info.get("IPAddress")
                if native_ip:
                    break

        if native_ip:
            logger.info(f"Waiting for {container_name} guest OS to boot at {native_ip}:5985 ...")
            deadline = time.time() + self._SHARED_CONTAINER_BOOT_TIMEOUT
            while time.time() < deadline:
                try:
                    import socket
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(3)
                    result = sock.connect_ex((native_ip, 5985))
                    sock.close()
                    if result == 0:
                        logger.info(f"Shared container {container_name} guest OS is ready")
                        return True
                except Exception:
                    pass
                time.sleep(10)
            logger.warning(f"Shared container {container_name} guest OS did not respond within {self._SHARED_CONTAINER_BOOT_TIMEOUT}s — proceeding anyway")
        return True

    def _stop_shared_container_if_idle(self, container_name: str):
        """
        Stop a shared container if no lab networks are connected to it.
        Only the container's own native network should remain.
        """
        if not self.client:
            return

        try:
            container = self.client.containers.get(container_name)
        except docker.errors.NotFound:
            return

        container.reload()
        if container.status != "running":
            return

        # Count networks — the container always has its native network.
        # If it has MORE than that, at least one lab is still using it.
        networks = container.attrs.get("NetworkSettings", {}).get("Networks", {})
        lab_networks = [n for n in networks.keys() if n.startswith("lab_")]
        if lab_networks:
            logger.debug(f"Shared container {container_name} still connected to {len(lab_networks)} lab network(s) — keeping alive")
            return

        # No lab networks — shut down gracefully.
        # Dockur/QEMU handles ACPI shutdown signals from docker stop, so a
        # generous timeout lets Windows shut down cleanly before being killed.
        logger.info(f"No lab networks remain on {container_name} — stopping container")
        try:
            container.stop(timeout=90)
            logger.info(f"Shared container {container_name} stopped")
        except Exception as e:
            logger.warning(f"Failed to stop shared container {container_name}: {e}")

    def get_shared_container_status(self, container_name: str) -> Dict:
        """
        Return status information for a shared container.
        Used by the frontend to show VM state in the lab UI.
        Results are cached for 5 seconds to avoid redundant socket checks
        when multiple tabs/students poll concurrently.
        """
        # Check cache first
        with _shared_status_cache_lock:
            cached = _shared_status_cache.get(container_name)
            if cached and time.time() - cached["_ts"] < _SHARED_STATUS_TTL:
                return {k: v for k, v in cached.items() if k != "_ts"}

        result = self._get_shared_container_status_uncached(container_name)

        # Store in cache
        with _shared_status_cache_lock:
            _shared_status_cache[container_name] = {**result, "_ts": time.time()}

        return result

    def _get_shared_container_status_uncached(self, container_name: str) -> Dict:
        """Actual status check (uncached)."""
        if not self.client:
            return {"status": "unknown", "message": "Docker not available"}

        try:
            container = self.client.containers.get(container_name)
            container.reload()
            status = container.status  # running, exited, created, paused, etc.

            result = {
                "name": container_name,
                "status": status,
                "exists": True,
            }

            if status == "running":
                # Grab the native IP for network info
                native_ip = None
                for net_name, net_info in container.attrs.get("NetworkSettings", {}).get("Networks", {}).items():
                    if net_name == container_name:
                        native_ip = net_info.get("IPAddress")
                        if native_ip:
                            result["native_ip"] = native_ip
                        break

                # Check if the guest OS has finished booting.
                # The Dockur log message "Windows started successfully" only
                # means QEMU launched — Windows may still be installing.
                # We also verify that RDP (3389) is reachable, which confirms
                # the Windows OS is actually up and past initial setup.
                # NOTE: timeout must be very short (0.5s) because this runs
                # synchronously on the async event loop — a long timeout here
                # blocks ALL other requests to the server.
                qemu_booted = False
                try:
                    logs = container.logs(tail=50).decode("utf-8", errors="replace")
                    qemu_booted = "Windows started successfully" in logs
                except Exception:
                    pass

                if qemu_booted and native_ip:
                    import socket
                    try:
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(0.5)
                        rdp_open = sock.connect_ex((native_ip, 3389)) == 0
                        sock.close()
                    except Exception:
                        rdp_open = False
                    result["guest_status"] = "ready" if rdp_open else "booting"
                elif qemu_booted:
                    result["guest_status"] = "booting"
                else:
                    result["guest_status"] = "booting"
            return result

        except docker.errors.NotFound:
            return {"name": container_name, "status": "not_found", "exists": False}
        except Exception as e:
            return {"name": container_name, "status": "error", "message": str(e)}

    def start_shared_container(self, container_name: str) -> Dict:
        """
        Start a shared container and begin waiting for guest OS boot.
        Returns immediately with status — caller should poll get_shared_container_status.
        """
        if not self.client:
            return {"success": False, "message": "Docker not available"}

        try:
            container = self.client.containers.get(container_name)
            container.reload()
            if container.status == "running":
                return {"success": True, "message": "Already running"}
            container.start()
            return {"success": True, "message": "Starting"}
        except docker.errors.NotFound:
            return {"success": False, "message": f"Container {container_name} not found"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def stop_shared_container(self, container_name: str) -> Dict:
        """
        Stop a shared container gracefully (ACPI shutdown for QEMU guests).
        """
        if not self.client:
            return {"success": False, "message": "Docker not available"}

        try:
            container = self.client.containers.get(container_name)
            container.reload()
            if container.status != "running":
                return {"success": True, "message": "Already stopped"}
            container.stop(timeout=90)
            return {"success": True, "message": "Stopped"}
        except docker.errors.NotFound:
            return {"success": False, "message": f"Container {container_name} not found"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ------------------------------------------------------------------ #
    #  Shared VM Lifecycle Methods                                         #
    # ------------------------------------------------------------------ #




    def cleanup_exercise_containers(self, user_id: int, lab_slug: str):
        """
        Partial teardown: remove only per-exercise containers while keeping
        the shared VM bridge network intact.
        """
        if not self.client:
            return

        project_name = f"lab_{user_id}_{lab_slug}".lower().lower()
        track_slug = lab_slug.split("-")[0].lower()
        track_dir_name = get_track_directory_name(track_slug)
        lab_dir = f"/labs/{track_dir_name}/{lab_slug}"
        compose_file = os.path.join(lab_dir, "docker-compose.yml")

        # Parse compose to check for exercise-specific services
        try:
            with open(compose_file) as f:
                compose_data = yaml.safe_load(f.read()) or {}
        except Exception:
            compose_data = {}

        services = compose_data.get("services") or {}

        # Tear down docker-compose project containers (if any)
        if services and os.path.exists(compose_file):
            try:
                subprocess.run(
                    ["docker", "compose", "-f", compose_file, "-p", project_name,
                     "down", "-v", "--timeout", "15"],
                    cwd=lab_dir,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                logger.info(f"Cleaned up exercise containers for {lab_slug}")
            except Exception as e:
                logger.warning(f"Exercise container cleanup failed for {lab_slug}: {e}")

        # Always remove the exercise network (shared-only labs create one too).
        # Disconnect any shared VMs still attached before removing.
        for net_name in [f"lab_{user_id}_{lab_slug}".lower(), f"{project_name}_default"]:
            try:
                network = self.client.networks.get(net_name)
                network.reload()
                containers = network.attrs.get("Containers", {})
                for container_id, cinfo in containers.items():
                    cname = cinfo.get("Name", container_id)
                    try:
                        network.disconnect(cname, force=True)
                        logger.info(f"Disconnected {cname} from {net_name}")
                    except Exception:
                        pass
                network.remove()
                logger.info(f"Removed exercise network {net_name}")
            except docker.errors.NotFound:
                pass
            except Exception as e:
                logger.warning(f"Failed to remove exercise network {net_name}: {e}")

        # Disconnect standalone RangeBox from exercise network
        self.unbridge_standalone_rangebox_from_lab(user_id, lab_slug)
        # Destroy any RangeBox associated with this exercise
        self.destroy_rangebox(user_id, lab_slug)

    def _setup_iptables_forwarding(self, container, container_name: str,
                                    bind_ip: str, guest_ip: str,
                                    forward_ports: list):
        """Set up iptables DNAT forwarding from lab-facing IP to QEMU guest IP.

        Uses kernel-level DNAT rather than socat so that nmap service detection
        and other tools that inspect raw TCP behaviour work transparently.
        Dockur already uses iptables DNAT on its native network interface —
        this extends the same approach to every lab-facing IP.
        """
        # Kill any legacy socat forwarders for this bind_ip (transition cleanup)
        container.exec_run(
            ["sh", "-c", f"pkill -f 'socat.*bind={bind_ip}' 2>/dev/null || true"],
            demux=False,
        )

        ports_csv = ",".join(str(int(p)) for p in forward_ports)

        # QEMU management ports that must NOT be exposed on lab networks.
        # Dockur excludes these from its own native-network DNAT rule.
        qemu_mgmt_ports = "5700,5900,7100,8006,8004"

        # Idempotent: -C checks if rule exists, || -A adds it only if missing
        script_lines = [
            # Block QEMU management ports (VNC, noVNC, SPICE, etc.) on lab IP
            f'iptables -C INPUT -d {bind_ip} -p tcp -m multiport '
            f'--dports {qemu_mgmt_ports} -j DROP 2>/dev/null || '
            f'iptables -A INPUT -d {bind_ip} -p tcp -m multiport '
            f'--dports {qemu_mgmt_ports} -j DROP',
            # TCP DNAT for the specified ports
            f'iptables -t nat -C PREROUTING -d {bind_ip} -p tcp -m multiport '
            f'--dports {ports_csv} -j DNAT --to-destination {guest_ip} 2>/dev/null || '
            f'iptables -t nat -A PREROUTING -d {bind_ip} -p tcp -m multiport '
            f'--dports {ports_csv} -j DNAT --to-destination {guest_ip}',
            # UDP DNAT (catches NetBIOS 137/138 and any other UDP services)
            f'iptables -t nat -C PREROUTING -d {bind_ip} -p udp '
            f'-j DNAT --to-destination {guest_ip} 2>/dev/null || '
            f'iptables -t nat -A PREROUTING -d {bind_ip} -p udp '
            f'-j DNAT --to-destination {guest_ip}',
            # MASQUERADE so the QEMU guest sees traffic from its gateway IP
            # (172.30.0.1) instead of the student's lab IP.  Without this,
            # Windows Firewall blocks SMB/RPC from "unknown" source networks.
            f'iptables -t nat -C POSTROUTING -d {guest_ip} '
            f'-j MASQUERADE 2>/dev/null || '
            f'iptables -t nat -A POSTROUTING -d {guest_ip} '
            f'-j MASQUERADE',
        ]
        script = " && ".join(script_lines)

        result = container.exec_run(["sh", "-c", script], demux=False)
        if result.exit_code != 0:
            output = result.output.decode(errors="replace").strip() if result.output else ""
            logger.warning(
                f"iptables DNAT setup in {container_name} failed "
                f"(exit {result.exit_code}): {output}"
            )
            raise RuntimeError(
                f"Failed to set up iptables DNAT in {container_name}: {output}"
            )
        logger.info(
            f"iptables DNAT: {bind_ip} tcp/{ports_csv}+udp → {guest_ip} "
            f"(MASQUERADE) in {container_name}"
        )

    def _repoint_dc_dns_a_records(self, container_name: str, lab_ip: str,
                                  aliases: List[str]) -> None:
        """
        Update an AD DC's DNS A records to point at a per-session lab IP.

        Heuristic: called when a shared container forwards port 53. We assume
        any such container is an AD DC running Windows DNS Server.

        AD's Netlogon auto-registers the DC's hostname A record against the
        dockur INTERNAL IP (172.30.X.2), which lab-side clients cannot reach.
        Tools like bloodhound-python query the DC's own DNS and fail with
        "Failed to resolve LDAP server IP" because the answer is the
        unreachable internal IP. We forcibly overwrite the A records for
        the DC's short hostname AND every alias declared in lab.yaml
        ('aliases:' under x-ocr-shared-containers) with the per-session
        lab IP.

        The setup script (setup-adpt-dc.ps1) sets RegisterDnsARecords=0 in
        the registry to prevent AD from re-overwriting our fix on the next
        DNS refresh cycle. This call still runs every spawn because the
        per-session lab IP changes each time.

        Multi-tenant note: A records can only point at one IP at a time, so
        only ONE concurrent session can use the DC by FQDN at a time. Future
        work needed for true multi-tenant. Per-session sequential testing
        works fine.
        """
        # Build short-name + zone pairs from the aliases. Aliases declared in
        # lab.yaml have the form "<short>.<zone>" (e.g.
        # "corp-dc01.corp.nordport.local"); we update each short name's A
        # record in its zone. Also update $env:COMPUTERNAME (the dockur-
        # generated DOCKERW-XXXX hostname) in every zone we touch.
        pairs: List[tuple[str, str]] = []
        zones: set[str] = set()
        for alias in (aliases or []):
            if "." in alias:
                short, zone = alias.split(".", 1)
                pairs.append((short, zone))
                zones.add(zone)
            else:
                # alias has no dot; pair with first known zone (added in second pass)
                pairs.append((alias, ""))
        # Resolve zone-less aliases to first known zone (or skip)
        resolved_pairs = [(s, z if z else next(iter(zones), "")) for s, z in pairs]
        resolved_pairs = [(s, z) for s, z in resolved_pairs if z]
        if not resolved_pairs:
            logger.info(
                f"No FQDN-style aliases declared for {container_name}; "
                f"skipping DC DNS repoint"
            )
            return

        # Build PowerShell that updates each short-name A record in its zone,
        # plus the dockur-generated $env:COMPUTERNAME against the same zone(s).
        ps_pairs = ",".join(
            f"@{{Name='{s}';Zone='{z}'}}" for s, z in resolved_pairs
        )
        ps_zones = ",".join(f"'{z}'" for z in zones)
        ps_script = (
            f"$lab_ip = '{lab_ip}'; "
            f"$pairs = @({ps_pairs}); "
            f"$zones = @({ps_zones}); "
            f"foreach ($z in $zones) {{ "
            f"  $pairs += @{{Name=$env:COMPUTERNAME;Zone=$z}} "
            f"}} "
            f"foreach ($p in $pairs) {{ "
            f"  try {{ "
            f"    Get-DnsServerResourceRecord -ZoneName $p.Zone -Name $p.Name -RRType A -ErrorAction SilentlyContinue | "
            f"      Remove-DnsServerResourceRecord -ZoneName $p.Zone -Force; "
            f"    Add-DnsServerResourceRecordA -ZoneName $p.Zone -Name $p.Name -IPv4Address $lab_ip -AgeRecord:$false; "
            f"    Write-Output ('SET ' + $p.Name + '.' + $p.Zone + ' -> ' + $lab_ip); "
            f"  }} catch {{ Write-Output ('FAIL ' + $p.Name + '.' + $p.Zone + ': ' + $_.Exception.Message) }} "
            f"}}"
        )

        # Connect via WinRM. The DC's host-bridge IP is reachable from the
        # backend. We assume the standard Docker user / admin password.
        try:
            import winrm
            # Find the DC's host-bridge IP by inspecting the container
            container = self.client.containers.get(container_name)
            container.reload()
            host_bridge_ip = None
            for net_name, net_info in container.attrs["NetworkSettings"]["Networks"].items():
                ip = net_info.get("IPAddress")
                if ip and not net_name.startswith("lab_"):
                    # First non-lab network is typically the host bridge
                    host_bridge_ip = ip
                    break
            if not host_bridge_ip:
                logger.warning(f"No host-bridge IP found for {container_name}; cannot repoint DNS")
                return

            session = winrm.Session(
                f"http://{host_bridge_ip}:5985/wsman",
                auth=("Docker", "admin"),
                transport="ntlm",
            )
            r = session.run_ps(ps_script)
            output = r.std_out.decode(errors="replace").strip()
            if "SET " in output:
                logger.info(f"DC DNS A records repointed to {lab_ip} on {container_name}: {output[:200]}")
            else:
                logger.warning(f"DC DNS repoint may have failed on {container_name}: {output[:300]}")
        except ImportError:
            logger.warning("python-winrm not available; cannot repoint DC DNS")
        except Exception as e:
            logger.warning(f"WinRM repoint of DC DNS on {container_name} failed: {e}")

    def _detect_host_network(self) -> Optional[str]:
        """
        Auto-detect the host's management LAN CIDR by inspecting the
        default route inside a privileged host-network container.

        Returns e.g. "10.20.0.0/24", or None on failure.
        Respects HOST_NETWORK env-var override if set.
        """
        override = os.environ.get("HOST_NETWORK", "").strip()
        if override:
            return override

        if not self.client:
            return None

        # Script: find the default-route interface, read its CIDR,
        # then compute the network address from it.
        script = r"""
apk add --no-cache iproute2 >/dev/null 2>&1
DEV=$(ip -4 route show default | awk '{print $5; exit}')
[ -z "$DEV" ] && exit 1
CIDR=$(ip -4 -o addr show dev "$DEV" | awk '{print $4; exit}')
[ -z "$CIDR" ] && exit 1
# Python-free network calc: use ipcalc from busybox
NETWORK=$(ipcalc -n "$CIDR" | grep Network | awk '{print $2}')
if [ -z "$NETWORK" ]; then
    # Fallback: just use the CIDR directly (busybox ipcalc varies)
    IP=$(echo "$CIDR" | cut -d/ -f1)
    PREFIX=$(echo "$CIDR" | cut -d/ -f2)
    # Zero the host bits for /24 or wider
    BASE=$(echo "$IP" | awk -F. -v p="$PREFIX" '{
        mask = lshift(0xFFFFFFFF, 32-p);
        ip = lshift($1,24) + lshift($2,16) + lshift($3,8) + $4;
        net = and(ip, mask);
        printf "%d.%d.%d.%d/%s", rshift(and(net,0xFF000000),24), rshift(and(net,0xFF0000),16), rshift(and(net,0xFF00),8), and(net,0xFF), p
    }')
    echo "$BASE"
else
    echo "$NETWORK"
fi
"""
        try:
            output = self.client.containers.run(
                "alpine:latest",
                command=["sh", "-c", script],
                network_mode="host",
                privileged=True,
                remove=True,
            )
            cidr = output.decode().strip().split("\n")[-1].strip()
            if "/" in cidr:
                logger.info(f"Auto-detected host management network: {cidr}")
                return cidr
            logger.warning(f"Host network detection returned unexpected value: {cidr!r}")
            return None
        except Exception as e:
            logger.warning(f"Failed to auto-detect host network: {e}")
            return None

    def _detect_external_interfaces(self) -> list:
        """
        Auto-detect physical / LAN-facing network interfaces on the host
        that should be blocked from forwarding into Docker-internal networks.

        By default, only the interface carrying the default route is returned.
        This is the NIC facing the physical LAN (and potentially the internet)
        — the primary attack surface.  VPN and tunnel interfaces (wg0,
        tailscale0, etc.) are intentional admin/student access paths and are
        NOT blocked by default.

        Environment variable overrides:
          OCR_EXTERNAL_IFACES  — explicit space-separated list of interfaces
                                 to block (skips auto-detection entirely)
          OCR_BLOCK_ALL_EXTERNAL — set to "1" to block ALL non-Docker
                                   interfaces (not just the default route)
          OCR_ALLOWED_IFACES   — exempt specific interfaces when using
                                 OCR_BLOCK_ALL_EXTERNAL mode

        Returns a list of interface names to block.
        """
        override = os.environ.get("OCR_EXTERNAL_IFACES", "").strip()
        if override:
            ifaces = override.split()
            logger.info(f"Using external interfaces from OCR_EXTERNAL_IFACES: {ifaces}")
            return ifaces

        if not self.client:
            return []

        block_all = os.environ.get("OCR_BLOCK_ALL_EXTERNAL", "").strip() == "1"

        try:
            # Detect the default-route interface AND all UP interfaces in one call
            script = (
                "DEV=$(ip -4 route show default 2>/dev/null | awk '{print $5; exit}'); "
                "echo \"DEFAULT=$DEV\"; "
                "ip -o link show up 2>/dev/null | awk -F': ' '{print $2}' | sed 's/@.*//'"
            )
            output = self.client.containers.run(
                "alpine:latest",
                command=["sh", "-c", script],
                network_mode="host",
                privileged=True,
                remove=True,
            ).decode()

            default_iface = None
            all_ifaces = []
            for line in output.strip().split("\n"):
                line = line.strip()
                if line.startswith("DEFAULT="):
                    default_iface = line.split("=", 1)[1].strip()
                elif line:
                    all_ifaces.append(line)

            if block_all:
                # Block ALL non-Docker interfaces (aggressive mode)
                allowed = set(os.environ.get("OCR_ALLOWED_IFACES", "").split())
                external = []
                for iface in all_ifaces:
                    if iface in ("lo",) or iface.startswith(("docker", "br-", "veth")):
                        continue
                    if iface in allowed:
                        logger.debug(f"Interface {iface} exempted via OCR_ALLOWED_IFACES")
                        continue
                    external.append(iface)
                logger.info(f"Auto-detected external interfaces (block-all mode): {external}")
                return external
            else:
                # Default: only block the default-route interface
                if default_iface:
                    logger.info(f"Auto-detected default-route interface: {default_iface}")
                    return [default_iface]
                else:
                    logger.warning("Could not detect default-route interface")
                    return []
        except Exception as e:
            logger.warning(f"Failed to detect external interfaces: {e}")
            return []

    def ensure_inbound_isolation(self) -> list:
        """
        Add iptables DOCKER-USER rules that block all external (non-Docker)
        interfaces from forwarding traffic into Docker-internal lab networks.

        This prevents the host's physical LAN, VPNs, tunnels, and the
        internet from directly reaching student lab containers, the Windows
        target VM, RangeBoxes, or SIEM containers.

        Published ports (port 80 for the frontend, etc.) are NOT affected
        because Docker rewrites their destination via PREROUTING DNAT to
        bridge-local IPs (172.16.x.x) before FORWARD is evaluated.

        Returns a list of result dicts:
          [{"rule": "...", "action": "added|exists|failed"}]
        """
        if not self.client:
            return [{"rule": "all", "action": "failed", "error": "Docker client unavailable"}]

        ext_ifaces = self._detect_external_interfaces()
        if not ext_ifaces:
            logger.warning("No external interfaces detected — skipping inbound isolation")
            return []

        # Build rules: for each external interface × protected subnet.
        # Use iptables -S (list) + grep to check for existing rules, because
        # iptables -C requires an exact match (including -m comment) and we
        # may have rules from the shell script that include comments.
        rules = []
        for iface in ext_ifaces:
            for subnet in self._PROTECTED_SUBNETS:
                rules.append((iface, subnet))

        lines = ["apk add --no-cache iptables >/dev/null 2>&1",
                 "EXISTING=$(iptables -S DOCKER-USER 2>/dev/null)"]
        for iface, subnet in rules:
            # Chained greps for order-independent matching (iptables -S may
            # output -d before -i).  Each grep filters for one component.
            add_cmd = f"-i {iface} -d {subnet} -j DROP"
            lines.append(
                f'if echo "$EXISTING" | grep "{iface}" | grep "{subnet}" | grep -q "DROP"; then '
                f'echo "EXISTS {add_cmd}"; '
                f'else iptables -I DOCKER-USER 1 {add_cmd} && echo "ADDED {add_cmd}" '
                f'|| echo "FAILED {add_cmd}"; fi'
            )
        script = "\n".join(lines)

        results = []
        try:
            output = self.client.containers.run(
                "alpine:latest",
                command=["sh", "-c", script],
                network_mode="host",
                privileged=True,
                remove=True,
            ).decode()

            for line in output.strip().split("\n"):
                line = line.strip()
                if line.startswith("ADDED "):
                    results.append({"rule": line[6:], "action": "added"})
                elif line.startswith("EXISTS "):
                    results.append({"rule": line[7:], "action": "exists"})
                elif line.startswith("FAILED "):
                    results.append({"rule": line[7:], "action": "failed"})

            added = [r for r in results if r["action"] == "added"]
            if added:
                logger.info(f"Inbound isolation: added {len(added)} new rules for interfaces {ext_ifaces}")
            else:
                logger.debug(f"Inbound isolation: all {len(results)} rules already present")
        except Exception as e:
            logger.warning(f"Failed to ensure inbound isolation iptables rules: {e}")
            for rule in rules:
                results.append({"rule": rule, "action": "failed", "error": str(e)})

        return results

    def ensure_lab_network_isolation(self) -> list:
        """
        Add iptables DOCKER-USER rules that block lab / RangeBox subnets
        from reaching the host management LAN, while still allowing
        internet access for tool downloads etc.

        Auto-detects the host LAN (or reads HOST_NETWORK env var).

        Returns a list of result dicts:
          [{"rule": "...", "action": "added|exists|failed", "error": "..."}]
        """
        if not self.client:
            return [{"rule": "all", "action": "failed", "error": "Docker client unavailable"}]

        host_net = self._detect_host_network()
        if not host_net:
            return [{"rule": "all", "action": "failed",
                     "error": "Could not detect host network — set HOST_NETWORK env var"}]

        rules = [f"-s {src} -d {host_net} -j DROP" for src in self._LAB_SUBNETS]

        # Block lab/RangeBox containers from reaching the backend API port
        # on any internal subnet. Defense-in-depth: even if the backend
        # accidentally ends up on a lab network, port 8000 is unreachable.
        # Also blocks access if a student flushes in-container iptables rules.
        for src in self._LAB_SUBNETS:
            rules.append(f"-s {src} -p tcp --dport 8000 -j DROP")

        # Build a script that checks (-C) then inserts (-I) each rule,
        # printing JSON-ish status for each so we can parse the results.
        lines = ["apk add --no-cache iptables >/dev/null 2>&1"]
        for rule in rules:
            lines.append(
                f'if iptables -C DOCKER-USER {rule} 2>/dev/null; then '
                f'echo "EXISTS {rule}"; '
                f'else iptables -I DOCKER-USER 1 {rule} && echo "ADDED {rule}" '
                f'|| echo "FAILED {rule}"; fi'
            )
        script = "\n".join(lines)

        results = []
        try:
            output = self.client.containers.run(
                "alpine:latest",
                command=["sh", "-c", script],
                network_mode="host",
                privileged=True,
                remove=True,
            ).decode()

            for line in output.strip().split("\n"):
                line = line.strip()
                if line.startswith("ADDED "):
                    results.append({"rule": line[6:], "action": "added"})
                elif line.startswith("EXISTS "):
                    results.append({"rule": line[7:], "action": "exists"})
                elif line.startswith("FAILED "):
                    results.append({"rule": line[7:], "action": "failed"})

            logger.info(f"Lab network isolation rules ensured (host LAN={host_net}): "
                        + ", ".join(f"{r['action']}:{r['rule']}" for r in results))
        except Exception as e:
            logger.warning(f"Failed to ensure lab network isolation iptables rules: {e}")
            for rule in rules:
                results.append({"rule": rule, "action": "failed", "error": str(e)})

        return results

    def audit_lab_network_isolation(self) -> list:
        """
        Check whether lab network isolation iptables rules are present
        in DOCKER-USER.

        Returns a list of check dicts matching the firewall-audit format:
          [{"name": "...", "status": "ok|error", "detail": "..."}]
        """
        if not self.client:
            return [{"name": "Lab isolation", "status": "error",
                     "detail": "Docker client unavailable"}]

        host_net = self._detect_host_network()
        if not host_net:
            return [{"name": "Lab isolation", "status": "error",
                     "detail": "Could not detect host network — set HOST_NETWORK env var"}]

        rules = [f"-s {src} -d {host_net} -j DROP" for src in self._LAB_SUBNETS]

        lines = ["apk add --no-cache iptables >/dev/null 2>&1"]
        for rule in rules:
            lines.append(
                f'iptables -C DOCKER-USER {rule} 2>/dev/null '
                f'&& echo "OK {rule}" || echo "MISSING {rule}"'
            )
        script = "\n".join(lines)

        checks = []
        try:
            output = self.client.containers.run(
                "alpine:latest",
                command=["sh", "-c", script],
                network_mode="host",
                privileged=True,
                remove=True,
            ).decode()

            for line in output.strip().split("\n"):
                line = line.strip()
                if line.startswith("OK "):
                    rule = line[3:]
                    checks.append({
                        "name": f"Lab isolation: {rule.split('-d')[0].strip().split()[-1]}",
                        "status": "ok",
                        "detail": f"DROP rule present: {rule}",
                    })
                elif line.startswith("MISSING "):
                    rule = line[8:]
                    checks.append({
                        "name": f"Lab isolation: {rule.split('-d')[0].strip().split()[-1]}",
                        "status": "error",
                        "detail": f"DROP rule MISSING: {rule} — click Fix Rules to apply",
                    })
        except Exception as e:
            checks.append({
                "name": "Lab isolation",
                "status": "error",
                "detail": f"Failed to audit: {e}",
            })

        # Audit inbound isolation — external interfaces should be blocked from
        # forwarding traffic into Docker-internal lab networks.
        try:
            ext_ifaces = self._detect_external_interfaces()
            if ext_ifaces:
                # Use grep-based check (tolerant of -m comment variations)
                inbound_lines = [
                    "apk add --no-cache iptables >/dev/null 2>&1",
                    "EXISTING=$(iptables -S DOCKER-USER 2>/dev/null)",
                ]
                for iface in ext_ifaces:
                    for subnet in self._PROTECTED_SUBNETS:
                        label = f"-i {iface} -d {subnet} -j DROP"
                        inbound_lines.append(
                            f'if echo "$EXISTING" | grep "{iface}" | grep "{subnet}" | grep -q "DROP"; then '
                            f'echo "OK {label}"; '
                            f'else echo "MISSING {label}"; fi'
                        )

                inbound_output = self.client.containers.run(
                    "alpine:latest",
                    command=["sh", "-c", "\n".join(inbound_lines)],
                    network_mode="host",
                    privileged=True,
                    remove=True,
                ).decode()

                missing_count = 0
                ok_count = 0
                for line in inbound_output.strip().split("\n"):
                    line = line.strip()
                    if line.startswith("OK "):
                        ok_count += 1
                    elif line.startswith("MISSING "):
                        missing_count += 1

                if missing_count == 0 and ok_count > 0:
                    checks.append({
                        "name": "Inbound isolation",
                        "status": "ok",
                        "detail": f"All {ok_count} inbound DROP rules present "
                                  f"(interfaces: {', '.join(ext_ifaces)})",
                    })
                elif missing_count > 0:
                    checks.append({
                        "name": "Inbound isolation",
                        "status": "error",
                        "detail": f"{missing_count} inbound DROP rule(s) MISSING "
                                  f"— external traffic can reach lab networks. "
                                  f"Click Fix Rules to apply.",
                    })
            else:
                checks.append({
                    "name": "Inbound isolation",
                    "status": "warning",
                    "detail": "Could not detect external interfaces — unable to verify inbound rules",
                })
        except Exception as e:
            checks.append({
                "name": "Inbound isolation",
                "status": "error",
                "detail": f"Failed to audit inbound rules: {e}",
            })

        # Audit shared containers (e.g. Dockur Windows VM) — verify they are
        # running and have iptables DNAT forwarding active for any connected
        # lab networks.  This catches issues like the Windows target being
        # stopped or forwarding rules missing.
        try:
            shared_container_names = set()
            # Scan all lab compose files to find declared shared containers
            labs_dir = os.environ.get("LABS_DIR", "/labs")
            if os.path.isdir(labs_dir):
                for root, _dirs, files in os.walk(labs_dir):
                    if "docker-compose.yml" in files:
                        try:
                            with open(os.path.join(root, "docker-compose.yml")) as f:
                                cdata = yaml.safe_load(f.read()) or {}
                            for entry in cdata.get("x-ocr-shared-containers", []):
                                name = entry.get("name") if isinstance(entry, dict) else str(entry)
                                shared_container_names.add(name)
                        except Exception:
                            continue

            for sc_name in shared_container_names:
                try:
                    sc = self.client.containers.get(sc_name)
                    if sc.status != "running":
                        checks.append({
                            "name": f"Shared container: {sc_name}",
                            "status": "ok",
                            "detail": f"Container exists ({sc.status}) — starts on demand when labs require it",
                        })
                        continue

                    # Count connected lab networks
                    sc.reload()
                    sc_nets = sc.attrs.get("NetworkSettings", {}).get("Networks", {})
                    lab_nets = [n for n in sc_nets if n.startswith("lab_")]
                    native_nets = [n for n in sc_nets if not n.startswith("lab_")]

                    # Check iptables DNAT forwarding rules for lab-facing IPs
                    dnat_ok = True
                    dnat_count = 0
                    if lab_nets:
                        dnat_check = sc.exec_run(
                            ["sh", "-c", "iptables -t nat -L PREROUTING -n 2>/dev/null | grep -c DNAT"],
                            demux=False,
                        )
                        dnat_count_str = dnat_check.output.decode().strip() if dnat_check.exit_code == 0 else "0"
                        try:
                            dnat_count = int(dnat_count_str)
                        except ValueError:
                            dnat_count = 0
                        if dnat_count == 0:
                            dnat_ok = False

                    detail_parts = [
                        f"Running on {len(native_nets)} native + {len(lab_nets)} lab network(s)",
                    ]
                    if lab_nets and dnat_ok:
                        detail_parts.append(f"iptables DNAT forwarding active ({dnat_count} rules)")
                    elif lab_nets and not dnat_ok:
                        detail_parts.append("iptables DNAT rules NOT found — labs may not reach VM services")

                    status = "ok" if (dnat_ok or not lab_nets) else "warning"
                    checks.append({
                        "name": f"Shared container: {sc_name}",
                        "status": status,
                        "detail": "; ".join(detail_parts),
                    })
                except docker.errors.NotFound:
                    checks.append({
                        "name": f"Shared container: {sc_name}",
                        "status": "ok",
                        "detail": f"Container {sc_name} not present — will be created on demand when labs require it",
                    })
        except Exception as e:
            logger.warning(f"Shared container audit failed: {e}")

        # Also audit gateway-blocking rules inside running RangeBox containers
        try:
            rangebox_containers = self.client.containers.list(
                filters={"label": "ocr.role"}
            )
            for c in rangebox_containers:
                role = c.labels.get("ocr.role", "")
                if "rangebox" not in role:
                    continue
                try:
                    exit_code, output = c.exec_run("iptables -L OUTPUT -n", user="root")
                    output_str = output.decode() if output else ""
                    if exit_code != 0 and ("not found" in output_str.lower() or "executable file not found" in output_str.lower() or not output_str.strip()):
                        # iptables not installed in this image — host-level
                        # DOCKER-USER rules provide isolation; skip this check
                        checks.append({
                            "name": f"RangeBox gateway block ({c.name})",
                            "status": "ok",
                            "detail": "Protected by host-level DOCKER-USER rules (iptables not available in container)",
                        })
                    elif "DROP" in output_str and ".1" in output_str:
                        checks.append({
                            "name": f"RangeBox gateway block ({c.name})",
                            "status": "ok",
                            "detail": "Gateway DROP rules present inside container",
                        })
                    else:
                        checks.append({
                            "name": f"RangeBox gateway block ({c.name})",
                            "status": "warning",
                            "detail": "Gateway DROP rules not yet applied — will auto-apply within 30s",
                        })
                except Exception:
                    # exec_run itself failed (e.g. OCI runtime error) — iptables
                    # not available, host-level rules still protect
                    checks.append({
                        "name": f"RangeBox gateway block ({c.name})",
                        "status": "ok",
                        "detail": "Protected by host-level DOCKER-USER rules (iptables not available in container)",
                    })
        except Exception:
            pass

        return checks

    def ensure_vpn_firewall_rules(self):
        """
        Ensure iptables rules allow VPN (WireGuard) traffic to reach Docker
        bridge networks. Docker adds DROP rules in raw PREROUTING that block
        traffic arriving on non-bridge interfaces.

        Calls the Peer Manager API on the host to apply the rules, since
        iptables cannot be modified from inside a Docker container.
        """
        import requests

        api_url = os.environ.get("WG_API_URL") or "http://host.docker.internal:5000"
        api_key = os.environ.get("WG_API_KEY") or ""

        logger.info(f"Ensuring VPN firewall rules via Peer Manager at {api_url}")

        headers = {}
        if api_key:
            headers["X-API-Key"] = api_key

        try:
            resp = requests.post(
                f"{api_url}/firewall/ensure",
                headers=headers,
                timeout=5
            )
            if resp.status_code == 200:
                data = resp.json()
                for rule in data.get("rules", []):
                    if rule.get("action") == "added":
                        logger.info(f"Peer Manager added iptables rule: {rule.get('rule')}")
                    elif rule.get("action") == "failed":
                        logger.warning(f"Peer Manager failed to add rule: {rule.get('rule')}: {rule.get('error')}")
            else:
                logger.warning(f"Peer Manager firewall/ensure returned {resp.status_code}: {resp.text}")
        except requests.exceptions.ConnectionError:
            logger.warning("Cannot reach Peer Manager API for firewall rules — ensure rules are applied on the host")
        except Exception as e:
            logger.warning(f"Error requesting firewall rules from Peer Manager: {e}")

    def _cleanup_failed_spawn(self, user_id: int, lab_slug: str,
                              override_path: Optional[str] = None):
        """Tear down the half-created environment after a failed bring-up.

        A spawn that dies mid-way can leave the lab network, a partial set of
        compose containers, and the temp override file behind, and the orphaned
        network then blocks the user's next spawn with a subnet conflict.
        destroy_lab_environment already knows how to stop compose containers,
        force-remove stragglers by project label, and delete both lab networks,
        so reuse it. Errors are logged and swallowed because the caller is
        already raising the original spawn failure.
        """
        if override_path:
            try:
                os.unlink(override_path)
            except OSError:
                pass
        try:
            self.destroy_lab_environment(user_id, lab_slug)
            logger.info(f"Cleaned up partial environment for lab_{user_id}_{lab_slug} after failed spawn")
        except Exception as e:
            logger.warning(f"Cleanup of failed spawn lab_{user_id}_{lab_slug} was incomplete: {e}")

    def create_lab_environment(
        self,
        user_id: int,
        lab_slug: str,
        compose_content: str,
    ) -> Dict[str, str]:
        """
        Create Docker network and containers for a lab session
        
        Args:
            user_id: User ID for network isolation
            lab_slug: Lab identifier
            compose_content: Docker Compose YAML content
            
        Returns:
            Dict with network_id and subnet
        """
        if not self.client:
            raise Exception("Docker client not available")
        
        # Get unique subnet octets per user + lab (prevents conflicts between labs)
        second_octet, third_octet = get_subnet_id(user_id, lab_slug)
        network_name = f"lab_{user_id}_{lab_slug}".lower()
        subnet = f"10.{second_octet}.{third_octet}.0/24"
        
        # CRITICAL: Remove ALL existing networks for this user_id first
        # This prevents conflicts when switching between labs quickly
        import time
        try:
            all_networks = self.client.networks.list()
            user_networks_removed = 0
            for net in all_networks:
                net_name = net.name
                # Remove any network belonging to this user (regardless of lab_slug)
                if not net_name.startswith(f"lab_{user_id}_"):
                    continue
                try:
                    logger.info(f"Removing existing network {net_name} for user {user_id} before creating new lab")
                    # Reload for fresh container list, disconnect by name
                    net.reload()
                    containers = net.attrs.get("Containers", {})
                    for container_id, cinfo in containers.items():
                        cname = cinfo.get("Name", container_id)
                        try:
                            net.disconnect(cname, force=True)
                            logger.info(f"Disconnected {cname} from {net_name}")
                        except Exception:
                            pass
                    net.remove()
                    user_networks_removed += 1
                except Exception as e:
                    logger.warning(f"Failed to remove existing network {net_name}: {e}")

            if user_networks_removed > 0:
                logger.info(f"Removed {user_networks_removed} existing network(s) for user {user_id}")
                # Docker needs time to fully release subnets after network removal
                time.sleep(2)
        except Exception as e:
            logger.warning(f"Failed to clean up user networks (non-fatal): {e}")
        
        # Clean up orphaned networks before creating new one (helps prevent conflicts)
        try:
            orphaned_count = self.cleanup_orphaned_networks()
            if orphaned_count > 0:
                logger.info(f"Cleaned up {orphaned_count} orphaned networks before creating {network_name}")
        except Exception as e:
            logger.warning(f"Failed to clean up orphaned networks (non-fatal): {e}")
        
        # Check if network with same name exists and clean it up if needed
        try:
            existing_network = self.client.networks.get(network_name)
            # Check if subnet matches
            existing_subnet = None
            try:
                ipam_config = existing_network.attrs.get("IPAM", {})
                configs = ipam_config.get("Config", [])
                if configs:
                    existing_subnet = configs[0].get("Subnet", "")
            except Exception:
                pass
            
            if existing_subnet == subnet:
                # Network exists with correct subnet, reuse it
                logger.info(f"Network {network_name} already exists with subnet {subnet}")
                network = existing_network
            else:
                # Network exists but with different subnet - remove and recreate
                logger.warning(f"Network {network_name} exists with different subnet ({existing_subnet} vs {subnet}), removing and recreating")
                try:
                    # Disconnect containers first
                    containers = existing_network.attrs.get("Containers", {})
                    for container_id in containers.keys():
                        try:
                            existing_network.disconnect(container_id, force=True)
                        except Exception:
                            pass
                    existing_network.remove()
                except Exception as e:
                    logger.error(f"Failed to remove existing network {network_name}: {e}")
                # Will create new network below
                network = None
        except docker.errors.NotFound:
            # Network doesn't exist, will create it
            network = None
        
        # Check for any existing networks with overlapping subnet and remove them
        # Use generous retry patience — a previous lab's background teardown may
        # still be releasing the subnet (Docker takes a few seconds to fully clean up).
        if network is None:
            import time
            max_retries = 8
            retry_delay = 3.0  # seconds
            
            for attempt in range(max_retries):
                try:
                    all_networks = self.client.networks.list()
                    conflicting_networks = []
                    
                    for net in all_networks:
                        try:
                            net_attrs = net.attrs
                            net_name = net_attrs.get("Name", "")
                            # Skip if it's the network we're about to create
                            if net_name == network_name:
                                continue
                            
                            # Check subnet overlap
                            ipam_config = net_attrs.get("IPAM", {})
                            configs = ipam_config.get("Config", [])
                            for config in configs:
                                existing_subnet = config.get("Subnet", "")
                                if existing_subnet == subnet:
                                    conflicting_networks.append((net, net_name))
                        except Exception as e:
                            logger.debug(f"Error checking network: {e}")
                            continue
                    
                    # Remove all conflicting networks
                    if conflicting_networks:
                        logger.warning(f"Found {len(conflicting_networks)} network(s) with overlapping subnet {subnet} (attempt {attempt + 1}/{max_retries})")
                        for net, net_name in conflicting_networks:
                            # Only remove lab networks (safety check)
                            if net_name.startswith("lab_"):
                                try:
                                    # Reload to get fresh container list
                                    net.reload()
                                    containers = net.attrs.get("Containers", {})
                                    for container_id, cinfo in containers.items():
                                        cname = cinfo.get("Name", container_id)
                                        try:
                                            net.disconnect(cname, force=True)
                                            logger.info(f"Disconnected {cname} from conflicting network {net_name}")
                                        except Exception as de:
                                            logger.debug(f"Disconnect {cname} from {net_name}: {de}")
                                    net.remove()
                                    logger.info(f"Removed conflicting network {net_name} with overlapping subnet")
                                except Exception as e:
                                    logger.warning(f"Failed to clean up conflicting network {net_name}: {e}")
                            else:
                                logger.error(f"Non-lab network {net_name} uses subnet {subnet} - cannot remove automatically")
                                if attempt == max_retries - 1:
                                    raise Exception(f"Network subnet {subnet} is in use by non-lab network {net_name}. Cannot create lab network.")
                        
                        # Wait a bit for Docker to process removals
                        if conflicting_networks and attempt < max_retries - 1:
                            time.sleep(retry_delay)
                            continue
                    else:
                        # No conflicts found, break out of retry loop
                        break
                        
                except Exception as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Error checking for subnet conflicts after {max_retries} attempts: {e}")
                        raise
                    time.sleep(retry_delay)
        
        # Create network if it doesn't exist (with retry logic)
        if network is None:
            import time
            max_create_retries = 6
            create_retry_delay = 2.0
            
            for create_attempt in range(max_create_retries):
                try:
                    # Use .254 as the Docker bridge gateway so that .1 is
                    # available for lab containers (e.g. gateway routers).
                    bridge_gateway = f"10.{second_octet}.{third_octet}.254"
                    network = self.client.networks.create(
                        network_name,
                        driver="bridge",
                        ipam=docker.types.IPAMConfig(
                            driver="default",
                            pool_configs=[
                                docker.types.IPAMPool(
                                    subnet=subnet,
                                    gateway=bridge_gateway
                                )
                            ]
                        )
                    )
                    logger.info(f"Created network {network_name} with subnet {subnet} (gw={bridge_gateway})")
                    break  # Success, exit retry loop
                except docker.errors.APIError as e:
                    if "overlaps" in str(e).lower() or "forbidden" in str(e).lower():
                        logger.warning(f"Network creation failed due to subnet overlap (attempt {create_attempt + 1}/{max_create_retries}): {e}")
                        # Try to find and clean up the conflicting network
                        try:
                            all_networks = self.client.networks.list()
                            for net in all_networks:
                                try:
                                    net_attrs = net.attrs
                                    ipam_config = net_attrs.get("IPAM", {})
                                    configs = ipam_config.get("Config", [])
                                    for config in configs:
                                        if config.get("Subnet", "") == subnet:
                                            net_name = net_attrs.get("Name", "")
                                            logger.warning(f"Found conflicting network: {net_name}")
                                            if net_name.startswith("lab_"):
                                                # Try to remove orphaned lab network
                                                try:
                                                    containers = net_attrs.get("Containers", {})
                                                    for container_id in containers.keys():
                                                        try:
                                                            net.disconnect(container_id, force=True)
                                                        except Exception:
                                                            pass
                                                    net.remove()
                                                    logger.info(f"Removed conflicting orphaned network {net_name}")
                                                    # Wait a bit for Docker to process
                                                    time.sleep(0.5)
                                                except Exception as cleanup_error:
                                                    logger.warning(f"Failed to clean up conflicting network {net_name}: {cleanup_error}")
                                except Exception:
                                    continue
                        except Exception as cleanup_error:
                            logger.warning(f"Error during cleanup attempt: {cleanup_error}")
                        
                        # Retry if we haven't exhausted attempts
                        if create_attempt < max_create_retries - 1:
                            logger.info(f"Retrying network creation after {create_retry_delay}s...")
                            time.sleep(create_retry_delay)
                            continue
                        else:
                            raise Exception(f"Failed to create network after {max_create_retries} attempts: subnet {subnet} overlaps with existing network. A previous lab may still be shutting down — please wait a moment and try again.")
                    else:
                        # Non-overlap error
                        if create_attempt == max_create_retries - 1:
                            raise
                        else:
                            logger.warning(f"Network creation failed (attempt {create_attempt + 1}/{max_create_retries}): {e}, retrying...")
                            time.sleep(create_retry_delay)
                            continue
        
        # Get lab directory path - labs are mounted at /labs in the container
        # lab_slug format: {track}-{level}-{num}-{name}, e.g., "web-1-1-basic-directory-enumeration"
        track_slug = lab_slug.split("-")[0].lower()  # e.g., "web", "windows", "capitalflow"
        track_dir_name = get_track_directory_name(track_slug)
        lab_dir = f"/labs/{track_dir_name}/{lab_slug}"

        # Start containers using docker-compose
        compose_file = os.path.join(lab_dir, "docker-compose.yml")

        # Parse compose content — prefer the DB content, fall back to disk file
        compose_data = yaml.safe_load(compose_content) if compose_content else None
        if not compose_data:
            try:
                with open(compose_file, "r") as f:
                    compose_data = yaml.safe_load(f.read()) or {}
            except Exception:
                compose_data = {}

        if not compose_data:
            raise Exception(f"No compose configuration found for {lab_slug} (no DB content, no file at {compose_file})")
        
        # Set environment variables for docker-compose
        env = os.environ.copy()
        env["COMPOSE_PROJECT_NAME"] = f"lab_{user_id}_{lab_slug}".lower()
        env["NETWORK_NAME"] = network_name

        # Start containers using pre-built images when available.
        # Pre-built images are created by scripts/prebuild-labs.sh which should
        # be run after deployment. This avoids slow builds (scapy, wireshark, etc.)
        # at student spawn time and prevents timeout/network failures.
        #
        # Generate a compose override that attaches all services to the
        # pre-created lab network as an external network.  This prevents
        # Docker Compose from auto-creating a "{project}_default" bridge
        # with a random subnet -- eliminating a class of connectivity bugs
        # where containers end up only on the wrong network.
        override_data = {
            "networks": {
                "default": {
                    "name": network_name,
                    "external": True,
                }
            }
        }
        # Per-instance FLAG / CRED_* env for labs materialized from an Exercise
        # Studio template (empty dict for every other lab, so this is a no-op for
        # them). Injected via the per-service compose override below so the
        # values reach the container without baking them into the image.
        instance_env = self._template_instance_env(lab_slug)
        services_override = {}
        for svc_name, svc_cfg in (compose_data.get("services") or {}).items():
            labels = svc_cfg.get("labels", {})
            svc_override = {}

            # Default CPU / memory caps. Skipped when the compose file sets
            # its own mem_limit / cpus / deploy limits for the service.
            if not svc_cfg.get("mem_limit") and not svc_cfg.get("deploy"):
                svc_override["mem_limit"] = self.LAB_MEM_LIMIT
                svc_override["memswap_limit"] = self.LAB_MEM_LIMIT  # no swap
            if not svc_cfg.get("cpus") and not svc_cfg.get("cpu_quota") and not svc_cfg.get("deploy"):
                try:
                    svc_override["cpus"] = float(self.LAB_CPU_LIMIT)
                except (TypeError, ValueError):
                    svc_override["cpus"] = 1.0

            # Opt-out: a service labeled ocr_lab_net="false" stays OFF the student
            # lab net and lives only on its own in-compose network (e.g. a
            # firewalled protected LAN behind an inline firewall service). Default
            # is to attach. Resource caps above still apply.
            if str(labels.get("ocr_lab_net", "true")).lower() == "false":
                if svc_override:
                    services_override[svc_name] = svc_override
                continue
            ip_off = labels.get("ip_offset", "10")
            svc_ip = f"10.{second_octet}.{third_octet}.{ip_off}"
            net_cfg = {"ipv4_address": svc_ip}
            hostname = svc_cfg.get("hostname")
            if hostname:
                net_cfg["aliases"] = [hostname]
            svc_override["networks"] = {"default": net_cfg}
            # Per-SERVICE injection: only the service the template's env_contract
            # scoped a var to receives it, so FLAG/creds never leak into peer
            # containers. Empty for every non-template lab -> strict no-op.
            svc_env = instance_env.get(svc_name) if instance_env else None
            if svc_env:
                svc_override["environment"] = dict(svc_env)
            services_override[svc_name] = svc_override
        if services_override:
            override_data["services"] = services_override

        override_fd, override_path = tempfile.mkstemp(
            suffix=".yml", prefix=f"lab_{user_id}_override_"
        )
        try:
            with os.fdopen(override_fd, "w") as f:
                yaml.safe_dump(override_data, f)
        except Exception:
            os.close(override_fd)
            raise

        project_args = [
            "docker", "compose",
            "-f", compose_file,
            "-f", override_path,
            "-p", f"lab_{user_id}_{lab_slug}".lower(),
        ]

        # Skip docker-compose up for labs that only use shared external containers
        _has_own_services = bool(compose_data.get("services"))

        if not _has_own_services:
            logger.info(f"No services defined for {lab_slug} — shared-container-only lab")

        if _has_own_services:
            # Re-tag pre-built images to match this user's project name.
            # prebuild-labs.sh tags images as  prebuild-{slug}-{service}:latest
            # but compose expects              lab_{uid}_{slug}-{service}:latest
            target_project = f"lab_{user_id}_{lab_slug}".lower()
            prebuild_project = f"prebuild-{lab_slug}".lower()
            for svc_name in compose_data.get("services", {}):
                for src_prefix in [prebuild_project, lab_slug.lower()]:
                    src_tag = f"{src_prefix}-{svc_name}:latest"
                    dst_tag = f"{target_project}-{svc_name}:latest"
                    if src_tag == dst_tag:
                        continue
                    try:
                        img = self.client.images.get(src_tag)
                        img.tag(dst_tag)
                        logger.info(f"Re-tagged {src_tag} -> {dst_tag}")
                    except docker.errors.ImageNotFound:
                        pass
                    except Exception as e:
                        logger.debug(f"Image re-tag {src_tag} -> {dst_tag} failed: {e}")

            try:
                # First, try to start with pre-built images only (fast path, ~5-10s)
                logger.info(f"Starting containers for {lab_slug} using pre-built images")
                result = subprocess.run(
                    project_args + ["up", "-d", "--no-build"],
                    cwd=lab_dir,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=60  # 60s is plenty for starting pre-built images
                )

                if result.returncode != 0:
                    # Images not pre-built - fall back to build+start (slow path)
                    logger.warning(f"Pre-built images not found for {lab_slug}, building on-demand (this may be slow)")
                    result = subprocess.run(
                        project_args + ["up", "-d", "--build"],
                        cwd=lab_dir,
                        env=env,
                        capture_output=True,
                        text=True,
                        timeout=180  # 3 minutes for build+start
                    )

                    if result.returncode != 0:
                        error_msg = result.stderr or result.stdout or "Unknown error"
                        logger.error(f"Failed to start containers for {lab_slug}: {error_msg}")
                        self._cleanup_failed_spawn(user_id, lab_slug, override_path)
                        raise Exception(f"Failed to start containers: {error_msg}")

                logger.info(f"Containers started successfully for {lab_slug}")
            except subprocess.TimeoutExpired:
                logger.error(f"Timeout starting containers for {lab_slug}")
                self._cleanup_failed_spawn(user_id, lab_slug, override_path)
                raise Exception(
                    f"Timeout starting containers for {lab_slug}. "
                    f"Run 'scripts/prebuild-labs.sh --lab {lab_slug}' on the server to pre-build images."
                )

        # Clean up the temporary compose override file
        try:
            os.unlink(override_path)
        except OSError:
            pass

        # Connect containers to network with IP addresses
        # With the external-network override, compose already places containers
        # on the correct network with static IPs.  The loop below is kept as a
        # safety net for edge cases (compose version differences, labs that
        # declare their own networks section, etc.).
        services = compose_data.get("services") or {}
        project_name = f"lab_{user_id}_{lab_slug}".lower().lower()
        for service_name, service_config in services.items():
            # Try multiple container name patterns (docker-compose v1 vs v2 naming)
            possible_names = [
                f"{project_name}-{service_name}-1",  # Docker Compose v2 format
                f"{project_name}_{service_name}_1",  # Docker Compose v1 format
                f"{project_name}_{service_name}",    # Legacy format
            ]
            
            container = None
            container_name = None
            for name in possible_names:
                try:
                    container = self.client.containers.get(name)
                    container_name = name
                    break
                except docker.errors.NotFound:
                    continue
            
            if not container:
                logger.warning(f"Container for service {service_name} not found (tried: {possible_names})")
                continue
            
            try:
                # Get IP offset from labels
                labels = service_config.get("labels", {})
                # Opt-out (see above): keep protected-LAN services off the student
                # lab net. No-op for every existing lab.
                if str(labels.get("ocr_lab_net", "true")).lower() == "false":
                    continue
                ip_offset = labels.get("ip_offset", "10")

                # Calculate IP address using subnet octets (already calculated above)
                ip_address = f"10.{second_octet}.{third_octet}.{ip_offset}"

                # Skip if the compose override already placed this container
                # on the correct network with the right IP.
                container.reload()
                existing_nets = container.attrs.get("NetworkSettings", {}).get("Networks", {})
                if network_name in existing_nets:
                    existing_ip = existing_nets[network_name].get("IPAddress", "")
                    if existing_ip == ip_address:
                        logger.debug(f"{container_name} already on {network_name} at {ip_address}")
                        continue
                    # Wrong IP -- disconnect first, then reconnect below
                    network.disconnect(container)

                # Connect to network with specific IP and friendly DNS alias
                connect_kwargs = {"ipv4_address": ip_address}
                hostname = service_config.get("hostname")
                if hostname:
                    connect_kwargs["aliases"] = [hostname]
                network.connect(container, **connect_kwargs)
                logger.info(f"Connected {container_name} to network with IP {ip_address} (alias={hostname})")
            except Exception as e:
                logger.error(f"Failed to connect {container_name} to network: {e}")
        
        self.ensure_vpn_firewall_rules()

        # Bridge any running standalone RangeBox to this lab network
        self.bridge_standalone_rangebox_to_lab(user_id, lab_slug)

        # Spawn a network tap container if the lab declares x-ocr-network-tap.
        # The tap captures all bridge traffic and streams PCAP over TCP 9999
        # as a fallback for students who can't use the GRETAP tunnel.
        if compose_data.get("x-ocr-network-tap"):
            self._spawn_network_tap(user_id, lab_slug, network, network_name,
                                    second_octet, third_octet, project_name)
            # Create a GRETAP tunnel bridged to the lab network so VPN
            # students can passively sniff with tcpdump -i lab0.  The
            # client side is set up automatically by a PostUp hook in
            # the student's WireGuard config.
            self._setup_gretap_mirror(user_id, network_name)

        return {
            "network_id": network.id,
            "subnet": subnet
        }

    # ------------------------------------------------------------------
    # Network Tap — streams PCAP over TCP 9999 for VPN-based sniffing
    # ------------------------------------------------------------------

    NETWORK_TAP_IMAGE = "ocr-network-tap:latest"
    NETWORK_TAP_IP_OFFSET = 253  # .253 on each lab subnet

    def _spawn_network_tap(self, user_id, lab_slug, network, network_name,
                           second_octet, third_octet, project_name):
        """Spawn a lightweight network-tap container on the lab bridge.

        The container captures all traffic in promiscuous mode and serves
        a live PCAP stream on TCP 9999.  VPN-connected students connect
        with:  nc <tap-ip> 9999 | tcpdump -r - -A 'port 80'

        Because Docker bridge switches unicast frames only to destination
        ports, promiscuous mode alone is not enough.  We also set up Linux
        TC (traffic control) ``mirred`` rules on every lab container's
        host-side veth to mirror ingress frames to the tap container's veth.
        This gives the tap full visibility of all inter-container traffic.
        """
        tap_name = f"{project_name}-nettap-1"
        tap_ip = f"10.{second_octet}.{third_octet}.{self.NETWORK_TAP_IP_OFFSET}"

        try:
            # Remove stale tap container if present
            try:
                old = self.client.containers.get(tap_name)
                old.remove(force=True)
            except docker.errors.NotFound:
                pass

            container = self.client.containers.run(
                self.NETWORK_TAP_IMAGE,
                name=tap_name,
                detach=True,
                restart_policy={"Name": "unless-stopped"},
                cap_add=["NET_ADMIN", "NET_RAW"],
                mem_limit="256m",
                memswap_limit="256m",  # no swap
                cpu_period=100000,
                cpu_quota=25000,  # 0.25 CPU is plenty for a passive tap
                labels={
                    "com.docker.compose.project": project_name,
                    "ocr.network-tap": "true",
                },
            )

            # Attach to the lab network with a fixed IP
            network.connect(container, ipv4_address=tap_ip,
                            aliases=["network-tap"])
            logger.info(f"Network tap spawned at {tap_ip} for {lab_slug} (user {user_id})")

            # Set up TC mirred rules so the tap can see all unicast traffic
            # between containers on the lab bridge.
            self._setup_tc_mirror_for_tap(project_name, network_name, container)

        except Exception as e:
            # Non-fatal — the lab works without the tap, students just can't
            # do remote packet capture.
            logger.warning(f"Failed to spawn network tap for {lab_slug}: {e}")

    def _setup_tc_mirror_for_tap(self, project_name, network_name, tap_container):
        """Configure TC ingress mirrors on lab container veths → tap veth.

        Each lab container's host-side veth gets an ingress qdisc with a
        mirred filter that copies every frame to the tap container's veth.
        This runs inside a short-lived privileged container with host
        networking so it can manipulate host-level TC rules.
        """
        try:
            # Identify the tap container's host-side veth name
            tap_container.reload()
            tap_iflink = tap_container.exec_run(
                "cat /sys/class/net/eth1/iflink", demux=True
            )
            tap_veth_idx = tap_iflink.output[0].decode().strip() if tap_iflink.output[0] else None
            if not tap_veth_idx:
                logger.warning("Could not determine tap container veth index")
                return

            # Find all container veths on the lab bridge using `bridge link show`.
            # This approach finds ALL veths regardless of whether the container
            # has a visible IP via `ip addr` (e.g. customer-laptop gets its IP
            # from Docker but it's not visible inside the container).
            try:
                network = self.client.networks.get(network_name)
                bridge_name = f"br-{network.id[:12]}"
            except Exception:
                logger.warning(f"Could not resolve bridge name for {network_name}")
                return

            veth_indices = []
            try:
                bridge_result = subprocess.run(
                    ["docker", "run", "--rm", "--privileged", "--net=host",
                     "alpine:3.19", "sh", "-c",
                     "apk add --no-cache iproute2 bridge-utils >/dev/null 2>&1; bridge link show"],
                    capture_output=True, text=True, timeout=15
                )
                for line in bridge_result.stdout.splitlines():
                    if bridge_name not in line:
                        continue
                    parts = line.strip().split(":")
                    if parts and parts[0].strip().isdigit():
                        idx = parts[0].strip()
                        # Skip the tap container's own veth
                        if idx == tap_veth_idx:
                            continue
                        veth_indices.append(idx)
            except Exception as e:
                logger.warning(f"Failed to list bridge ports for tap mirror: {e}")

            if not veth_indices:
                logger.warning("No lab container veths found for TC mirror")
                return

            # Build a shell script that:
            # 1. Maps veth indices to names
            # 2. Sets up ingress qdisc + mirred filter on each
            mirror_cmds = []
            for idx in veth_indices:
                mirror_cmds.append(
                    f'VETH=$(ip -o link show | awk -v i={idx} \'$1 ~ "^"i":" {{split($2,a,"@"); print a[1]}}\')'
                    f' && tc qdisc add dev $VETH ingress 2>/dev/null;'
                    f' tc filter add dev $VETH parent ffff: protocol all u32 match u32 0 0'
                    f' action mirred egress mirror dev $TAP_VETH 2>/dev/null'
                )
            script = (
                f'apk add --no-cache iproute2 >/dev/null 2>&1\n'
                f'TAP_VETH=$(ip -o link show | awk -v i={tap_veth_idx} \'$1 ~ "^"i":" {{split($2,a,"@"); print a[1]}}\')\n'
                f'echo "Tap veth: $TAP_VETH"\n'
                + "\n".join(mirror_cmds)
                + '\necho "TC mirrors configured"'
            )

            result = subprocess.run(
                ["docker", "run", "--rm", "--privileged", "--net=host",
                 "alpine:3.19", "sh", "-c", script],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                logger.info(f"TC mirrors configured for {len(veth_indices)} container veths")
            else:
                logger.warning(f"TC mirror setup returned {result.returncode}: {result.stderr}")

        except Exception as e:
            logger.warning(f"TC mirror setup failed: {e}")

    # ------------------------------------------------------------------
    # GRETAP mirror — Layer 2 tunnel for VPN passive sniffing
    # ------------------------------------------------------------------

    def _setup_gretap_mirror(self, user_id: int, network_name: str):
        """Create a GRETAP tunnel bridged to the lab network, with TC mirrors.

        This gives VPN-connected students a Layer 2 interface (``lab0``)
        on their local machine that receives all broadcast and unicast
        traffic from the lab's Docker bridge.  The client-side ``lab0``
        is created automatically by a PostUp hook in the WireGuard config.

        The tunnel endpoints use the WireGuard VPN IPs (10.0.0.x) so
        GRE packets ride encrypted inside the existing WireGuard tunnel.

        After bridging the GRETAP, TC ingress mirrors are added on every
        lab container's host-side veth so that unicast traffic (not just
        broadcast/multicast) is copied to the GRETAP interface.
        """
        server_ip = "10.0.0.1"  # WireGuard server address
        gre_name = f"gre_u{user_id}"

        try:
            # Read the actual VPN client IP from the DB rather than
            # recalculating it — the stored value is authoritative.
            from app.database import SessionLocal
            from app.models import WireGuardConfig
            db = SessionLocal()
            try:
                wg_config = db.query(WireGuardConfig).filter(
                    WireGuardConfig.user_id == user_id
                ).first()
                if wg_config and wg_config.client_ip:
                    client_ip = wg_config.client_ip
                else:
                    # Fallback: calculate it (may be wrong for legacy users)
                    from app.routers.labs import get_vpn_client_ip
                    from app.config import settings
                    client_ip = get_vpn_client_ip(user_id, settings.WG_CLIENT_BASE)
                    logger.warning(f"No WireGuard config in DB for user {user_id}, using calculated IP {client_ip}")
            finally:
                db.close()
            # Find the Docker bridge interface for this lab network
            network = self.client.networks.get(network_name)
            bridge_name = f"br-{network.id[:12]}"

            script = (
                f"apk add --no-cache iproute2 >/dev/null 2>&1\n"
                f"ip link del {gre_name} 2>/dev/null\n"
                f"ip link add {gre_name} type gretap remote {client_ip} local {server_ip}\n"
                f"ip link set {gre_name} master {bridge_name}\n"
                f"ip link set {gre_name} up\n"
                f"echo 'GRETAP {gre_name} bridged to {bridge_name}'"
            )

            result = subprocess.run(
                ["docker", "run", "--rm", "--privileged", "--net=host",
                 "alpine:3.19", "sh", "-c", script],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0:
                logger.info(f"GRETAP {gre_name} created: {server_ip} <-> {client_ip} on {bridge_name}")
            else:
                logger.warning(f"GRETAP setup failed: {result.stderr}")
                return

            # --- TC mirrors: copy all container veths' ingress → GRETAP ---
            # The GRETAP is a host-level interface so we can use it directly
            # as the mirred target (no veth lookup needed for it).
            #
            # We use the bridge's port list (from `bridge link show`) to find
            # all veth peers on this bridge, rather than checking IPs inside
            # containers.  Some containers (e.g. customer-laptop) have their
            # IP assigned by Docker but not visible via `ip addr` inside the
            # container, so the old IP-based approach missed them.
            veth_indices = []
            try:
                bridge_result = subprocess.run(
                    ["docker", "run", "--rm", "--privileged", "--net=host",
                     "alpine:3.19", "sh", "-c",
                     "apk add --no-cache iproute2 bridge-utils >/dev/null 2>&1; bridge link show"],
                    capture_output=True, text=True, timeout=15
                )
                for line in bridge_result.stdout.splitlines():
                    if bridge_name not in line:
                        continue
                    # Skip the GRETAP interface itself
                    if gre_name in line:
                        continue
                    # Extract the veth index (first number before ":")
                    parts = line.strip().split(":")
                    if parts and parts[0].strip().isdigit():
                        veth_indices.append(parts[0].strip())
            except Exception as e:
                logger.warning(f"Failed to list bridge ports: {e}")

            if not veth_indices:
                logger.debug("No container veths found for GRETAP TC mirror")
                return

            mirror_cmds = []
            for idx in veth_indices:
                mirror_cmds.append(
                    f'VETH=$(ip -o link show | awk -v i={idx} \'$1 ~ "^"i":" {{split($2,a,"@"); print a[1]}}\')'
                    f' && tc qdisc add dev $VETH ingress 2>/dev/null;'
                    f' tc filter add dev $VETH parent ffff: protocol all u32 match u32 0 0'
                    f' action mirred egress mirror dev {gre_name} 2>/dev/null'
                )
            tc_script = (
                f'apk add --no-cache iproute2 >/dev/null 2>&1\n'
                + "\n".join(mirror_cmds)
                + f'\necho "TC mirrors to {gre_name} configured for {len(veth_indices)} veths"'
            )

            tc_result = subprocess.run(
                ["docker", "run", "--rm", "--privileged", "--net=host",
                 "alpine:3.19", "sh", "-c", tc_script],
                capture_output=True, text=True, timeout=30
            )
            if tc_result.returncode == 0:
                logger.info(f"GRETAP TC mirrors configured: {len(veth_indices)} veths → {gre_name}")
            else:
                logger.warning(f"GRETAP TC mirror setup returned {tc_result.returncode}: {tc_result.stderr}")

        except Exception as e:
            logger.warning(f"GRETAP mirror setup failed for user {user_id}: {e}")

    def _teardown_gretap_mirror(self, user_id: int):
        """Remove the GRETAP tunnel for a user (called when lab stops)."""
        gre_name = f"gre_u{user_id}"
        try:
            subprocess.run(
                ["docker", "run", "--rm", "--privileged", "--net=host",
                 "alpine:3.19", "sh", "-c",
                 f"apk add --no-cache iproute2 >/dev/null 2>&1; ip link del {gre_name} 2>/dev/null; echo ok"],
                capture_output=True, text=True, timeout=10
            )
            logger.debug(f"GRETAP {gre_name} removed")
        except Exception:
            pass

    def get_lab_targets(self, user_id: int, lab_slug: str) -> List[Dict]:
        """
        Get list of target containers for a lab session

        Args:
            user_id: User ID
            lab_slug: Lab identifier

        Returns:
            List of target dictionaries with name, ip, and ports
        """
        if not self.client:
            return []
        
        targets = []
        project_name = f"lab_{user_id}_{lab_slug}".lower().lower()
        
        try:
            containers = self.client.containers.list(
                filters={"label": f"com.docker.compose.project={project_name}"}
            )
            
            for container in containers:
                # Get IP from network
                network_name = f"lab_{user_id}_{lab_slug}".lower()
                try:
                    network = self.client.networks.get(network_name)
                    container_info = network.attrs["Containers"].get(container.id, {})
                    ip = container_info.get("IPv4Address", "").split("/")[0]
                except Exception:
                    ip = "unknown"
                
                # Get exposed ports
                ports = []
                if container.attrs.get("NetworkSettings"):
                    port_bindings = container.attrs["NetworkSettings"].get("Ports", {})
                    for port_info in port_bindings.values():
                        if port_info:
                            ports.append(int(port_info[0]["HostPort"]))
                
                targets.append({
                    "name": container.name.replace(f"{project_name}_", ""),
                    "ip": ip,
                    "ports": ports
                })
        except Exception as e:
            logger.error(f"Failed to get lab targets: {e}")
        
        return targets
    
    def destroy_lab_environment(self, user_id: int, lab_slug: str):
        """
        Destroy all containers and network for a lab session
        
        Args:
            user_id: User ID
            lab_slug: Lab identifier
        """
        if not self.client:
            return
        
        project_name = f"lab_{user_id}_{lab_slug}".lower().lower()
        network_name = f"lab_{user_id}_{lab_slug}".lower()
        
        # Stop and remove containers with timeout and force fallback
        track_slug = lab_slug.split("-")[0].lower()
        track_dir_name = get_track_directory_name(track_slug)
        lab_dir = f"/labs/{track_dir_name}/{lab_slug}"
        compose_file = os.path.join(lab_dir, "docker-compose.yml")
        
        # First, try graceful shutdown with timeout
        if os.path.exists(compose_file):
            try:
                logger.info(f"Stopping containers for {lab_slug} (graceful shutdown)")
                result = subprocess.run(
                    ["docker", "compose", "-f", compose_file, "-p", project_name, "down", "-v", "--timeout", "30"],
                    cwd=lab_dir,
                    capture_output=True,
                    text=True,
                    timeout=45  # 45 second timeout (30s for docker + 15s buffer)
                )
                
                if result.returncode == 0:
                    logger.info(f"Successfully stopped containers for {lab_slug}")
                else:
                    logger.warning(f"docker compose down returned non-zero: {result.stderr}")
                    # Fall through to force removal
            except subprocess.TimeoutExpired:
                logger.warning(f"Timeout stopping containers for {lab_slug}, forcing removal")
            except Exception as e:
                logger.error(f"Error during graceful shutdown: {e}")
            
            # Force removal if graceful shutdown failed or timed out
            try:
                logger.info(f"Force removing containers for {lab_slug}")
                # Try docker compose down with --remove-orphans and force
                subprocess.run(
                    ["docker", "compose", "-f", compose_file, "-p", project_name, "down", "-v", "--remove-orphans", "--timeout", "5"],
                    cwd=lab_dir,
                    capture_output=True,
                    text=True,
                    timeout=15  # Short timeout for force removal
                )
                
                # Also try direct container removal as fallback
                try:
                    containers = self.client.containers.list(
                        all=True,
                        filters={"label": f"com.docker.compose.project={project_name}"}
                    )
                    for container in containers:
                        try:
                            if container.status == "running":
                                logger.info(f"Force stopping container: {container.name}")
                                container.stop(timeout=5)
                            container.remove(force=True)
                            logger.info(f"Force removed container: {container.name}")
                        except Exception as e:
                            logger.warning(f"Failed to force remove container {container.name}: {e}")
                except Exception as e:
                    logger.debug(f"Could not list containers for force removal: {e}")
                    
            except subprocess.TimeoutExpired:
                logger.error(f"Force removal also timed out for {lab_slug}")
            except Exception as e:
                logger.error(f"Failed to force remove containers: {e}")
        
        # Remove network tap container (if present)
        tap_name = f"{project_name}-nettap-1"
        try:
            tap = self.client.containers.get(tap_name)
            tap.remove(force=True)
            logger.info(f"Removed network tap {tap_name}")
        except docker.errors.NotFound:
            pass
        except Exception as e:
            logger.debug(f"Could not remove network tap {tap_name}: {e}")

        # Remove GRETAP tunnel (if present)
        self._teardown_gretap_mirror(user_id)

        # Disconnect standalone RangeBox from lab network (if bridged)
        self.unbridge_standalone_rangebox_from_lab(user_id, lab_slug)

        # Remove RangeBox container if present
        self.destroy_rangebox(user_id, lab_slug)

        # Remove network (disconnect containers first if needed)
        # Must remove BOTH the custom lab network AND Docker Compose's
        # auto-created _default network, otherwise the subnet stays allocated.
        for net_name in [network_name, f"{project_name}_default"]:
            try:
                network = self.client.networks.get(net_name)
                # Disconnect any remaining containers
                try:
                    containers = network.attrs.get("Containers", {})
                    for container_id in containers.keys():
                        try:
                            network.disconnect(container_id, force=True)
                        except Exception:
                            pass
                except Exception:
                    pass
                network.remove()
                logger.info(f"Removed network {net_name}")
            except docker.errors.NotFound:
                logger.debug(f"Network {net_name} not found (already removed)")
            except Exception as e:
                logger.error(f"Failed to remove network {net_name}: {e}")

        # Stop shared containers if no other labs still need them.
        # Read the compose file to find which shared containers were used.
        if os.path.exists(compose_file):
            try:
                with open(compose_file) as f:
                    compose_data = yaml.safe_load(f.read()) or {}
                for entry in compose_data.get("x-ocr-shared-containers", []):
                    shared_name = entry.get("name") if isinstance(entry, dict) else str(entry)
                    self._stop_shared_container_if_idle(shared_name)
            except Exception as e:
                logger.debug(f"Could not check shared containers for cleanup: {e}")

    def cleanup_orphaned_networks(self) -> int:
        """
        Find and remove orphaned lab networks that aren't associated with active sessions.
        Returns the number of networks removed.
        """
        if not self.client:
            return 0
        
        removed_count = 0
        
        try:
            from datetime import datetime, timezone, timedelta
            from app.database import SessionLocal
            from app.models import LabSession
            
            # Get all active lab sessions from database
            db = SessionLocal()
            try:
                active_sessions = db.query(LabSession).filter(
                    LabSession.status.in_(["starting", "running", "stopping"])
                ).all()
                
                # Build set of active network names
                active_networks = set()
                for session in active_sessions:
                    if session.lab:
                        network_name = f"lab_{session.user_id}_{session.lab.slug}"
                        active_networks.add(network_name)
            finally:
                db.close()
            
            # Get all networks
            all_networks = self.client.networks.list()
            
            # Find lab networks that aren't active
            for network in all_networks:
                network_name = network.name
                
                # Only process lab networks
                if not network_name.startswith("lab_"):
                    continue
                
                # Check if network belongs to an active session
                is_active = network_name in active_networks
                
                if not is_active:
                    try:
                        # Disconnect any containers
                        containers = network.attrs.get("Containers", {})
                        for container_id in containers.keys():
                            try:
                                network.disconnect(container_id, force=True)
                            except Exception:
                                pass
                        
                        # Remove the network
                        network.remove()
                        removed_count += 1
                        logger.info(f"Removed orphaned network: {network_name}")
                    except Exception as e:
                        logger.warning(f"Failed to remove orphaned network {network_name}: {e}")
        
        except Exception as e:
            logger.error(f"Error cleaning up orphaned networks: {e}")
        
        return removed_count
    
    def cleanup_orphaned_containers(self) -> int:
        """
        Find and remove orphaned lab containers that aren't associated with active sessions.
        Returns the number of containers removed.
        """
        if not self.client:
            return 0
        
        removed_count = 0
        
        try:
            from datetime import datetime, timezone, timedelta
            from app.database import SessionLocal
            from app.models import LabSession
            
            # Get all active lab sessions from database
            db = SessionLocal()
            try:
                active_sessions = db.query(LabSession).filter(
                    LabSession.status == "running"
                ).all()
                
                # Build set of active project names
                active_projects = set()
                for session in active_sessions:
                    if session.lab:
                        project_name = f"lab_{session.user_id}_{session.lab.slug}"
                        active_projects.add(project_name)
            finally:
                db.close()
            
            # Get all containers
            all_containers = self.client.containers.list(all=True)
            
            # Find containers that look like lab containers
            for container in all_containers:
                container_name = container.name
                
                # Skip platform containers (backend, frontend, db)
                if container_name.startswith("ocr-"):
                    continue
                
                # Check if it's a lab container
                is_lab_container = (
                    container_name.startswith("lab_") or 
                    any(pattern in container_name for pattern in [
                        "-webserver-", "-database-", "-target-"
                    ])
                )
                
                if not is_lab_container:
                    continue
                
                try:
                    container_info = container.attrs
                    state = container_info.get("State", {})
                    status = state.get("Status", "")
                    created = container_info.get("Created", "")
                    
                    # Extract project name from container
                    # Format: lab_{user_id}_{lab_slug}-{service}-1
                    # Or: {lab_slug}-{service}-1 (manually started)
                    project_name = None
                    if container_name.startswith("lab_"):
                        # Extract project name (everything before the last dash and number)
                        parts = container_name.rsplit("-", 1)
                        if len(parts) == 2 and parts[1].isdigit():
                            project_name = parts[0]
                    
                    # Check if container belongs to an active session
                    is_active = project_name and project_name in active_projects
                    
                    # Remove if:
                    # 1. Container is stopped/exited and older than 30 minutes, OR
                    # 2. Container doesn't belong to an active session and is older than 30 minutes
                    if status in ["exited", "stopped"] or not is_active:
                        try:
                            created_time = datetime.fromisoformat(created.replace('Z', '+00:00'))
                            age = datetime.now(timezone.utc) - created_time.replace(tzinfo=timezone.utc)
                            
                            # Remove containers older than 30 minutes
                            if age > timedelta(minutes=30):
                                container.remove(force=True)
                                removed_count += 1
                                logger.info(f"Removed orphaned container: {container_name} (age: {age}, status: {status}, active: {is_active})")
                        except Exception as e:
                            logger.debug(f"Could not parse container age for {container_name}: {e}")
                except Exception as e:
                    logger.debug(f"Error processing container {container_name}: {e}")
        
        except Exception as e:
            logger.error(f"Error cleaning up orphaned containers: {e}")
        
        return removed_count
    
    def get_container_health(self, user_id: int, lab_slug: str, include_stats: bool = True) -> List[Dict]:
        """
        Get health status of all containers in a lab environment.

        Args:
            user_id: User ID
            lab_slug: Lab identifier
            include_stats: If True, fetch CPU/memory via container.stats()
                (slow: ~1-2s per container). Pass False for fast status-only checks.

        Returns:
            List of container health dictionaries
        """
        if not self.client:
            return []

        project_name = f"lab_{user_id}_{lab_slug}".lower().lower()
        containers = []

        try:
            container_list = self.client.containers.list(
                filters={"label": f"com.docker.compose.project={project_name}"}
            )

            for container in container_list:
                # Get basic container info
                container_info = {
                    "name": container.name.replace(f"{project_name}_", "").replace(f"lab_{user_id}_{lab_slug}-", ""),
                    "status": container.status,  # running, exited, paused, etc.
                    "health": "none",
                    "cpu_percent": 0.0,
                    "memory_mb": 0
                }

                # Get health status if available
                try:
                    health_status = container.attrs.get("State", {}).get("Health", {}).get("Status")
                    if health_status:
                        container_info["health"] = health_status  # healthy, unhealthy, starting, none
                except Exception:
                    pass

                # Get resource usage stats (expensive: ~1-2s per container)
                if include_stats:
                    try:
                        stats = container.stats(stream=False)

                        # Calculate CPU percentage
                        cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                                    stats["precpu_stats"]["cpu_usage"]["total_usage"]
                        system_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                                       stats["precpu_stats"]["system_cpu_usage"]
                        num_cpus = stats["cpu_stats"].get("online_cpus", 1)

                        if system_delta > 0:
                            container_info["cpu_percent"] = round((cpu_delta / system_delta) * num_cpus * 100, 1)

                        # Calculate memory in MB
                        memory_usage = stats["memory_stats"].get("usage", 0)
                        container_info["memory_mb"] = round(memory_usage / (1024 * 1024), 1)
                    except Exception as e:
                        logger.debug(f"Failed to get stats for {container.name}: {e}")

                containers.append(container_info)

        except Exception as e:
            logger.error(f"Failed to get container health for {project_name}: {e}")

        return containers

    # ==================== RangeBox (Browser-Based Attack Desktop) ====================

    RANGEBOX_IMAGE = os.environ.get("RANGEBOX_IMAGE", "opencyberrange/rangebox:lite")
    UBUNTUBOX_IMAGE = os.environ.get("UBUNTUBOX_IMAGE", "opencyberrange/ubuntubox:latest")
    RANGEBOX_IMAGES = {
        "kali": RANGEBOX_IMAGE,
        "ubuntu": UBUNTUBOX_IMAGE,
    }
    RANGEBOX_MEM_LIMIT = os.environ.get("RANGEBOX_MEM_LIMIT", "2g")
    RANGEBOX_CPU_QUOTA = int(os.environ.get("RANGEBOX_CPU_QUOTA", "50000"))  # 0.5 CPU
    RANGEBOX_NOVNC_PORT = 6080  # websockify port inside the container
    # RangeBox concurrency is computed live from free memory (see the
    # MAX_CONCURRENT_RANGEBOXES property) so the meter can never authorize more
    # boxes than the server can actually hold, and it shrinks automatically when
    # the SIEM or the Security Onion VM are running. Set the MAX_CONCURRENT_RANGEBOXES
    # env var to pin a fixed cap and disable the auto-computation.
    _RANGEBOX_MAX_OVERRIDE = os.environ.get("MAX_CONCURRENT_RANGEBOXES")
    # Memory kept free for the platform itself (backend, DB, SIEM, kernel) and
    # never handed out to RangeBoxes. Raise it if you run the SO VM continuously.
    RANGEBOX_MEM_RESERVE_GB = float(os.environ.get("RANGEBOX_MEM_RESERVE_GB", "8"))
    # Sanity ceiling so a misread of /proc/meminfo can never authorize absurd numbers.
    RANGEBOX_MAX_CEILING = int(os.environ.get("RANGEBOX_MAX_CEILING", "64"))

    @staticmethod
    def _standalone_network_name(user_id: int) -> str:
        return f"ocr-rangebox-standalone-{user_id}"

    @staticmethod
    def _standalone_subnet(user_id: int) -> str:
        """Per-user /24 subnet for standalone RangeBox isolation."""
        octet = (user_id % 240) + 10
        return f"10.50.{octet}.0/24"

    @staticmethod
    def _standalone_rangebox_ip(user_id: int) -> str:
        octet = (user_id % 240) + 10
        return f"10.50.{octet}.10"

    @staticmethod
    def _standalone_backend_ip(user_id: int) -> str:
        octet = (user_id % 240) + 10
        return f"10.50.{octet}.2"

    def _rangebox_container_name(self, user_id: int, lab_slug: str) -> str:
        return f"rangebox_{user_id}_{lab_slug}"

    def _count_running_rangeboxes(self) -> int:
        """Count all running RangeBox containers (lab-based and standalone)."""
        if not self.client:
            return 0
        try:
            containers = self.client.containers.list(
                filters={"label": "ocr.role", "status": "running"}
            )
            return sum(1 for c in containers if "rangebox" in c.labels.get("ocr.role", ""))
        except Exception:
            return 0

    @staticmethod
    def _parse_mem_bytes(value: str) -> int:
        """Parse a docker-style memory string ('2g', '512m', '1024k', '2048') to bytes."""
        s = str(value).strip().lower()
        mult = 1
        if s and s[-1] in "gmk":
            mult = {"g": 1024 ** 3, "m": 1024 ** 2, "k": 1024}[s[-1]]
            s = s[:-1]
        elif s.endswith("b"):
            s = s[:-1]
        try:
            return int(float(s) * mult)
        except ValueError:
            return 2 * 1024 ** 3

    @staticmethod
    def _mem_available_bytes() -> int:
        """Live allocatable RAM of the host these containers run on (the labs VM),
        read from /proc/meminfo. A container sees the node's meminfo, so this is
        the memory free across all sibling containers, which is exactly what gates
        how many more RangeBoxes can start. Returns 0 if it cannot be read."""
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemAvailable:"):
                        return int(line.split()[1]) * 1024  # kB -> bytes
        except Exception:
            pass
        return 0

    @property
    def MAX_CONCURRENT_RANGEBOXES(self) -> int:
        """Live concurrency cap: the boxes already running plus however many more
        the currently free memory can hold, after reserving RANGEBOX_MEM_RESERVE_GB
        for the platform. Tracks reality, so the meter shrinks when the SIEM or the
        Security Onion VM are up and grows when they are stopped. An explicit
        MAX_CONCURRENT_RANGEBOXES env value pins a fixed cap instead."""
        if self._RANGEBOX_MAX_OVERRIDE:
            try:
                return max(0, int(self._RANGEBOX_MAX_OVERRIDE))
            except ValueError:
                pass
        per_box = self._parse_mem_bytes(self.RANGEBOX_MEM_LIMIT) or (2 * 1024 ** 3)
        reserve = int(self.RANGEBOX_MEM_RESERVE_GB * (1024 ** 3))
        avail = self._mem_available_bytes()
        running = self._count_running_rangeboxes()
        if avail <= 0:
            # /proc/meminfo unreadable: do not authorize growth beyond what runs.
            return max(running, 1)
        extra = max(0, (avail - reserve) // per_box)
        return max(running, min(self.RANGEBOX_MAX_CEILING, running + int(extra)))

    def _check_rangebox_capacity(self):
        """Raise RangeBoxCapacityError if the server is at capacity."""
        count = self._count_running_rangeboxes()
        if count >= self.MAX_CONCURRENT_RANGEBOXES:
            raise RangeBoxCapacityError(
                f"Server at capacity ({count}/{self.MAX_CONCURRENT_RANGEBOXES} RangeBoxes running)"
            )

    def _resolve_rangebox_image(self, image: Optional[str] = None) -> str:
        """Resolve a RangeBox image name from a shorthand or return the default."""
        if image and image in self.RANGEBOX_IMAGES:
            return self.RANGEBOX_IMAGES[image]
        return image or self.RANGEBOX_IMAGE

    def _template_instance_env(self, lab_slug: str) -> dict:
        """
        Return the per-instance FLAG / CRED_* env vars for a lab that was
        materialized from an Exercise Studio template, or an empty dict.

        ADDITIVE and backward-compatible: a lab with no template_instances row
        (every lab today) yields ``{}``, so the caller is a strict no-op for it.
        The env map is the one the instantiation engine computed at staging time
        (``template_engine._env_overrides``) and the router persisted on the
        instance's ``override_values`` under the reserved ``env`` key. The
        template's container entrypoints read these names with a baked fallback,
        so injecting them rotates the flag/credentials per instance without
        rebaking the image; injecting nothing leaves the baked defaults intact.

        Never raises: any lookup/parse failure logs and returns ``{}`` so a
        spawn can never be broken by this opt-in path.
        """
        import json
        try:
            from app.database import SessionLocal
            from sqlalchemy import text
            with SessionLocal() as db:
                row = db.execute(
                    text(
                        """
                        SELECT ti.override_values
                        FROM template_instances ti
                        JOIN labs l ON l.id = ti.lab_id
                        WHERE l.slug = :slug
                        ORDER BY ti.id DESC
                        LIMIT 1
                        """
                    ),
                    {"slug": lab_slug},
                ).fetchone()
            if not row or not row[0]:
                return {}
            stored = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            if not isinstance(stored, dict):
                return {}
            env_map = stored.get("env") or {}
            if not isinstance(env_map, dict):
                return {}
            # env_map is per-service: {service_name: {VAR: VALUE}}. Coerce to a
            # clean nested str->str map, dropping anything malformed, so FLAG and
            # credentials land only on the service the template's env_contract
            # scoped them to and are never broadcast into peer containers.
            out = {}
            for svc, vars_ in env_map.items():
                if not isinstance(svc, str) or not isinstance(vars_, dict):
                    continue
                clean = {}
                for k, v in vars_.items():
                    if isinstance(k, str) and v is not None:
                        clean[k] = str(v)
                if clean:
                    out[svc] = clean
            if out:
                logger.info(
                    f"Injecting template-instance env into {len(out)} service(s) "
                    f"for lab {lab_slug}"
                )
            return out
        except Exception as e:
            logger.warning(
                f"Could not look up template-instance env for lab={lab_slug}: {e}"
            )
            return {}

    def _build_rangebox_env(self, user_id: int, lab_slug: str) -> dict:
        """
        Build the environment dict for a student's RangeBox container.

        Always includes RESOLUTION. For per-token-scoped tracks (e.g. ADPT)
        also injects OCR_SCOPE_TOKEN by looking up the user's enrollment in
        any course that has this lab assigned. Workbook commands like
        ``svc_kerb_${OCR_SCOPE_TOKEN}`` then evaluate to the right per-token
        AD object inside the student's shell automatically.
        """
        env = {"RESOLUTION": "1280x800"}
        try:
            from app.database import SessionLocal
            from sqlalchemy import text
            with SessionLocal() as db:
                row = db.execute(
                    text(
                        """
                        SELECT ce.scope_token
                        FROM course_enrollments ce
                        JOIN course_lab_assignments cla ON cla.course_id = ce.course_id
                        JOIN labs l ON l.id = cla.lab_id
                        WHERE ce.user_id = :uid
                          AND l.slug = :slug
                          AND ce.scope_token IS NOT NULL
                        ORDER BY ce.id DESC
                        LIMIT 1
                        """
                    ),
                    {"uid": user_id, "slug": lab_slug},
                ).fetchone()
                if row and row[0]:
                    env["OCR_SCOPE_TOKEN"] = row[0].strip()
                    logger.info(
                        f"Injecting OCR_SCOPE_TOKEN={env['OCR_SCOPE_TOKEN']} "
                        f"into RangeBox for user {user_id} / lab {lab_slug}"
                    )
        except Exception as e:
            logger.warning(f"Could not look up scope_token for user={user_id} lab={lab_slug}: {e}")
        return env

    def spawn_rangebox(self, user_id: int, lab_slug: str, network_name: str, image: Optional[str] = None) -> Optional[str]:
        """
        Spawn a RangeBox container on the lab network.

        Args:
            image: Docker image or shorthand ("kali", "ubuntu"). Defaults to RANGEBOX_IMAGE.

        Returns the container ID on success, or None on failure.
        Raises RangeBoxCapacityError if the server is at capacity.
        """
        if not self.client:
            logger.error("Docker client not available — cannot spawn RangeBox")
            return None

        self._check_rangebox_capacity()

        self.ensure_lab_network_isolation()
        self.ensure_inbound_isolation()

        container_name = self._rangebox_container_name(user_id, lab_slug)

        # Remove any leftover RangeBox container with the same name
        try:
            old = self.client.containers.get(container_name)
            logger.warning(f"Removing leftover RangeBox container {container_name}")
            old.remove(force=True)
            time.sleep(0.5)
        except docker.errors.NotFound:
            pass
        except Exception as e:
            logger.warning(f"Error removing leftover RangeBox {container_name}: {e}")

        second_octet, third_octet = get_subnet_id(user_id, lab_slug)
        # Use the same last-octet as the student's WireGuard VPN IP
        # so lab targets see the same source IP regardless of connection method
        vpn_suffix = get_vpn_client_suffix(user_id)
        rangebox_ip = f"10.{second_octet}.{third_octet}.{vpn_suffix}"

        resolved_image = self._resolve_rangebox_image(image)

        try:
            # Security note: no-new-privileges is intentionally NOT set.
            # It would break sudo, which students need for pentesting tools
            # (nmap SYN scan, tcpdump, service enumeration, etc.).
            # Mitigation: cap_drop=ALL limits what sudo can actually do.
            container = self.client.containers.run(
                image=resolved_image,
                name=container_name,
                detach=True,
                shm_size="256m",
                mem_limit=self.RANGEBOX_MEM_LIMIT,
                memswap_limit=self.RANGEBOX_MEM_LIMIT,  # no swap
                cpu_period=100000,
                cpu_quota=self.RANGEBOX_CPU_QUOTA,
                pids_limit=512,
                cap_drop=["ALL"],
                cap_add=[
                    "NET_RAW",          # nmap SYN scan, tcpdump
                    "NET_ADMIN",        # iptables gateway blocking, network config
                    "SETUID",           # sudo
                    "SETGID",           # sudo / group switching
                    "DAC_OVERRIDE",     # root file access via sudo
                    "CHOWN",            # file ownership changes
                    "FOWNER",           # file permission changes
                    "KILL",             # process management (kill, pkill)
                    "NET_BIND_SERVICE", # bind to ports <1024 (e.g. nc -lvp 80)
                    "SYS_CHROOT",       # chroot (some tools use it)
                ],

                environment=self._build_rangebox_env(user_id, lab_slug),
                labels={
                    "ocr.role": "rangebox",
                    "ocr.user_id": str(user_id),
                    "ocr.lab_slug": lab_slug,
                    "ocr.image": resolved_image,
                },
            )

            # Attach to the lab network with the designated IP (falling back to
            # a free address if the VPN-suffix IP collides with a lab service)
            try:
                network = self.client.networks.get(network_name)
                connect_ip = self._resolve_free_lab_ip(network, rangebox_ip)
                network.connect(container, ipv4_address=connect_ip)
            except Exception as e:
                logger.error(f"Failed to connect RangeBox to network {network_name}: {e}")
                container.remove(force=True)
                return None

            # Disconnect from default bridge so RangeBox is isolated to the
            # lab network — prevents reaching the host / home network.
            try:
                default_bridge = self.client.networks.get("bridge")
                default_bridge.disconnect(container)
                logger.info(f"Disconnected RangeBox {container_name} from default bridge for isolation")
            except Exception as e:
                logger.warning(f"Could not disconnect RangeBox from default bridge: {e}")

            # Create a dedicated proxy network so the backend can reach
            # the RangeBox for VNC proxying WITHOUT joining the lab network.
            # This prevents students from seeing the backend via nmap.
            proxy_network_name = f"ocr-proxy-{user_id}-{lab_slug}"
            proxy_subnet = f"10.200.{third_octet}.0/30"
            proxy_rangebox_ip = f"10.200.{third_octet}.1"
            proxy_backend_ip = f"10.200.{third_octet}.2"
            try:
                try:
                    proxy_net = self.client.networks.get(proxy_network_name)
                except docker.errors.NotFound:
                    proxy_net = self.client.networks.create(
                        proxy_network_name,
                        driver="bridge",
                        ipam=docker.types.IPAMConfig(
                            pool_configs=[docker.types.IPAMPool(subnet=proxy_subnet)]
                        ),
                        labels={"ocr.role": "rangebox-proxy", "ocr.user_id": str(user_id)},
                    )
                proxy_net.connect(container, ipv4_address=proxy_rangebox_ip)
                # Attach backend to proxy network (not the lab network)
                backend = self.client.containers.get(_BACKEND_CONTAINER)
                backend_networks = backend.attrs.get("NetworkSettings", {}).get("Networks", {})
                if proxy_network_name not in backend_networks:
                    proxy_net.connect(backend, ipv4_address=proxy_backend_ip)
                    logger.info(f"Attached ocr-backend to proxy network {proxy_network_name} at {proxy_backend_ip}")
            except docker.errors.NotFound:
                logger.warning("ocr-backend container not found — VNC proxy may not work")
            except Exception as e:
                logger.warning(f"Failed to set up proxy network {proxy_network_name}: {e}")

            logger.info(f"RangeBox spawned: {container_name} ({container.short_id}) at {rangebox_ip} using {resolved_image}")
            return container.id

        except docker.errors.ImageNotFound:
            logger.error(
                f"RangeBox image '{resolved_image}' not found. "
                f"Build it with: docker build -t {resolved_image} RangeBox/ (or UbuntuBox/)"
            )
            return None
        except Exception as e:
            logger.error(f"Failed to spawn RangeBox for user {user_id}: {e}")
            return None

    def destroy_rangebox(self, user_id: int, lab_slug: str):
        """Stop and remove the RangeBox container for a lab session."""
        if not self.client:
            return

        container_name = self._rangebox_container_name(user_id, lab_slug)
        try:
            container = self.client.containers.get(container_name)
            container.stop(timeout=10)
            container.remove(force=True)
            logger.info(f"RangeBox destroyed: {container_name}")
        except docker.errors.NotFound:
            logger.debug(f"RangeBox {container_name} not found (already removed)")
        except Exception as e:
            logger.warning(f"Error destroying RangeBox {container_name}: {e}")
            # Force-remove as fallback
            try:
                container = self.client.containers.get(container_name)
                container.remove(force=True)
            except Exception:
                pass

        # Clean up the proxy network (backend ↔ RangeBox VNC proxy path)
        proxy_network_name = f"ocr-proxy-{user_id}-{lab_slug}"
        try:
            proxy_net = self.client.networks.get(proxy_network_name)
            # Disconnect backend before removing
            try:
                backend = self.client.containers.get(_BACKEND_CONTAINER)
                proxy_net.disconnect(backend)
            except Exception:
                pass
            proxy_net.remove()
            logger.info(f"Removed proxy network {proxy_network_name}")
        except docker.errors.NotFound:
            pass  # network already gone
        except Exception as e:
            logger.debug(f"Could not remove proxy network {proxy_network_name}: {e}")

    def get_rangebox_ip(self, user_id: int, lab_slug: str) -> Optional[str]:
        """Return the RangeBox IP on the proxy network (reachable by backend).
        The proxy network isolates backend-to-RangeBox traffic from the lab network."""
        _, third_octet = get_subnet_id(user_id, lab_slug)
        return f"10.200.{third_octet}.1"

    def get_rangebox_status(self, user_id: int, lab_slug: str, include_stats: bool = True) -> dict:
        """Get RangeBox container status and resource usage."""
        if not self.client:
            return {"status": "unavailable"}

        container_name = self._rangebox_container_name(user_id, lab_slug)
        try:
            container = self.client.containers.get(container_name)
            info = {
                "status": container.status,
                "container_id": container.short_id,
                "ip": self.get_rangebox_ip(user_id, lab_slug),
                "novnc_port": self.RANGEBOX_NOVNC_PORT,
            }

            # Resource usage (expensive: ~1-2s per container)
            if include_stats:
                try:
                    stats = container.stats(stream=False)
                    cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                                stats["precpu_stats"]["cpu_usage"]["total_usage"]
                    system_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                                   stats["precpu_stats"]["system_cpu_usage"]
                    num_cpus = stats["cpu_stats"].get("online_cpus", 1)
                    if system_delta > 0:
                        info["cpu_percent"] = round((cpu_delta / system_delta) * num_cpus * 100, 1)
                    memory_usage = stats["memory_stats"].get("usage", 0)
                    info["memory_mb"] = round(memory_usage / (1024 * 1024), 1)
                except Exception:
                    pass

            return info
        except docker.errors.NotFound:
            return {"status": "not_found"}
        except Exception as e:
            logger.warning(f"Error getting RangeBox status: {e}")
            return {"status": "error", "detail": str(e)}

    # ==================== Standalone RangeBox ====================

    def ensure_standalone_rangebox_network(self, user_id: int) -> str:
        """
        Create a per-user standalone RangeBox network if it doesn't exist,
        and ensure the backend container is attached to it.

        Each user gets their own isolated /24 to prevent cross-user visibility.
        Returns the network name.
        """
        if not self.client:
            raise Exception("Docker client not available")

        network_name = self._standalone_network_name(user_id)
        subnet = self._standalone_subnet(user_id)
        backend_ip = self._standalone_backend_ip(user_id)

        try:
            network = self.client.networks.get(network_name)
        except docker.errors.NotFound:
            network = self.client.networks.create(
                network_name,
                driver="bridge",
                ipam=docker.types.IPAMConfig(
                    driver="default",
                    pool_configs=[
                        docker.types.IPAMPool(subnet=subnet)
                    ]
                ),
                labels={
                    "ocr.role": "rangebox-standalone",
                    "ocr.user_id": str(user_id),
                },
            )
            logger.info(f"Created standalone RangeBox network {network_name} ({subnet})")

        # Ensure ocr-backend is attached so VNC proxy can reach containers
        try:
            backend = self.client.containers.get(_BACKEND_CONTAINER)
            backend_networks = backend.attrs.get("NetworkSettings", {}).get("Networks", {})
            if network_name not in backend_networks:
                network.connect(backend, ipv4_address=backend_ip)
                logger.info(f"Attached ocr-backend to {network_name} at {backend_ip}")
        except docker.errors.NotFound:
            logger.warning("ocr-backend container not found — cannot attach to standalone RangeBox network")
        except Exception as e:
            logger.warning(f"Failed to attach ocr-backend to {network_name}: {e}")

        return network_name

    def _resolve_free_lab_ip(self, network, desired_ip: str) -> str:
        """Return ``desired_ip`` if free on ``network``, else a free high host octet.

        The RangeBox's lab IP is derived from the user's VPN suffix
        ((user_id % 240) + 10), which can collide with a lab service's
        ip_offset — e.g. user 2 maps to .12, but a lab may already place an
        ``inject`` container at .12.  A collision leaves the RangeBox connected
        with no IP and unable to reach any lab target, so fall back to a free
        address, scanning the high end of the /24 downward.  Lab authors assign
        service offsets low, so .250 downward is effectively reserved for the
        RangeBox and keeps the source IP stable across restarts.
        """
        try:
            network.reload()
        except Exception:
            pass
        used = set()
        for c in (network.attrs.get("Containers") or {}).values():
            ip = (c.get("IPv4Address") or "").split("/")[0]
            if ip:
                used.add(ip)
        if desired_ip and desired_ip not in used:
            return desired_ip
        if not desired_ip or "." not in desired_ip:
            return desired_ip
        base = desired_ip.rsplit(".", 1)[0]
        # Avoid .0/.255 (network/broadcast) and .254 (lab gateway); scan high->low.
        for octet in range(250, 10, -1):
            candidate = f"{base}.{octet}"
            if candidate not in used:
                logger.info(
                    f"RangeBox IP {desired_ip} already in use on {network.name}; "
                    f"using free {candidate} instead"
                )
                return candidate
        # Subnet somehow full — return desired and let Docker surface the error.
        logger.warning(f"No free host octet on {network.name} for RangeBox; keeping {desired_ip}")
        return desired_ip

    def bridge_standalone_rangebox_to_lab(self, user_id: int, lab_slug: str, network_owner_id: int = None):
        """
        Connect a running standalone RangeBox to a lab network so the student
        can reach lab targets from the RangeBox desktop.

        The VNC proxy reaches the RangeBox through the standalone network
        (10.50.0.0/24), so ocr-backend does NOT need to join the lab
        network here — keeping it off prevents students from seeing the
        backend (port 8000) in nmap scans.

        Safe to call even if no standalone RangeBox is running — it simply
        does nothing in that case.

        If network_owner_id is provided, the RangeBox belonging to user_id
        is bridged to the lab network owned by network_owner_id (used for
        admin impersonation).

        Returns True if the bridge was established, False otherwise.
        """
        if not self.client:
            return False

        net_owner = network_owner_id if network_owner_id is not None else user_id
        container_name = f"rangebox_{user_id}_standalone"
        network_name = f"lab_{net_owner}_{lab_slug}"
        second_octet, third_octet = get_subnet_id(net_owner, lab_slug)
        vpn_suffix = get_vpn_client_suffix(user_id)
        rangebox_ip = f"10.{second_octet}.{third_octet}.{vpn_suffix}"

        import time as _t
        # Retry up to 3 times with short delays to handle container startup timing
        for attempt in range(3):
            try:
                container = self.client.containers.get(container_name)
                if container.status == "running":
                    break
                logger.debug(f"RangeBox {container_name} not running yet (attempt {attempt + 1})")
            except docker.errors.NotFound:
                logger.debug(f"RangeBox {container_name} not found (attempt {attempt + 1})")
            if attempt < 2:
                _t.sleep(2)
        else:
            logger.warning(f"RangeBox {container_name} not available after retries — skipping bridge")
            return False

        try:
            network = self.client.networks.get(network_name)
        except docker.errors.NotFound:
            logger.warning(f"Lab network {network_name} not found — cannot bridge standalone RangeBox")
            return False

        # Check if already connected
        container.reload()
        container_networks = container.attrs.get("NetworkSettings", {}).get("Networks", {})
        existing = container_networks.get(network_name)
        if existing:
            if existing.get("IPAddress"):
                logger.debug(f"Standalone RangeBox already connected to {network_name}")
                return True
            # Connected but with no IP — an earlier collision left the endpoint
            # unroutable (the exact failure this fallback exists to fix).
            # Drop the dead endpoint so we can reconnect with a free address.
            logger.warning(
                f"Standalone RangeBox connected to {network_name} with no IP; reconnecting"
            )
            try:
                network.disconnect(container, force=True)
            except Exception as e:
                logger.warning(f"Failed to drop stale RangeBox endpoint on {network_name}: {e}")

        try:
            connect_ip = self._resolve_free_lab_ip(network, rangebox_ip)
            network.connect(container, ipv4_address=connect_ip)
            logger.info(f"Bridged standalone RangeBox {container_name} to {network_name} at {connect_ip}")

            # If this lab has a network tap, set up TC mirrors so the
            # RangeBox can passively sniff all inter-container traffic
            # (Docker bridges only forward unicast to the destination MAC).
            self._setup_tc_mirror_for_rangebox(container, network_name)

            return True
        except Exception as e:
            logger.warning(f"Failed to bridge standalone RangeBox to {network_name}: {e}")
            return False

    def _setup_tc_mirror_for_rangebox(self, rangebox_container, network_name):
        """Set up TC ingress mirrors so the RangeBox sees all unicast traffic.

        Uses ``bridge link show`` to find every veth on the lab bridge,
        then mirrors their ingress to the RangeBox's host-side veth.
        This approach works even for containers whose IP is not visible
        via ``ip addr`` inside the container (e.g. customer-laptop).
        """
        import time as _t
        try:
            # Determine which interface on the RangeBox is the lab network.
            # It's NOT eth0 by default - it may be eth0 or eth1 depending on
            # connect order.  Find the one whose IP matches the lab subnet.
            # Retry several times because the interface may not be fully
            # plumbed inside the container immediately after network.connect().
            rb_iface = None
            lab_ip = None
            for attempt in range(6):
                if attempt > 0:
                    _t.sleep(0.5)
                rangebox_container.reload()
                rb_networks = rangebox_container.attrs.get("NetworkSettings", {}).get("Networks", {})
                if network_name not in rb_networks:
                    continue

                lab_ip = rb_networks[network_name].get("IPAddress", "")
                if not lab_ip:
                    continue

                for iface_name in ["eth0", "eth1", "eth2"]:
                    try:
                        result = rangebox_container.exec_run(
                            f"sh -c 'ip -4 addr show {iface_name} 2>/dev/null | grep -o \"inet [0-9.]*\" | cut -d\" \" -f2'",
                            demux=True
                        )
                        iface_ip = result.output[0].decode().strip() if result.output[0] else ""
                        if iface_ip == lab_ip:
                            rb_iface = iface_name
                            break
                    except Exception:
                        continue
                if rb_iface:
                    break

            if not rb_iface:
                logger.warning(f"Could not identify RangeBox lab interface after retries (lab_ip={lab_ip}) - skipping TC mirror")
                return

            # Get the RangeBox's host-side veth index
            result = rangebox_container.exec_run(
                f"cat /sys/class/net/{rb_iface}/iflink", demux=True
            )
            rb_veth_idx = result.output[0].decode().strip() if result.output[0] else None
            if not rb_veth_idx:
                return

            # Use `bridge link show` to find ALL veths on the lab bridge.
            # This works for every container regardless of whether `ip addr`
            # shows the IP inside the container.
            try:
                network = self.client.networks.get(network_name)
                bridge_name = f"br-{network.id[:12]}"
            except Exception:
                logger.warning(f"Could not resolve bridge name for {network_name}")
                return

            veth_indices = []
            try:
                bridge_result = subprocess.run(
                    ["docker", "run", "--rm", "--privileged", "--net=host",
                     "alpine:3.19", "sh", "-c",
                     "apk add --no-cache iproute2 bridge-utils >/dev/null 2>&1; bridge link show"],
                    capture_output=True, text=True, timeout=15
                )
                for line in bridge_result.stdout.splitlines():
                    if bridge_name not in line:
                        continue
                    # Skip GRE tunnel interfaces (not veths)
                    if "gre_" in line:
                        continue
                    parts = line.strip().split(":")
                    if parts and parts[0].strip().isdigit():
                        idx = parts[0].strip()
                        # Skip the RangeBox's own veth
                        if idx == rb_veth_idx:
                            continue
                        veth_indices.append(idx)
            except Exception as e:
                logger.warning(f"Failed to list bridge ports for RangeBox mirror: {e}")

            if not veth_indices:
                logger.debug("No container veths found for RangeBox TC mirror")
                return

            # Build mirror commands
            mirror_cmds = []
            for idx in veth_indices:
                mirror_cmds.append(
                    f'VETH=$(ip -o link show | awk -v i={idx} \'$1 ~ "^"i":" {{split($2,a,"@"); print a[1]}}\')'
                    f' && tc qdisc add dev $VETH ingress 2>/dev/null;'
                    f' tc filter add dev $VETH parent ffff: protocol all u32 match u32 0 0'
                    f' action mirred egress mirror dev $RB_VETH 2>/dev/null'
                )
            script = (
                f'apk add --no-cache iproute2 >/dev/null 2>&1\n'
                f'RB_VETH=$(ip -o link show | awk -v i={rb_veth_idx} \'$1 ~ "^"i":" {{split($2,a,"@"); print a[1]}}\')\n'
                f'echo "RangeBox veth: $RB_VETH"\n'
                + "\n".join(mirror_cmds)
                + '\necho "RangeBox TC mirrors configured"'
            )

            result = subprocess.run(
                ["docker", "run", "--rm", "--privileged", "--net=host",
                 "alpine:3.19", "sh", "-c", script],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                logger.info(f"RangeBox TC mirrors configured for {len(veth_indices)} container veths")
            else:
                logger.warning(f"RangeBox TC mirror setup returned {result.returncode}: {result.stderr}")

        except Exception as e:
            logger.debug(f"RangeBox TC mirror setup failed (non-fatal): {e}")

    def unbridge_standalone_rangebox_from_lab(self, user_id: int, lab_slug: str, network_owner_id: int = None):
        """
        Disconnect a standalone RangeBox from a lab network (called when
        a lab is stopped).  The RangeBox itself stays running on its own
        standalone network.

        If network_owner_id is provided, disconnects user_id's RangeBox
        from network_owner_id's lab network (used for admin impersonation).
        """
        if not self.client:
            return

        net_owner = network_owner_id if network_owner_id is not None else user_id
        container_name = f"rangebox_{user_id}_standalone"
        network_name = f"lab_{net_owner}_{lab_slug}"

        try:
            container = self.client.containers.get(container_name)
            network = self.client.networks.get(network_name)
            network.disconnect(container)
            logger.info(f"Unbridged standalone RangeBox {container_name} from {network_name}")
        except docker.errors.NotFound:
            pass  # Container or network already gone
        except Exception as e:
            logger.debug(f"Could not unbridge standalone RangeBox from {network_name}: {e}")

    def spawn_standalone_rangebox(self, user_id: int, image: Optional[str] = None, username: Optional[str] = None) -> Optional[str]:
        """
        Spawn a standalone RangeBox (not tied to any lab session).

        Args:
            image: Docker image or shorthand ("kali", "ubuntu"). Defaults to RANGEBOX_IMAGE.
            username: Platform username to display in shell prompt (e.g. "instructor@ocr").

        One per user. Returns the container ID on success, or None.
        Raises RangeBoxCapacityError if the server is at capacity.
        """
        if not self.client:
            logger.error("Docker client not available — cannot spawn standalone RangeBox")
            return None

        self._check_rangebox_capacity()
        self.ensure_lab_network_isolation()
        self.ensure_inbound_isolation()

        container_name = f"rangebox_{user_id}_standalone"

        # If already running, return existing
        try:
            existing = self.client.containers.get(container_name)
            if existing.status == "running":
                logger.info(f"Standalone RangeBox already running for user {user_id}")
                return existing.id
            logger.warning(f"Removing stopped standalone RangeBox {container_name}")
            existing.remove(force=True)
            time.sleep(0.5)
        except docker.errors.NotFound:
            pass
        except Exception as e:
            logger.warning(f"Error checking existing standalone RangeBox {container_name}: {e}")

        try:
            network_name = self.ensure_standalone_rangebox_network(user_id)
        except Exception as e:
            logger.error(f"Failed to ensure standalone RangeBox network: {e}")
            return None

        rangebox_ip = self._standalone_rangebox_ip(user_id)

        resolved_image = self._resolve_rangebox_image(image)

        try:
            # Security note: no-new-privileges is intentionally NOT set.
            # It would break sudo, which students need for pentesting tools
            # (nmap SYN scan, tcpdump, service enumeration, etc.).
            # Mitigation: cap_drop=ALL limits what sudo can actually do.
            # Hostname shows in the shell prompt and is auto-written to /etc/hosts
            # by Docker. Use the OS name, not "ocr": a self-referencing "ocr"
            # entry looked like a planted target inside the pentest box and
            # leaked the platform brand.
            box_hostname = "ubuntu" if str(image or "").lower().startswith("ubuntu") else "kali"
            container = self.client.containers.run(
                image=resolved_image,
                name=container_name,
                hostname=box_hostname,
                detach=True,
                shm_size="256m",
                mem_limit=self.RANGEBOX_MEM_LIMIT,
                memswap_limit=self.RANGEBOX_MEM_LIMIT,
                cpu_period=100000,
                cpu_quota=self.RANGEBOX_CPU_QUOTA,
                pids_limit=512,
                cap_drop=["ALL"],
                cap_add=[
                    "NET_RAW",          # nmap SYN scan, tcpdump
                    "NET_ADMIN",        # iptables gateway blocking, network config
                    "SETUID",           # sudo
                    "SETGID",           # sudo / group switching
                    "DAC_OVERRIDE",     # root file access via sudo
                    "CHOWN",            # file ownership changes
                    "FOWNER",           # file permission changes
                    "KILL",             # process management (kill, pkill)
                    "NET_BIND_SERVICE", # bind to ports <1024 (e.g. nc -lvp 80)
                    "SYS_CHROOT",       # chroot (some tools use it)
                ],

                environment={
                    "RESOLUTION": "1280x800",
                    "OCR_USERNAME": username or "",
                    # Standalone RangeBox is not lab-scoped, so no OCR_SCOPE_TOKEN
                    # injection here. Per-token scoping only applies to spawn_rangebox().
                },
                labels={
                    "ocr.role": "rangebox-standalone",
                    "ocr.user_id": str(user_id),
                    "ocr.image": resolved_image,
                    "ocr.expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                },
            )

            try:
                network = self.client.networks.get(network_name)
                network.connect(container, ipv4_address=rangebox_ip)
            except Exception as e:
                logger.error(f"Failed to connect standalone RangeBox to network {network_name}: {e}")
                container.remove(force=True)
                return None

            # Disconnect from default bridge so RangeBox is isolated —
            # prevents reaching the host / home network.
            try:
                default_bridge = self.client.networks.get("bridge")
                default_bridge.disconnect(container)
                logger.info(f"Disconnected standalone RangeBox {container_name} from default bridge for isolation")
            except Exception as e:
                logger.warning(f"Could not disconnect standalone RangeBox from default bridge: {e}")

            logger.info(f"Standalone RangeBox spawned: {container_name} ({container.short_id}) at {rangebox_ip} using {resolved_image}")

            # If the user already has a running lab, bridge the RangeBox to it.
            # Filter out Docker Compose "_default" networks -- they use a
            # random subnet and the computed rangebox IP won't fit.
            try:
                lab_networks = [
                    n for n in self.client.networks.list()
                    if n.name.startswith(f"lab_{user_id}_") and not n.name.endswith("_default")
                ]
                for lab_net in lab_networks:
                    lab_slug = lab_net.name.replace(f"lab_{user_id}_", "", 1)
                    self.bridge_standalone_rangebox_to_lab(user_id, lab_slug)
            except Exception as e:
                logger.warning(f"Failed to bridge standalone RangeBox to existing lab networks: {e}")

            return container.id

        except docker.errors.ImageNotFound:
            logger.error(
                f"RangeBox image '{resolved_image}' not found. "
                f"Build it with: docker build -t {resolved_image} RangeBox/ (or UbuntuBox/)"
            )
            return None
        except Exception as e:
            logger.error(f"Failed to spawn standalone RangeBox for user {user_id}: {e}")
            return None

    def destroy_standalone_rangebox(self, user_id: int):
        """Stop and remove the standalone RangeBox container and its per-user network."""
        if not self.client:
            return

        container_name = f"rangebox_{user_id}_standalone"
        try:
            container = self.client.containers.get(container_name)
            container.stop(timeout=10)
            container.remove(force=True)
            logger.info(f"Standalone RangeBox destroyed: {container_name}")
        except docker.errors.NotFound:
            logger.debug(f"Standalone RangeBox {container_name} not found (already removed)")
        except Exception as e:
            logger.warning(f"Error destroying standalone RangeBox {container_name}: {e}")
            try:
                container = self.client.containers.get(container_name)
                container.remove(force=True)
            except Exception:
                pass

        # Clean up the per-user standalone network
        network_name = self._standalone_network_name(user_id)
        try:
            network = self.client.networks.get(network_name)
            # Disconnect backend before removing the network
            try:
                backend = self.client.containers.get(_BACKEND_CONTAINER)
                network.disconnect(backend)
            except Exception:
                pass
            network.remove()
            logger.info(f"Removed standalone network {network_name}")
        except docker.errors.NotFound:
            pass
        except Exception as e:
            logger.debug(f"Could not remove standalone network {network_name}: {e}")

    def get_standalone_rangebox_ip(self, user_id: int) -> str:
        """Return the IP address for a user's standalone RangeBox."""
        return self._standalone_rangebox_ip(user_id)

    def get_standalone_rangebox_status(self, user_id: int, include_stats: bool = True) -> dict:
        """Get standalone RangeBox container status."""
        if not self.client:
            return {"status": "unavailable"}

        container_name = f"rangebox_{user_id}_standalone"
        try:
            container = self.client.containers.get(container_name)
            # Determine image shorthand from label
            image_label = container.labels.get("ocr.image", "")
            if "ubuntubox" in image_label.lower():
                image_name = "ubuntu"
            else:
                image_name = "kali"

            # Parse expiration from label
            expires_at_str = container.labels.get("ocr.expires_at", "")
            expires_at = None
            time_remaining = None
            if expires_at_str:
                try:
                    expires_at = datetime.fromisoformat(expires_at_str)
                    if expires_at.tzinfo is None:
                        expires_at = expires_at.replace(tzinfo=timezone.utc)
                    remaining = (expires_at - datetime.now(timezone.utc)).total_seconds()
                    time_remaining = max(0, int(remaining))
                except Exception:
                    pass

            info = {
                "status": container.status,
                "container_id": container.short_id,
                "ip": self.get_standalone_rangebox_ip(user_id),
                "novnc_port": self.RANGEBOX_NOVNC_PORT,
                "image": image_name,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "time_remaining": time_remaining,
            }

            # Resource usage (expensive: ~1-2s per container)
            if include_stats:
                try:
                    stats = container.stats(stream=False)
                    cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                                stats["precpu_stats"]["cpu_usage"]["total_usage"]
                    system_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                                   stats["precpu_stats"]["system_cpu_usage"]
                    num_cpus = stats["cpu_stats"].get("online_cpus", 1)
                    if system_delta > 0:
                        info["cpu_percent"] = round((cpu_delta / system_delta) * num_cpus * 100, 1)
                    memory_usage = stats["memory_stats"].get("usage", 0)
                    info["memory_mb"] = round(memory_usage / (1024 * 1024), 1)
                except Exception:
                    pass

            return info
        except docker.errors.NotFound:
            return {"status": "not_found"}
        except Exception as e:
            logger.warning(f"Error getting standalone RangeBox status: {e}")
            return {"status": "error", "detail": str(e)}

    # ==================== Docker Disk Management ====================

    def get_disk_usage(self) -> dict:
        """Return Docker disk usage broken down by category.

        Returns a dict with images, containers, build_cache, and volumes,
        each containing total_bytes, reclaimable_bytes, and count.
        """
        if not self.client:
            return {"error": "Docker client not available"}

        try:
            usage = self.client.df()

            # Images
            images = usage.get("Images") or []
            img_total = sum(i.get("Size", 0) for i in images)
            # Reclaimable = images not referenced by any container
            img_reclaimable = sum(
                i.get("Size", 0) for i in images
                if i.get("Containers", 0) == 0
            )

            # Containers
            containers = usage.get("Containers") or []
            ctr_total = sum(c.get("SizeRw", 0) for c in containers)

            # Volumes
            volumes = usage.get("Volumes") or []
            vol_total = sum(v.get("UsageData", {}).get("Size", 0) for v in volumes)
            vol_reclaimable = sum(
                v.get("UsageData", {}).get("Size", 0) for v in volumes
                if v.get("UsageData", {}).get("RefCount", 1) == 0
            )

            # Build cache
            build_cache = usage.get("BuildCache") or []
            bc_total = sum(b.get("Size", 0) for b in build_cache)
            bc_reclaimable = sum(
                b.get("Size", 0) for b in build_cache
                if not b.get("InUse", False)
            )

            return {
                "images": {
                    "count": len(images),
                    "total_bytes": img_total,
                    "reclaimable_bytes": img_reclaimable,
                },
                "containers": {
                    "count": len(containers),
                    "total_bytes": ctr_total,
                },
                "build_cache": {
                    "count": len(build_cache),
                    "total_bytes": bc_total,
                    "reclaimable_bytes": bc_reclaimable,
                },
                "volumes": {
                    "count": len(volumes),
                    "total_bytes": vol_total,
                    "reclaimable_bytes": vol_reclaimable,
                },
            }
        except Exception as e:
            logger.error(f"Failed to get Docker disk usage: {e}")
            return {"error": str(e)}

    def get_lab_images(self, lab_slug: str) -> list:
        """Find all Docker images associated with a lab slug.

        Checks for images built by docker-compose with project names matching
        the prebuild convention (prebuild-{slug}) and any per-user builds
        (lab_{user_id}_{slug}).
        """
        if not self.client:
            return []

        matching = []
        try:
            all_images = self.client.images.list(all=False)
            for img in all_images:
                tags = img.tags or []
                # Match prebuild images (prebuild-{slug}-{service}:latest)
                # and user-session images (lab_{uid}_{slug}-{service}:latest)
                for tag in tags:
                    repo = tag.split(":")[0]
                    if (repo.startswith(f"prebuild-{lab_slug}-") or
                            f"_{lab_slug}-" in repo):
                        matching.append({
                            "id": img.short_id,
                            "tags": tags,
                            "size_bytes": img.attrs.get("Size", 0),
                        })
                        break
        except Exception as e:
            logger.error(f"Failed to list images for {lab_slug}: {e}")

        return matching

    def delete_lab_images(self, lab_slug: str) -> dict:
        """Delete all cached Docker images for a specific exercise.

        Returns a summary with the number of images removed and bytes freed.
        """
        if not self.client:
            return {"removed": 0, "bytes_freed": 0, "error": "Docker client not available"}

        images = self.get_lab_images(lab_slug)
        removed = 0
        bytes_freed = 0
        errors = []

        for img_info in images:
            try:
                # Remove by first tag (most reliable)
                tag = img_info["tags"][0] if img_info["tags"] else img_info["id"]
                self.client.images.remove(tag, force=True)
                removed += 1
                bytes_freed += img_info["size_bytes"]
            except docker.errors.APIError as e:
                errors.append(f"{tag}: {e}")
            except Exception as e:
                errors.append(f"{img_info['id']}: {e}")

        result = {"removed": removed, "bytes_freed": bytes_freed}
        if errors:
            result["errors"] = errors
        return result

    def prune_all_images(self) -> dict:
        """Remove all unused Docker images (not referenced by running containers).

        Returns the number of images removed and space reclaimed.
        """
        if not self.client:
            return {"error": "Docker client not available"}

        try:
            result = self.client.images.prune(filters={"dangling": False})
            deleted = result.get("ImagesDeleted") or []
            space = result.get("SpaceReclaimed", 0)
            return {
                "images_removed": len([d for d in deleted if d.get("Untagged")]),
                "layers_removed": len([d for d in deleted if d.get("Deleted")]),
                "bytes_freed": space,
            }
        except Exception as e:
            logger.error(f"Failed to prune images: {e}")
            return {"error": str(e)}

    def prune_build_cache(self) -> dict:
        """Remove Docker build cache.

        Returns the space reclaimed.
        """
        if not self.client:
            return {"error": "Docker client not available"}

        try:
            result = self.client.api.prune_builds()
            return {
                "cache_entries_removed": len(result.get("CachesDeleted") or []),
                "bytes_freed": result.get("SpaceReclaimed", 0),
            }
        except Exception as e:
            logger.error(f"Failed to prune build cache: {e}")
            return {"error": str(e)}
