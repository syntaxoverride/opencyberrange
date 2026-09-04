# Exercise 2.7: User Enumeration via Null Session

## Before You Begin

Exercise 2.6 showed that null sessions can enumerate shares. this exercise reveals what many consider the most dangerous null session capability: **user enumeration**. A list of valid usernames is half of every credential attack; and null sessions hand it over for free.

## Scenario

FinanceCorp's null session enumeration has already revealed significant information disclosure. James Mitchell is particularly concerned about user enumeration, as this can aid credential attacks and social engineering. Your task is to use the null session to enumerate all user accounts on the target, understand what each account's RID tells you, and capture the flag.

## Your Objectives

- Enumerate all user accounts on the target through a null session using rpcclient
- Understand RID significance and what it reveals about each account
- Identify the built-in Administrator account by its RID
- Capture the flag

---

## Background: Why User Enumeration Is the Most Dangerous Null Session Capability

Every credential attack needs two things: a **username** and a **password**. When a null session exposes the full list of valid usernames, it eliminates half the guesswork. An attacker no longer needs to guess *who* exists; only *what their password is*.

Windows assigns each account a **Relative Identifier (RID)**, a numeric value appended to the domain's Security Identifier (SID). Certain RIDs are fixed and always mean the same thing:

| RID (Decimal) | RID (Hex) | Account |
|---------------|-----------|---------|
| 500 | 0x1f4 | Built-in Administrator (always exists, cannot be deleted) |
| 501 | 0x1f5 | Guest account |
| 1000+ | 0x3e8+ | Regular user accounts created by administrators |

Low RIDs indicate built-in or privileged accounts. The built-in Administrator (RID 500) is a high-value target in every penetration test because it always exists and typically holds the highest privileges on the system. Even if an administrator renames this account, its RID remains 500.

User enumeration feeds directly into Chapter 3 (credential attacks). this exercise is the bridge between reconnaissance and exploitation; the user list you gather here becomes the input for brute force and password spraying attacks later.

**Converting hex RIDs to decimal:** The output from rpcclient displays RIDs in hexadecimal. To convert, use standard hex-to-decimal conversion. For example, `0x1f4` = (1 x 256) + (15 x 16) + 4 = 500. The most important ones to recognize on sight are 0x1f4 (500) and 0x1f5 (501).

## Tool Primer: rpcclient User Enumeration Commands

You used rpcclient in Exercise 2.5 to establish a null session. this exercise introduces new commands for user and group enumeration:

| Command | What It Returns |
|---------|----------------|
| `enumdomusers` | List all domain/local users with their RIDs |
| `queryuser <RID>` | Detailed info about a specific user (description, last logon, etc.) |
| `enumdomgroups` | List all groups on the domain/machine |
| `lookupnames <username>` | Look up a specific username and return its SID/RID |

The output format for `enumdomusers` looks like this:

```
user:[admin] rid:[0x3e8]
user:[user1] rid:[0x3e9]
user:[guest] rid:[0x1f5]
```

Each line gives you the account name in brackets and its RID in hexadecimal. In this exercise, you should expect to find three accounts: admin, user1, and guest.

Note that `queryuser` takes the RID as its argument, not the username. To query the built-in Administrator, you would pass `0x1f4`: the hex form of RID 500.

---

## Walkthrough

### Step 1: Launch the Exercise

Open the platform in your browser and start the exercise environment. The target has SMB running on port 445 with null sessions enabled.

- Navigate to the appropriate learning path and locate Exercise 2.7
- Click **Launch** and wait for the status to change to **Running**
- Note the **target IP** displayed in the Active Lab View

### Step 2: Establish a Null Session

!!! kali "Establish a null session with rpcclient"
    Connect to the target using rpcclient with empty credentials:

    ```bash
    rpcclient -U "" -N <target_ip>
    ```

    The `-U ""` flag specifies an empty username, and `-N` suppresses the password prompt. You should see the `rpcclient $>` prompt, confirming the null session is established.

### Step 3: Enumerate Users

