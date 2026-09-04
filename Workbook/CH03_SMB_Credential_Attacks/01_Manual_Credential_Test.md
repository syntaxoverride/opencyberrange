# Exercise 3.1: Manual Credential Test

## Before You Begin

In Chapter 2, you accessed anonymous shares and enumerated usernames. Those anonymous shares had no authentication; anyone could browse them. But most real-world SMB shares require a username and password. this exercise teaches you to authenticate to SMB using credentials, starting with the most basic approach: guessing a common password for a known username.

## Scenario

FinanceCorp's anonymous shares have been assessed. James Mitchell wants to test whether any shares require weak credentials. You have a username from your enumeration work; now try common passwords manually. The target is running a Samba server with at least one share that requires authentication.

## Your Objectives

- Authenticate to a protected SMB share using discovered credentials
- Understand SMB authentication error codes and what they reveal
- Demonstrate the impact of weak credentials on a protected share
- Capture the flag

---

## Background: Understanding SMB Authentication

When you connect to a protected share, SMB uses **NTLM challenge-response authentication**. The process works like this:

1. Your client sends a session setup request with the username
2. The server sends back a random **challenge** (a nonce)
3. Your client computes a **response** by hashing the password together with the challenge
4. The server performs the same computation and compares the results

If the credentials are wrong, the server returns an **NT_STATUS** error code. These codes are intelligence; they tell you something about the account, not just that the login failed:

| Code | Meaning |
|------|---------|
| `NT_STATUS_LOGON_FAILURE` | Wrong username or password |
| `NT_STATUS_ACCOUNT_LOCKED_OUT` | Too many failed attempts; account locked |
| `NT_STATUS_ACCOUNT_DISABLED` | Account exists but is disabled |
| `NT_STATUS_PASSWORD_EXPIRED` | Account exists, password needs reset |

If the credentials are correct, you get the `smb: \>` prompt; silent success. There is no "login successful" banner. The absence of an error is the confirmation.

A note about inline passwords: the syntax `smbclient -U user%pass` places the password directly in your shell history. In a real engagement, use the interactive prompt or clear your history afterward.

## Tool Primer: SMB Authentication with smbclient

You already know `smbclient` from Chapter 2. Authentication adds the `-U` flag:

!!! kali "Authenticate to a share with smbclient"
    Three syntaxes cover the cases you need. The inline form puts the password directly in the command, the interactive form prompts for it, and the IPC$ form tests the credential pair without touching a data share.

    Inline password (password visible in command):

    ```bash
    smbclient //<target_ip>/private -U admin%password
    ```

    Interactive password (prompted, password hidden):

    ```bash
    smbclient //<target_ip>/private -U admin
    ```

    Testing credentials against IPC$:

    ```bash
    smbclient //<target_ip>/IPC$ -U admin%password -c 'exit'
    ```

    IPC$ is a special inter-process communication share that exists on every Windows and Samba server. If authentication succeeds against IPC$, the credentials are valid system-wide; regardless of which data shares you can access.

**What success looks like:**

```
Try "help" to get a list of possible commands.
smb: \>
```

**What failure looks like:**

```
session setup failed: NT_STATUS_LOGON_FAILURE
```

---

## Walkthrough

### Step 1: Launch the Exercise

Open the platform in your browser and start the exercise environment.

- Navigate to **Exercises** → **SMB Credential Attacks** → **Level 1**
- Click **Launch** on "Manual Credential Test"
- Wait for the status to change to **Running**
- Note the **target IP** displayed in the Active Lab View

### Step 2: Verify SMB Is Running

!!! kali "Confirm port 445 is open"
    Confirm that the target is listening on port 445 before attempting authentication:

    ```bash
    nmap -p 445 <target_ip>
    ```

    You should see port 445 in the **open** state. If it shows as closed or filtered, wait a moment for the lab environment to finish starting and try again.

### Step 3: Try Anonymous Access to the Private Share

