"""
WireGuard configuration management
Generates client configs and manages peers via the local Peer Manager API
"""

import subprocess
import logging
import base64
import requests
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


class WireGuardManager:
    def __init__(self, api_url: str = None, api_key: str = None):
        self.api_url = api_url
        self.api_key = api_key
    
    def generate_keypair(self) -> tuple:
        """Generate WireGuard private/public keypair"""
        try:
            # Generate private key
            private_key_result = subprocess.run(
                ['wg', 'genkey'],
                capture_output=True,
                text=True
            )
            private_key = private_key_result.stdout.strip()
            
            # Generate public key from private key
            public_key_result = subprocess.run(
                ['wg', 'pubkey'],
                input=private_key,
                capture_output=True,
                text=True
            )
            public_key = public_key_result.stdout.strip()
            
            return private_key, public_key
            
        except FileNotFoundError:
            # WireGuard tools not installed, generate keys using Python
            logger.warning("WireGuard tools not found, using fallback key generation")
            return self._generate_keypair_python()
    
    def _generate_keypair_python(self) -> tuple:
        """Fallback keypair generation using Python crypto"""
        from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
        from cryptography.hazmat.primitives import serialization
        
        private_key = X25519PrivateKey.generate()
        private_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
        public_bytes = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        private_key_b64 = base64.b64encode(private_bytes).decode('utf-8')
        public_key_b64 = base64.b64encode(public_bytes).decode('utf-8')
        
        return private_key_b64, public_key_b64
    
    # wstunnel version used in auto-install PreUp hook
    WSTUNNEL_VERSION = "10.5.2"

    def generate_client_config(
        self,
        private_key: str,
        client_ip: str,
        server_public_key: str,
        server_endpoint: str,
        allowed_ips: str,
        wstunnel_url: str = None,
        platform_base_url: str = None
    ) -> str:
        """Generate WireGuard client configuration file content.

        Args:
            wstunnel_url: When set (e.g. "wss://vpn.example.com"), the config
                          embeds PreUp/PostDown hooks that automatically install
                          and run wstunnel to wrap WireGuard UDP inside a
                          WebSocket connection.  The Endpoint is overridden to
                          127.0.0.1:51820 so WireGuard talks to the local
                          wstunnel relay instead of the remote server directly.
            platform_base_url: Base URL of the platform (e.g. "https://labs.example.com").
                               Used as the primary download source for wstunnel binaries.
                               Falls back to GitHub releases if not set or unreachable.
        """
        if wstunnel_url:
            # Tunnel mode: WireGuard -> local wstunnel client -> WebSocket -> server
            ver = self.WSTUNNEL_VERSION

            # Build download URL: try platform first (self-hosted), fall back to GitHub
            if platform_base_url:
                primary_url = f"{platform_base_url}/downloads/wstunnel_{ver}_linux_${{A}}.tar.gz"
                fallback_url = f"https://github.com/erebe/wstunnel/releases/download/v{ver}/wstunnel_{ver}_linux_${{A}}.tar.gz"
                download_cmd = (
                    f"(curl -sfL {primary_url} || curl -sL {fallback_url}) "
                    f"| tar xz -C /usr/local/bin/ && chmod +x /usr/local/bin/wstunnel"
                )
            else:
                download_cmd = (
                    f"curl -sL https://github.com/erebe/wstunnel/releases/download/v{ver}/wstunnel_{ver}_linux_${{A}}.tar.gz "
                    f"| tar xz -C /usr/local/bin/ && chmod +x /usr/local/bin/wstunnel"
                )

            # PreUp: use pkill -x (exact name match) to avoid killing the PreUp
            # bash process itself. setsid detaches wstunnel from wg-quick's
            # process group so it survives after PreUp completes.
            preup = (
                f"/bin/bash -c '"
                f"nmcli connection delete ocr-vpn 2>/dev/null; "
                f"command -v wstunnel >/dev/null 2>&1 || "
                f"(ARCH=$(uname -m); "
                f"case $ARCH in x86_64) A=amd64;; aarch64) A=arm64;; *) echo \"Unsupported arch: $ARCH\" >&2; exit 1;; esac; "
                f"echo \"[+] Installing wstunnel ($A)...\" && "
                f"{download_cmd}); "
                f"pkill -x wstunnel 2>/dev/null; sleep 0.5; "
                f"echo \"[+] Starting VPN tunnel...\"; "
                f"setsid wstunnel client -L \"udp://51820:127.0.0.1:51820?timeout_sec=0\" {wstunnel_url} </dev/null >/dev/null 2>&1 & "
                f"for i in 1 2 3 4 5; do ss -ulnp 2>/dev/null | grep -q :51820 && break; sleep 1; done; "
                f"echo \"[+] VPN tunnel ready\""
                f"'"
            )
            postdown = "/bin/bash -c 'pkill -x wstunnel 2>/dev/null; true'"
            endpoint = "127.0.0.1:51820"

            # GRETAP lab mirror: creates a Layer 2 interface (lab0) bridged
            # to the exercise network so students can passively sniff traffic
            # with tcpdump -i lab0.  Rides inside the WireGuard tunnel.
            gretap_postup = (
                f"/bin/bash -c '"
                f"ip link del lab0 2>/dev/null; "
                f"ip link add lab0 type gretap remote 10.0.0.1 local {client_ip}; "
                f"ip link set lab0 up"
                f"'"
            )
            gretap_postdown = "/bin/bash -c 'ip link del lab0 2>/dev/null; true'"

            config = f"""[Interface]
PrivateKey = {private_key}
Address = {client_ip}/16
PreUp = {preup}
PostUp = {gretap_postup}
PostDown = {postdown}
PostDown = {gretap_postdown}

[Peer]
PublicKey = {server_public_key}
Endpoint = {endpoint}
AllowedIPs = {allowed_ips}
PersistentKeepalive = 25
"""
        else:
            # Direct mode: WireGuard connects straight to the server
            # GRETAP lab mirror: creates a Layer 2 interface (lab0) bridged
            # to the exercise network so students can passively sniff traffic
            # with tcpdump -i lab0.  Rides inside the WireGuard tunnel.
            gretap_postup = (
                f"/bin/bash -c '"
                f"ip link del lab0 2>/dev/null; "
                f"ip link add lab0 type gretap remote 10.0.0.1 local {client_ip}; "
                f"ip link set lab0 up"
                f"'"
            )
            gretap_postdown = "/bin/bash -c 'ip link del lab0 2>/dev/null; true'"

            config = f"""[Interface]
PrivateKey = {private_key}
Address = {client_ip}/16
PostUp = {gretap_postup}
PostDown = {gretap_postdown}

[Peer]
PublicKey = {server_public_key}
Endpoint = {server_endpoint}
AllowedIPs = {allowed_ips}
PersistentKeepalive = 25
"""
        return config
    
    # ==================== Peer Manager API Methods ====================
    
    def _api_request(self, method: str, endpoint: str, data: dict = None) -> Optional[dict]:
        """Make authenticated request to Peer Manager API"""
        if not self.api_url or not self.api_key:
            logger.debug("Peer Manager API not configured")
            return None
        
        headers = {"X-API-Key": self.api_key}
        url = f"{self.api_url}{endpoint}"
        
        try:
            # Reduced timeout to fail faster (3 seconds instead of 10)
            if method == "GET":
                resp = requests.get(url, headers=headers, timeout=3)
            elif method == "POST":
                resp = requests.post(url, headers=headers, json=data, timeout=3)
            elif method == "DELETE":
                resp = requests.delete(url, headers=headers, timeout=3)
            else:
                return None
            
            if resp.status_code in (200, 201):
                return resp.json()
            else:
                logger.warning(f"Peer Manager API request failed: {resp.status_code} - {resp.text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.debug(f"Peer Manager API timeout: {url}")
            return None
        except requests.exceptions.RequestException as e:
            logger.debug(f"Peer Manager API error: {e}")
            return None
    
    def list_peers(self) -> Optional[List[Dict]]:
        """Get all peers from Peer Manager.

        Returns list of peers on success, None on API failure.
        Callers that want graceful degradation should use: list_peers() or []
        """
        result = self._api_request("GET", "/peers")
        if result and "peers" in result:
            return result["peers"]
        return None
    
    def get_peer_info(self, public_key: str) -> Optional[Dict]:
        """Get detailed information about a specific peer, including connection status"""
        try:
            peers = self.list_peers() or []
            for peer in peers:
                if peer.get("public_key", "").strip() == public_key.strip():
                    return peer
            return None
        except Exception as e:
            logger.debug(f"Failed to get peer info: {e}")
            return None
    
    def is_peer_connected(self, public_key: str, max_handshake_age_seconds: int = 180) -> bool:
        """Check if a peer is actively connected by checking last handshake time
        
        Args:
            public_key: The peer's public key
            max_handshake_age_seconds: Maximum age of last handshake to consider "connected" (default 3 minutes)
        
        Returns:
            True if peer has recent handshake, False otherwise
        """
        peer_info = self.get_peer_info(public_key)
        if not peer_info:
            return False
        
        # Check for last handshake time in peer info
        # Peer Manager API may provide: last_handshake, last_handshake_time, or similar
        last_handshake = peer_info.get("last_handshake") or peer_info.get("last_handshake_time")
        
        if last_handshake:
            try:
                from datetime import datetime, timezone
                import time
                
                # Parse handshake time (could be timestamp or ISO string)
                if isinstance(last_handshake, (int, float)):
                    handshake_time = datetime.fromtimestamp(last_handshake, tz=timezone.utc)
                elif isinstance(last_handshake, str):
                    # Try parsing ISO format
                    handshake_time = datetime.fromisoformat(last_handshake.replace('Z', '+00:00'))
                else:
                    return False
                
                # Check if handshake is recent
                age_seconds = (datetime.now(timezone.utc) - handshake_time).total_seconds()
                return age_seconds <= max_handshake_age_seconds
            except Exception as e:
                logger.debug(f"Failed to parse handshake time: {e}")
                # If we can't parse, assume not connected for safety
                return False
        
        # If no handshake info available, we can't determine connection status
        # Return False to be conservative
        return False
    
    def add_peer(self, public_key: str, client_ip: str) -> bool:
        """Add a peer to WireGuard via Peer Manager"""
        allowed_ips = f"{client_ip}/32"
        data = {
            "public_key": public_key,
            "allowed_ips": allowed_ips
        }
        result = self._api_request("POST", "/peers", data)
        if result and result.get("status") == "ok":
            logger.info(f"Added peer {public_key[:20]}... with IP {client_ip}")
            return True
        return False
    
    def remove_peer(self, public_key: str) -> bool:
        """Remove a peer from WireGuard via Peer Manager"""
        # URL encode the public key
        import urllib.parse
        encoded_key = urllib.parse.quote(public_key, safe='')
        result = self._api_request("DELETE", f"/peers/{encoded_key}")
        if result and result.get("status") == "ok":
            logger.info(f"Removed peer {public_key[:20]}...")
            return True
        return False
    
    def peer_exists(self, public_key: str) -> bool:
        """Check if a peer already exists on WireGuard - returns False on API failure"""
        try:
            peers = self.list_peers() or []
            for peer in peers:
                if peer.get("public_key") == public_key:
                    return True
            return False
        except Exception as e:
            logger.debug(f"Failed to check peer existence: {e}")
            return False
    
    def sync_peer(self, public_key: str, client_ip: str) -> bool:
        """Ensure peer exists on WireGuard (add if missing)"""
        if self.peer_exists(public_key):
            logger.debug(f"Peer {public_key[:20]}... already exists")
            return True
        return self.add_peer(public_key, client_ip)

    @staticmethod
    def _peer_ip(peer: Dict) -> str:
        """Extract the bare host IP from a peer's allowed_ips (e.g.
        '10.0.0.10/32' -> '10.0.0.10'). Handles a list or a comma string."""
        allowed = peer.get("allowed_ips") or peer.get("allowedIps") or ""
        if isinstance(allowed, list):
            allowed = allowed[0] if allowed else ""
        first = str(allowed).split(",")[0].strip()
        return first.split("/")[0].strip()

    def reconcile_peers(self, valid: Dict[str, str], dry_run: bool = True) -> Dict:
        """Reconcile the live wg0 peer set against the authoritative DB configs.

        `valid` maps each current public_key to the client_ip it should own
        (built from wireguard_configs). Reconciliation:
          - removes peers whose public_key has no DB config (dead orphans left by
            historical key churn, deleted users, or re-registration), and
          - repairs a peer whose IP no longer matches its DB config (remove then
            re-add with the correct allowed_ips), which also clears a duplicate
            peer squatting on an IP that now belongs to someone else.
        Peers already correct are left untouched. With dry_run=True (default) it
        reports what it WOULD do and changes nothing.

        Returns a report dict: {removed, repaired, kept, missing, dry_run, error}.
        `missing` lists DB configs with no live peer (informational; callers can
        re-sync those separately). Returns error set when the peer list is
        unreachable, so a transient API failure never looks like "0 orphans".
        """
        report = {"removed": [], "repaired": [], "kept": 0,
                  "missing": [], "dry_run": dry_run, "error": None}
        peers = self.list_peers()
        if peers is None:
            report["error"] = "Peer Manager unreachable; no changes made."
            return report

        valid = {k.strip(): v for k, v in valid.items() if k}
        live_keys = set()
        for peer in peers:
            pk = str(peer.get("public_key", "")).strip()
            if not pk:
                continue
            live_keys.add(pk)
            want_ip = valid.get(pk)
            if want_ip is None:
                # No DB config owns this peer -> dead orphan.
                report["removed"].append({"public_key": pk, "ip": self._peer_ip(peer)})
                if not dry_run:
                    try:
                        self.remove_peer(pk)
                    except Exception as e:
                        logger.warning(f"reconcile: remove orphan {pk[:20]} failed: {e}")
                continue
            if self._peer_ip(peer) != want_ip:
                # Right key, wrong IP -> repair to the DB address.
                report["repaired"].append(
                    {"public_key": pk, "from": self._peer_ip(peer), "to": want_ip})
                if not dry_run:
                    try:
                        self.remove_peer(pk)
                        self.add_peer(pk, want_ip)
                    except Exception as e:
                        logger.warning(f"reconcile: repair {pk[:20]} failed: {e}")
                continue
            report["kept"] += 1

        # DB configs with no live peer (a re-sync candidate, not pruned here).
        for pk, ip in valid.items():
            if pk not in live_keys:
                report["missing"].append({"public_key": pk, "ip": ip})
        return report

