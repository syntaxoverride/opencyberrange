# Monitoring Active Sessions

The Sessions view shows every running lab session on the platform in real time, with its student, exercise, time remaining, VPN connectivity, RangeBox status, and container health. You use it to confirm that a student's lab is healthy, to spot stale or expiring sessions, and to reach the per-session actions for support.

## Prerequisites

- An [admin account](../01_Getting_Started/05_Logging_In.md) signed in to the Admin Panel.

## Steps

1. In the left sidebar, click **Monitoring**. The panel opens at `/admin?tab=monitoring` with the **Sessions** sub-tab selected by default.
2. Read the **Active Sessions** count in the panel header. Each running session renders as a card.
3. Inspect a session card. It shows the student, the exercise name, the time remaining, a **VPN** badge (Connected, Disconnected, Not Registered, or No Config), the container list, and CPU and RAM usage.
4. Click **Refresh** in the header to pull the latest health snapshot at any time.
5. Use the **Recent History** table at the bottom to review past sessions. Filter it with the time-range pills (1h, 6h, 24h, 7d, All, or Custom).

**What you should see:** One card per running session with live status badges, plus a history table of recent sessions below.

<figure markdown>

![Monitoring Sessions sub-tab showing session health cards](img/admin-monitoring-sessions.png)

<figcaption>The Sessions sub-tab lists each running session with VPN, container, and resource status, plus a recent-history table.</figcaption>
</figure>

Per-session cards expose these actions:

| Action | What it does |
| --- | --- |
| Logs | Opens the container logs for that session. |
| Impersonate | Connects your RangeBox to the student's lab network (a session bridge, not a read-only preview). |
| Reset Stale | Marks a stale session as stopped so the student can start a new lab. Shown only when the session is stale. |
| Re-sync VPN | Re-registers the student's VPN peer. Shown only when the VPN has a config but is not connected. |
| Force Stop | Tears down the session's containers and stops it. |

!!! note "Stale sessions are flagged"
    A session whose database row says running but has no containers is marked stale with a warning. Clear it with **Reset Stale**, covered in [Terminating Sessions](14_Terminating_Sessions.md).

!!! note "Diagnostic sessions are tagged"
    Sessions the Exercise Tester spins up to validate a lab carry a **Diagnostics** tag and are excluded from student-facing statistics.

!!! tip "Privacy mode masks names"
    With privacy mode on, the User column shows masked names so you can monitor safely even when real students are active.

The Sessions, VPN Peers, and Activity Log views are sub-tabs of Monitoring. An old `?tab=sessions` link still resolves to this view. For VPN, see [Managing VPN Peers](16_Managing_VPN_Peers.md).
