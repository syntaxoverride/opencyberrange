# System Requirements

You access the platform through a web browser and reach lab targets over a WireGuard VPN. Read this page before you register so you know what software and network access you need on your own machine.

## What you need

The platform is a browser application, so it does not install anything on your computer and does not check your operating system or browser version. The requirements below are practical guidance for a smooth experience.

| Requirement | Detail |
| --- | --- |
| Web browser | A current version of Chrome, Firefox, Edge, or Safari. JavaScript must be enabled. |
| Network to the platform | Outbound HTTPS on TCP 443 to the platform address. |
| VPN client | A WireGuard client to reach lab targets from your own machine. See [Installing WireGuard on Linux](../05_VPN_Setup_Guide/03_Installing_WireGuard_on_Linux.md), [Windows](../05_VPN_Setup_Guide/04_Installing_WireGuard_on_Windows.md), or [macOS](../05_VPN_Setup_Guide/05_Installing_WireGuard_on_macOS.md). |
| VPN network path | Outbound UDP on port 51820 to the platform, so the WireGuard tunnel can connect. |
| Account | A registered account that an admin has approved. See [Registering an Account](04_Registering_an_Account.md). |

## When you can skip the VPN

If you cannot install a WireGuard client, or your network blocks UDP 51820, use RangeBox instead. RangeBox is an in-browser desktop that already sits on the lab network, so you reach lab targets through the browser alone. See [VPN Overview](../05_VPN_Setup_Guide/01_VPN_Overview.md).

!!! note
    Whether the VPN is needed for a given lab depends on how the platform is deployed. In an internet-facing deployment you connect over WireGuard or use RangeBox; the lab page tells you the target addresses once a lab is running.

## A note on smaller screens

The sidebar narrows on smaller screens, and you collapse or expand it with the chevron button at the top of the sidebar itself. There is no separate menu icon. A laptop or desktop screen gives you the most room for lab consoles and the dashboard.

!!! tip
    If a lab page or console feels cramped, collapse the sidebar with the chevron to free up horizontal space.

If you have trouble connecting after setup, see [Troubleshooting VPN Issues](../05_VPN_Setup_Guide/08_Troubleshooting_VPN_Issues.md).
