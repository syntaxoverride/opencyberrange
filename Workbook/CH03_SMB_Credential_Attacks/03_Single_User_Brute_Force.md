# Exercise 3.3: Single User Brute Force

## Before You Begin

Your bash loop from Exercise 3.2 tested 8 passwords in about 10 seconds. Imagine testing 1,000. Or 14 million (the size of rockyou.txt). Bash loops do not scale. this exercise introduces **CrackMapExec**: the standard tool for SMB credential attacks. It is faster, produces cleaner output, and; critically; supports SMBv2 and SMBv3, which Hydra does not.

## Scenario

James Mitchell reviewed your bash loop results from Exercise 3.2 and wants to see professional-grade tooling. The target still has an SMB share called "private" that requires authentication, and you still suspect the username is `admin`. For this round, instead of a hand-rolled bash script, you will use CrackMapExec; a purpose-built tool for network credential testing that handles modern SMB natively.

## Your Objectives

- Use CrackMapExec to perform an automated SMB brute force attack against a single user
- Understand why Hydra does not work on modern SMB targets
- Discover valid credentials for the "private" share
- Capture the flag

---

## Background: Automated Brute Force Attacks

A brute force attack systematically tests every password in a list against a target. Unlike the manual and semi-automated approaches in Exercises 3.1 and 3.2, a proper brute force attack relies on a dedicated tool to handle the volume.

Whether a brute force attack succeeds depends on three factors:

- **Wordlist quality**: the password must be in your list, or you will never find it
- **Target password policy**: complexity requirements reduce the chance that simple passwords work
- **Account lockout settings**: many systems lock an account after a set number of failed attempts, killing your attack entirely

**Why dedicated tools over bash scripts:**

Your bash loop from Exercise 3.2 worked, but it had real limitations. It spawned a new `smbclient` process for every attempt, had no connection reuse, no retry handling, and crude output parsing. Dedicated tools solve all of this with connection pooling, protocol-aware retry logic, clean output formatting, and multi-protocol support.

**Hydra vs CrackMapExec; a critical distinction:**

Hydra is the classic brute force tool that appears in most tutorials. However, its SMB module only supports SMBv1. SMBv1 has been deprecated by Microsoft and is disabled on these lab targets (and increasingly in production environments) for security reasons. CrackMapExec (CME) supports SMBv2 and SMBv3 natively; it is the modern replacement for SMB credential testing.

| Feature | Hydra | CrackMapExec |
|---------|-------|--------------|
| SMBv1 | Yes | Yes |
| SMBv2/v3 | No | Yes |
| Output format | Basic | Color-coded, clear |
| Post-auth actions | No | Yes (shares, dump hashes) |
| Multi-target | Yes | Yes |

If you only remember one thing from this table: **Hydra cannot authenticate to SMBv2/v3 targets.** If your target has disabled SMBv1, Hydra will fail silently or throw protocol errors. CrackMapExec will not.

---

## Tool Primer: `crackmapexec`

CrackMapExec (often shortened to CME) is a post-exploitation and credential-testing framework. You give it a protocol, a target, and credentials to try. It handles the rest.

**Basic syntax:**

```bash
crackmapexec smb <target_ip> -u admin -p wordlist.txt
```

**Flags:**

| Flag | Purpose |
|------|---------|
| `smb` | Protocol to attack |
| `-u` | Single username (or `-u users.txt` for a file) |
| `-p` | Single password (or `-p wordlist.txt` for a file) |
| `--continue-on-success` | Keep testing after finding valid creds |
| `--shares` | List accessible shares after successful auth |

**Reading the output:**

CrackMapExec prefixes every attempt with a status indicator:

- `[-]`: failed attempt. The credentials were rejected.
- `[+]`: valid credentials found. Authentication succeeded.

**Sample output:**

```
SMB  <target>  445  WIN-DC01  [-] WORKGROUP\admin:password
SMB  <target>  445  WIN-DC01  [-] WORKGROUP\admin:admin123
SMB  <target>  445  WIN-DC01  [+] WORKGROUP\admin:qwerty
```

The `[+]` line tells you the exact username and password combination that worked. By default, CrackMapExec stops after the first successful authentication.

---

## Walkthrough

### Step 1: Launch the Exercise

Open the platform in your browser and start the exercise environment.

- Navigate to **Exercises** → **Windows** → **Level 3**
- Click **Launch** on "Single User Brute Force"
- Wait for the status to change to **Running**
- Note the **target IP** displayed in the Active Lab View

### Step 2: Create a Wordlist

You need a wordlist file containing the passwords to test. Create one with common passwords.

!!! kali "Create a small password wordlist"
    The heredoc writes nine common passwords to `wordlist.txt`, one per line, on your Kali machine.

    ```bash
    cat > wordlist.txt << 'EOF'
    password
    admin
    admin123
    qwerty
    123456
    Password123
    password123
    letmein
    welcome
    EOF
    ```

    The heredoc creates a small, targeted list. In real engagements, wordlists can contain millions of entries. The goal here is to understand the tool before scaling up.