!!! kali "Enumerate domain users"
    At the rpcclient prompt, list all user accounts:

    ```bash
    rpcclient $> enumdomusers
    ```

    You should see output listing each user account with its RID in the format `user:[username] rid:[0xHEX]`. Note every username and its corresponding RID; you will need these for the Record Your Findings section below.

    Pay close attention to the hex values and which RID ranges they fall into. Any account with a RID below 1000 (0x3e8) is a built-in account. Accounts at 1000 and above were created by an administrator after initial setup.

### Step 4: Query a Specific User

!!! kali "Query the built-in Administrator account"
    Use the RID to pull detailed information about the built-in Administrator account:

    ```bash
    rpcclient $> queryuser 0x1f4
    ```

    The `queryuser` command returns extended details including the account description, last logon time, and account flags. Review the output and note the description field and when the account last logged in. Such detail can reveal whether an account is actively used, which informs your attack prioritization in later chapters.

### Step 5: Enumerate Groups

!!! kali "Enumerate domain groups"
    List all groups on the target:

    ```bash
    rpcclient $> enumdomgroups
    ```

    Group names reveal how the system is organized and which groups might grant elevated privileges. Note any groups that suggest administrative access. Common groups to look for include Domain Admins, Administrators, and Remote Desktop Users.

### Step 6: Exit rpcclient

!!! kali "Close the null session"
    Close the null session cleanly:

    ```bash
    rpcclient $> exit
    ```

    You are now back at your regular shell prompt.

### Step 7: Find the Flag

!!! kali "List shares and read the server string"
    Use smbclient to list available shares and look for the flag in the server string:

    ```bash
    smbclient -L //<target_ip> -N
    ```

    The server string in the output contains the flag. Look for the line that reads "DC01 - Users Enumerable"; the flag in `OCR{...}` format appears in this server description string. Copy the flag and submit it on the platform.

---

### Record Your Findings

> **My enumdomusers output:**
>
> ```
> (paste your output here)
> ```
>
> **Users discovered:**
>
> | Username | RID (Hex) | RID (Decimal) | Account Type |
> |----------|-----------|---------------|--------------|
> |          |           |               |              |
> |          |           |               |              |
> |          |           |               |              |
>
> **My queryuser output for RID 0x1f4:**
>
> ```
> (paste your output here)
> ```
>
> **How to submit:** enter the flag on the exercise page exactly as you recovered it, keeping the `OCR{...}` wrapper.
>
> **Flag:** `___________________________`

---

## Analysis Questions

Think through each question before reading the provided answer.

**1. You discovered a user with RID 500. Why is this account significant in a penetration test?**

??? note "Reveal Answer"

    RID 500 is the built-in Administrator account. It cannot be deleted, is often targeted first in credential attacks, and typically holds the highest privileges on the system. Even if an administrator renames it, the RID remains 500; making it always identifiable through enumeration.

**2. How does the user list you just discovered directly enable the attacks in Chapter 3?**

??? note "Reveal Answer"

    Chapter 3 focuses on credential attacks such as brute force and password spraying. Having a confirmed list of valid usernames eliminates half the guesswork. Instead of guessing both usernames and passwords, you only need to guess passwords. Narrowing the search to passwords alone dramatically increases the success rate of credential attacks and reduces the number of failed attempts, which in turn lowers the risk of detection.

**3. An administrator renamed the Administrator account to "sysadmin" for security. Does this protect against the technique you just used?**

??? note "Reveal Answer"

    No. The `enumdomusers` command returns the account regardless of its display name, and the RID remains 500. RID-based enumeration bypasses name-based obscurity entirely. An attacker who sees RID 0x1f4 knows immediately that this is the built-in Administrator, no matter what it has been renamed to.

---

## Key Takeaways

- `enumdomusers` lists all user accounts accessible through null sessions, providing both usernames and RIDs
- RIDs identify account types: 500 is always the built-in Administrator, 501 is Guest, and 1000+ are regular user accounts created by administrators
- User enumeration is the most dangerous null session capability because it directly enables credential attacks by providing half of every username-password pair
- Renaming accounts does not change their RIDs; RID 500 is always the built-in Administrator, regardless of its display name
- You have now enumerated shares, server info, and users individually. The final lab in this chapter combines everything into a single automated enumeration pass.