!!! kali "Attempt anonymous access"
    Before using credentials, confirm that the share actually requires authentication. Attempt an anonymous connection:

    ```bash
    smbclient //<target_ip>/private -N
    ```

    The `-N` flag suppresses the password prompt, connecting with no credentials. You should see:

    ```
    tree connect failed: NT_STATUS_ACCESS_DENIED
    ```

    The `NT_STATUS_ACCESS_DENIED` error confirms that the "private" share requires authentication. Anonymous access is denied.

### Step 4: Test Credentials Against IPC$

!!! kali "Validate credentials against IPC$"
    You know the username `admin` from your enumeration work. Before trying to access the private share, validate the credentials against IPC$ first. Testing against IPC$ separates the question "are these credentials valid?" from "does this user have access to that share?"

    ```bash
    smbclient //<target_ip>/IPC$ -U admin%password -c 'exit'
    ```

    The `-c 'exit'` flag tells smbclient to connect, run the `exit` command, and disconnect immediately. If you see no error, the credentials are valid. If you see `NT_STATUS_LOGON_FAILURE`, the username or password is wrong.

### Step 5: Connect to the Private Share

!!! kali "Connect to the private share with credentials"
    Now that you have confirmed the credentials work, connect to the protected share:

    ```bash
    smbclient //<target_ip>/private -U admin%password
    ```

    You should see the `smb: \>` prompt, confirming authenticated access to the share.

### Step 6: List and Download the Flag

!!! kali "List and download the flag file"
    List the contents of the share:

    ```
    smb: \> ls
    ```

    You should see `flag.txt` in the listing. Download it:

    ```
    smb: \> get flag.txt
    ```

    Exit the session:

    ```
    smb: \> exit
    ```

### Step 7: Read the Flag

!!! kali "Read the downloaded flag"
    Read the downloaded file on your local machine:

    ```bash
    cat flag.txt
    ```

    The flag is in `OCR{<flag_here>}` format.

    Copy it and paste it into the **Submit Flag** form on the platform and click **Submit**.

---

### Record Your Findings

> **Anonymous access attempt result:**
>
> ```
> (paste the NT_STATUS error you received here)
> ```
>
> **IPC$ credential test result:**
>
> ```
> (paste the output here; success or failure)
> ```
>
> **Authenticated share listing:**
>
> ```
> (paste the output of ls from the private share)
> ```
>
> **Flag:**
>
> ```
> (paste the flag here)
> ```

---

## Analysis Questions

Take a moment to think through these questions. They reinforce the concepts behind each step you performed.

**1. You tested credentials against IPC$ before trying the private share. Why is IPC$ a good target for credential testing?**

??? note "Reveal Answer"

    IPC$ exists on every Windows and Samba server. If authentication succeeds against IPC$, you know the credentials are valid system-wide. You can then try those credentials against every other share without worrying about share-specific permissions. A failure against a data share could mean bad credentials or insufficient permissions; IPC$ eliminates that ambiguity.

**2. The error `NT_STATUS_LOGON_FAILURE` does not distinguish between a wrong username and a wrong password. Why is this a security feature?**

??? note "Reveal Answer"

    If the server told you "username correct but password wrong," an attacker could enumerate valid usernames by trying random passwords. By returning the same error for both cases, the server prevents username enumeration through the login process. The attacker has to guess both the username and the password, not just one at a time.

**3. The password for admin was "password"; literally the most common password in the world. What does this tell you about password policies at FinanceCorp?**

??? note "Reveal Answer"

    There is no effective password policy in place. No minimum length requirement would catch "password." No complexity requirement (uppercase, numbers, special characters) would catch it either. There is no check against common password lists. A trivially guessable administrator password is a critical finding for the report; the organization needs to enforce password complexity, minimum length, and ideally a blocklist of known common passwords.

---

## Key Takeaways

- `smbclient -U user%password` authenticates to SMB shares with inline credentials
- Always test credentials against IPC$ first; it exists on every system and validates the credential pair without ambiguity
- NT_STATUS error codes reveal information about the authentication attempt, including whether accounts are locked, disabled, or expired
- Weak credentials (admin/password) are the most common vulnerability in real assessments; they require no exploits and no special tools
- Testing one password at a time works, but it is slow. The next exercise scales this up by testing multiple passwords in a loop.
