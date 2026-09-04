# Managing VPN Peers

The VPN Peers view shows every WireGuard peer the platform knows about, which users are registered, which are not, and the health of each peer's configuration. You use it to register a user who has no peer, repair a broken or duplicate peer, and remove peers that no longer belong.

## Prerequisites

- An [admin account](../01_Getting_Started/05_Logging_In.md) signed in to the Admin Panel.

## Steps

1. In the left sidebar, click **Monitoring** to open `/admin?tab=monitoring`.
2. Click the **VPN Peers** sub-tab. The **VPN Peer Management** panel loads.
3. Read the two stat cards: **Registered on VPN Server** and **Not Registered**.
4. Register a missing peer: in the **Unregistered Users** list, click **Register** next to a user. The platform registers that user's peer.
5. Inspect the **Active VPN Peers** table. Each row shows the user, the assigned IP, a health badge, the last handshake, and transfer totals.
6. Act on a peer row using its **Repair** or **Remove** action.

**What you should see:** The registered count rises after a Register, and the peer's row appears in the Active VPN Peers table with a health badge.

<figure markdown>

![VPN Peers sub-tab showing the peer table with health badges](img/admin-vpn-peers.png)

<figcaption>The VPN Peers sub-tab lists registered and unregistered users plus an Active VPN Peers table with health badges and actions.</figcaption>
</figure>

The health badge tells you what is wrong with a peer:

| Badge | Meaning | Action |
| --- | --- | --- |
| OK | Peer is configured correctly | None |
| No allowed_ips | Peer has no routed address | Repair |
| Duplicate | More than one peer claims the same IP | Repair |
| Orphan | Peer exists on the server with no database record | Remove |

!!! note "Repair removes conflicts and re-registers"
    Clicking **Repair** removes the conflicting peers for that user and re-registers a clean peer from the database record.

!!! warning "The Labs Server peer is special"
    The row tagged **Labs Server** is the platform's own peer. It carries no Repair or Remove action and must stay in place.

!!! note "Duplicate IPs come from the address allocator"
    A Duplicate badge means two peers were assigned the same address. Repair clears the conflict and re-registers the affected user from the database.

The VPN Peers view is a sub-tab of Monitoring; an old `?tab=vpn` link still resolves here. To reconcile the whole peer set at once, see [Syncing VPN Configurations](17_Syncing_VPN_Configurations.md). For student-side connection problems, see [VPN Connection Problems](../07_Troubleshooting/04_VPN_Connection_Problems.md).
