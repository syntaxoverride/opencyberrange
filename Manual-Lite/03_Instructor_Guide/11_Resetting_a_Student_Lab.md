# Resetting a Student Lab

Resetting a student lab clears a completion so the student can attempt the exercise again inside the course. You use it when a student finished a lab by accident, shared an answer, or needs a fresh attempt for a regrade.

## Prerequisites

- You own the course, or you are an administrator.
- The student is enrolled and the lab is assigned to the course.
- The lab is already marked **Completed** for that student. The Reset action appears only on completed labs.

## Reset one lab for one student

1. In the left sidebar, select **Instructor Panel**.
2. On the **My Courses** tab, click the course.
3. Click the **Students** sub-tab.
4. In the student's row, click **View Exercises** to expand the per-lab table.
5. On a row marked **Completed**, click **Reset**.

**What you should see:** the lab returns to **Incomplete** for that student, and the student can submit the flag again. The reset is recorded against the course.

<figure markdown>

![Students sub-tab with an expanded per-lab table showing the Reset action](img/course-students.png)

<figcaption>Expanding a student row reveals the per-lab table where the Reset action appears on completed labs.</figcaption>
</figure>

## What the reset changes

A course reset overlays a reset record on top of the student's completion rather than deleting their global completion record. Within the course, the lab reads as incomplete and the score contribution drops away. Other courses that assign the same lab are unaffected.

A reset also revokes that student's **course-wide achievements**, not only the achievement tied to the single lab. Achievements that depend on clearing a set of labs, such as clean-sweep or streak badges, are removed because the underlying completion no longer counts.

!!! warning
    Resetting a lab strips course-wide achievements for that student, not just the one lab's badge. The student re-earns them by completing the work again. Do not use reset as a quick toggle.

!!! note
    The Reset button is hidden on incomplete labs. If you do not see it, the student has not completed that lab yet.

After a reset, the scoreboard recalculates on the next load. See [10_Viewing_the_Course_Scoreboard.md](10_Viewing_the_Course_Scoreboard.md).
