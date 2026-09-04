# OCR-Lite Solo Operator Guide

OpenCyberRange Lite is a self-hosted cybersecurity training platform sized for one person running a class. The "solo operator" is a single instructor who is also the admin: one privileged account that already carries every instructor capability, so there is no separate role to set up or switch between. The guide below walks that operator front-to-back through a full term, organized as a lifecycle: before the first class, building the syllabus, running the term, and closing it out.

Everything an operator does lives in the Admin area and the instructor Ops dashboard. You will move between the two often, so keep both within reach as you work.

## Contents

1. [Before the First Class](#1-before-the-first-class)
2. [Building the Syllabus](#2-building-the-syllabus)
3. [During the Term](#3-during-the-term)
4. [End of Term](#4-end-of-term)

---

## 1. Before the First Class

Your goal before day one is a working set of student accounts and one course they can join. Do the account work first, then create the course, then hand out the invite code.

### Student accounts

You have three ways to get students into the platform, and you can mix them:

- **Create accounts yourself.** In the Admin area you can create student accounts individually or in bulk. The same screen lets you approve, unlock, and reset accounts later, so it is your control panel for the whole roster.
- **Let students self-register.** Self-registration is approval-gated by default, meaning a new sign-up sits in a pending state until you approve it. You review pending accounts in the Admin area.
- **Invite by course code.** A student can join a course directly with its invite code (covered below), which is the lightest-weight option once a course exists.

For a first class the common pattern is to create or approve accounts in advance so nobody is blocked on sign-up during your limited class time.

When you set a temporary password for a created account, avoid the exclamation mark; use `#` instead. A reasonable starter password looks like this:

```
Welcome2Range#2026
```

Ask students to change it after their first login.

### Create a course

Courses are created in the Admin area through an admin-only endpoint, so only your operator account can make them. Each course has one instructor (you), an invite code, and start and end dates. Give the course a clear name and set the dates to match your term calendar.

Lite allows up to 5 active courses at once. If you have hit that limit, archive a finished course to free a slot (see [End of Term](#4-end-of-term)).

### Share the invite code

Every course carries an invite code that students use to join. Distribute it however you normally reach your class (syllabus, LMS post, first-day slide). If the code leaks or a term rolls over, regenerate it from the course settings; the old code stops working once a new one is issued.

```
Course join code: BLUE-TEAM-7F3K
```

---

## 2. Building the Syllabus

With a course in place, you turn it into a schedule of work. In OCR-Lite that means assignments: named groups of labs with their own start and due dates.

### Assignments and weeks

Inside a course you group labs into assignments. Labs auto-group by "week," so a natural rhythm is one assignment per week that collects that week's labs. Each assignment has a start date and a due date, and an assignment can be locked so students cannot open it before you are ready.

A simple weekly layout looks like this:

- Week 1 assignment: intro labs, start Monday, due end of week
- Week 2 assignment: next labs, locked until Week 1 closes
- and so on across the term

### Assigning labs

Add labs to each assignment to define what students must complete. Set the start date so the assignment appears when you want it visible, and set the due date to drive your grading window. Lock assignments you are not ready to release, then unlock them as the term progresses.

Build out as many assignments as your syllabus needs before the term starts, or add them week by week; both work, and locked assignments let you stage the whole term in advance without exposing it early.

---

## 3. During the Term

Once class is running, your day-to-day work is watching progress, helping students who are stuck, and producing grades. All of it is available to your single operator account.

### Monitor progress

The instructor Ops dashboard is your live view of the class. It shows:

- **Flags Today**, with a 7-day sparkline so you can see the trend, not just today's count
- **Active Now**, the students currently working
- **Avg Completion** across the course

Alongside those metrics you get an activity feed and session monitoring, so you can see what students are doing in near real time and spot who has gone quiet.

### View As (impersonation)

When a student reports a problem you cannot reproduce, use "View As" to see the platform from their perspective. The view is read-only: you observe exactly what they see without changing anything on their account. Use it to confirm whether an assignment is visible, whether a lab shows as complete, or why a page looks different for them.

### Unlock and reset accounts

Students lock themselves out, forget passwords, and get stuck. From the same Admin account-management screen you used to create the roster, you can unlock a locked account or reset a password. Hand out a fresh temporary password using `#` rather than `!`, for example:

```
Reset2Range#88
```

Tell the student to change it at next login.

### Reports

You can produce two kinds of reports during the term:

- **Per-student PDF grade reports**, useful for progress check-ins and for the student's own record.
- **Per-assignment reports**, useful for seeing how the whole class handled one week's work.

Run these whenever you need a grading snapshot; they draw on the same completion data shown on the dashboard.

---

## 4. End of Term

Closing a term is two steps: capture the final grades, then archive the course.

### Final reports

Before you archive anything, generate the final per-student PDF grade reports for your records and your gradebook, and pull any per-assignment reports you want for review. Do this while the course is still active so all completion data is fully in view.

### Archive the course

When grading is done, archive the course. Archiving frees one of your 5 active-course slots so you can create next term's course without hitting the limit. Archive only after you have saved every report you need, since your goal in archiving is to close out the term cleanly and make room, not to work with the data further.

With the finished course archived, you are back to [Before the First Class](#1-before-the-first-class) for the next term: create or approve accounts, create the course, share the new invite code, and build the syllabus again.
