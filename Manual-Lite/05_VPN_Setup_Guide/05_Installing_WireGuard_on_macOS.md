# Installing WireGuard on macOS

On macOS you use the WireGuard application from the Mac App Store to import your config file and activate the tunnel. The platform does not ship a macOS setup panel; the config you download is standard WireGuard and imports without editing. Follow this page to connect from a Mac.

## Prerequisites

- Your config file `ocr-vpn.conf` downloaded. See [02_Downloading_Your_VPN_Config.md](02_Downloading_Your_VPN_Config.md).
- Permission to install applications and grant network access on your Mac.

## Steps

1. Install WireGuard from the Mac App Store, then open it.

2. Click **Import tunnel(s) from file** and select your `ocr-vpn.conf` file.

3. If macOS asks to allow the WireGuard network extension, approve it. Then select the tunnel and click **Activate**.

**What you should see.** The tunnel shows as active with the lab subnets under the allowed IPs and a **Latest handshake** time once traffic flows. Your VPN IP from the platform appears in the tunnel detail. Back on the VPN setup page, the status reads **Registered**.

The flow from download to a working tunnel looks like this.

```mermaid
flowchart LR
  D[Download ocr-vpn.conf] --> I[Import tunnel in WireGuard app]
  I --> P[Approve network extension]
  P --> A[Activate tunnel]
  A --> H[Latest handshake appears]
  H --> R[VPN setup page reads Registered]
```

## Where macOS differs from Linux

The config carries shell hooks for a port 443 fallback and a passive lab mirror. The macOS application does not run those hooks.

| Feature | Linux command line | macOS app |
| --- | --- | --- |
| Split-tunnel routing of lab subnets | Yes | Yes |
| Automatic 443 fallback on UDP-blocked networks | Yes | No |
| Passive lab mirror interface | Yes | No |

!!! warning
    On a network that blocks UDP, the macOS app does not fall back to port 443 on its own. If the handshake never completes, your network may be blocking UDP. Use [01_VPN_Overview.md](01_VPN_Overview.md) RangeBox instead.

!!! note
    macOS may prompt for the network-extension permission the first time you activate the tunnel. Without it the tunnel cannot route traffic.

## Next step

Confirm the connection works: [07_Testing_Your_Connection.md](07_Testing_Your_Connection.md). For problems, see [08_Troubleshooting_VPN_Issues.md](08_Troubleshooting_VPN_Issues.md).