### Step 3: Run CrackMapExec

Launch the brute force attack against the target.

!!! kali "Brute force the admin user with CrackMapExec"
    Replace `<target_ip>` with the IP shown in the Active Lab View. CrackMapExec will iterate through every password in your wordlist, attempting to authenticate as `admin` against the SMB service on port 445.

    ```bash
    crackmapexec smb <target_ip> -u admin -p wordlist.txt
    ```

    Watch the output as it runs; you will see `[-]` lines for each failed attempt.

### Step 4: Read the Output

Look for the `[+]` line in the output. It should show:

```
SMB  <target_ip>  445  FINANCECORP  [+] WORKGROUP\admin:qwerty
```

The password `qwerty` is a keyboard pattern; the six letters on the top-left row of a standard keyboard. It is consistently one of the most commonly used passwords worldwide.

### Step 5: Verify the Credentials

Now use the discovered credentials to access the "private" share.

!!! kali "Authenticate to the private share with smbclient"
    The `-U admin%qwerty` syntax supplies the username and password inline so smbclient does not prompt for them.

    ```bash
    smbclient //<target_ip>/private -U admin%qwerty
    ```

    You should see the `smb: \>` prompt, confirming that the credentials are valid and the share is accessible.

### Step 6: Download the Flag

From inside the SMB session, download the flag file.

!!! kali "Download the flag from the SMB session"
    Run these at the `smb: \>` prompt. The `get` command copies `flag.txt` from the share to your current Kali directory, then `exit` closes the session.

    ```
    smb: \> get flag.txt
    smb: \> exit
    ```

### Step 7: Read the Flag

Back at your normal terminal prompt, read the file.

!!! kali "Read the downloaded flag"
    The downloaded `flag.txt` now sits in your Kali working directory.

    ```bash
    cat flag.txt
    ```

    You should see the flag in `OCR{<flag_here>}` format.

Paste this into the **Submit Flag** form on the platform and click **Submit**.

### Step 8 (Optional): See Why Hydra Fails

To understand the Hydra limitation firsthand, try running the same attack with Hydra.

!!! kali "Attempt the same brute force with Hydra"
    The same username and wordlist go to Hydra's SMB module so you can compare the result against CrackMapExec.

    ```bash
    hydra -l admin -P wordlist.txt smb://<target_ip>
    ```

    Observe the output. Hydra will either throw protocol negotiation errors or fail to authenticate entirely. The failure happens because the target has SMBv1 disabled, and Hydra's SMB module cannot negotiate SMBv2 or SMBv3. The result is not a configuration problem on your end; it is a fundamental limitation of the tool.

---

### Record Your Findings

> **CrackMapExec full output:**
>
> ```
> (paste your output here)
> ```
>
> **Discovered credentials:**
>
> | Username | Password |
> |----------|----------|
> |          |          |
>
> **Hydra comparison (if attempted):**
>
> ```
> (paste Hydra output here, if applicable)
> ```
>
> **How to submit:** enter the flag on the exercise page exactly as you recovered it, keeping the `OCR{...}` wrapper.
>
> **Flag:** `__________________________`

---

## Analysis Questions

**1. CrackMapExec found the password in about 2 seconds. Your bash loop from Exercise 3.2 took approximately 10 seconds for a similar list. What makes CrackMapExec faster?**

??? note "Reveal Answer"

    CrackMapExec reuses SMB connections, handles protocol negotiation efficiently, and is written in compiled code with optimized network I/O. Bash loops spawn a new `smbclient` process for each attempt, which means full process creation, TCP connection setup, SMB negotiation, authentication, and teardown for every single password. CME eliminates most of that overhead.

**2. The password was "qwerty"; a keyboard pattern. What category of passwords should you always include in a custom wordlist?**

??? note "Reveal Answer"

    Keyboard patterns (qwerty, 123456, zxcvbn), default credentials (admin/admin, admin/password), seasonal patterns (Summer2024, Winter2024), and company-specific patterns (FinanceCorp2024, Finance123). A good custom wordlist combines all of these categories rather than relying on generic lists alone.

**3. If FinanceCorp had disabled SMBv1 (which they have), and you only knew about Hydra, how would you approach SMB credential testing?**

??? note "Reveal Answer"

    You would need to find an alternative tool. CrackMapExec is the standard answer for modern SMB. Other options include Metasploit's `smb_login` module, custom Python scripts using impacket's SMBConnection library, or Medusa. The broader lesson: always verify your tool supports the target's protocol version before investing time in an attack that will never succeed.

---

## Key Takeaways

- **CrackMapExec** is the standard tool for SMB credential testing on modern systems
- Hydra's SMB module only supports SMBv1; it will fail on SMBv2/v3 targets
- `[+]` in CrackMapExec output means valid credentials were found; `[-]` means failure
- Password `qwerty` is a keyboard pattern; one of the most common password categories
- You brute-forced one user. But what if you do not know the username? The next exercise combines user enumeration from Chapter 2 with the brute force techniques from this exercise.
