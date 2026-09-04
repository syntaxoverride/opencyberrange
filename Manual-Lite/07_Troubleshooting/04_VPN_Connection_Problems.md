# VPN Connection Problems

Use this page when your WireGuard tunnel will not come up or shows no handshake. The platform reaches lab targets over a per-user VPN, and most failures trace to a stale config, a competing tunnel, or a lab that is not running. The checklist below isolates the cause; the full setup details live in the VPN Setup Guide.

## Prerequisites

- WireGuard installed for your operating system. See [Installing WireGuard on Linux](../05_VPN_Setup_Guide/03_Installing_WireGuard_on_Linux.md), [Windows](../05_VPN_Setup_Guide/04_Installing_WireGuard_on_Windows.md), or [macOS](../05_VPN_Setup_Guide/05_Installing_WireGuard_on_macOS.md).
- A downloaded VPN config. See [Downloading Your VPN Config](../05_VPN_Setup_Guide/02_Downloading_Your_VPN_Config.md).
- A running lab to reach. See [Launching a Lab](../02_Student_Guide/04_Launching_a_Lab.md).

## How the tunnel works

The VPN page lives at `/vpn-setup`. You download a `.conf` file and bring the tunnel up with `wg-quick`. The config carries a hook that installs and launches a WebSocket relay (wstunnel), which carries the WireGuard traffic. Your VPN status is visible on the dashboard and on the VPN page.

## Symptom, cause, and fix

| Symptom | Cause | Fix |
| --- | --- | --- |
| Tunnel comes up but no recent handshake | The relay or a firewall is blocking the path | Bring the tunnel down and up again; if it persists, re-download the config so your peer is re-registered |
| Tunnel will not start at all | Another active VPN is hijacking your routing | Disconnect any other VPN, then bring this tunnel up |
| Connected but cannot reach any target | The lab is not in the running status, so there is nothing to reach | Launch the lab and confirm it shows running, then retry. See [Cannot Reach Lab Target](05_Cannot_Reach_Lab_Target.md) |
| Worked earlier, fails after re-download | Re-registering the peer rotates keys, so an old config is stale | Use the freshly downloaded config and reconnect |
| Status shows no peer after a long gap | Your peer needs a re-sync | An administrator can re-register your peer with **Sync VPN**, which also refreshes firewall rules |

!!! tip
    Re-downloading the config and reconnecting fixes most stuck tunnels, because each download re-registers your peer and rotates the keys the relay expects.

!!! warning
    Two active VPN tunnels fight over the routing table. Disconnect every other VPN before bringing the platform tunnel up.

## Tunnel path

The diagram below shows the path your traffic takes from your machine to a lab target.

```mermaid
flowchart LR
  A[Your machine WireGuard] --> B[wstunnel WebSocket relay]
  B --> C[Platform server]
  C --> D[Lab bridge network]
  D --> E[Lab target]
```

## Related pages

- [Troubleshooting VPN Issues](../05_VPN_Setup_Guide/08_Troubleshooting_VPN_Issues.md)
- [Testing Your Connection](../05_VPN_Setup_Guide/07_Testing_Your_Connection.md)
- [Cannot Reach Lab Target](05_Cannot_Reach_Lab_Target.md)
