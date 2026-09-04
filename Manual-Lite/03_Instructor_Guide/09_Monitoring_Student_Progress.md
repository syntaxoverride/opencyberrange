# Monitoring Student Progress

The Students sub-tab inside a course shows your roster and, for each student, a per-lab breakdown of status, score, attempts, and hints used. You use it to see who is keeping up, who is stuck, and which exercises need attention.

## Prerequisites

- You own at least one course. Course creation is admin-only; see [02_Creating_a_Course.md](02_Creating_a_Course.md).
- Students are enrolled, either by an administrator or through your course invite code. See [04_Generating_and_Sharing_Invite_Codes.md](04_Generating_and_Sharing_Invite_Codes.md).

## Open the roster

1. In the left sidebar, select **Instructor Panel**.
2. On the **My Courses** tab, click the course you want to inspect.
3. Click the **Students** sub-tab.

**What you should see:** a table with one row per enrolled student, listing **Username**, **Email**, **Enrolled** date, and an **Actions** column. Usernames and emails show in full by default; turn on Privacy Mode, the optional sidebar toggle, to mask them to a partial value.

<figure markdown>

![Course manager Students sub-tab with the enrolled roster and invite code](img/course-students.png)

<figcaption>The Students sub-tab lists every enrolled student with per-row actions, its identifiers masked only when Privacy Mode is on.</figcaption>
</figure>

## Expand a student to read per-lab progress

1. In a student's row, click **View Exercises** to expand the row.
2. Read the nested table.

**What you should see:** a per-lab table with columns **Exercise**, **Status** (Completed or Incomplete), **Score**, **Attempts**, **Hints**, and a **Reset** action. The Reset button appears only on labs the student has already completed. To reset one, see [11_Resetting_a_Student_Lab.md](11_Resetting_a_Student_Lab.md).

## Watch live activity in the Ops Center

The course roster gives you a point-in-time view. For a running feed across all your courses, open the Ops Center.

1. In the left sidebar, select **Dashboard**.
2. Read the **Flags Today**, **Active Now**, and **Avg Completion** cards.
3. Scroll to the **Live Operations Feed** and click **Refresh** to pull the latest events.

**What you should see:** the three stat cards summarize today's activity across your active courses, and the feed lists recent events (User, Event, Target, Time). Usernames appear masked when Privacy Mode is on.

The feed refreshes when you click **Refresh** or **Load More**. It does not stream on its own, so refresh to see the latest events.

!!! note
    Ops Center stats count only your **active** courses. An archived course's students drop out of the cards and feed. See [13_Archiving_a_Course.md](13_Archiving_a_Course.md) for how archive state affects reporting.

!!! tip
    Turn on Privacy Mode, the optional sidebar toggle that is off by default, to mask identifiers in both the roster and the feed. Avoid screenshotting or sharing rosters that contain real student emails.

If a student reports a lab they cannot finish, confirm the symptom against [../07_Troubleshooting/06_Flag_Not_Accepted.md](../07_Troubleshooting/06_Flag_Not_Accepted.md) before resetting their attempt.
