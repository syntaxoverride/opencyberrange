# Chapter 3: Review

## What You Learned

Over five labs, you progressed from manually testing a single password to executing a complete multi-user credential attack chain. You learned to authenticate to SMB with smbclient, write bash loops for automated testing, use CrackMapExec for professional-grade brute forcing, combine enumeration with exploitation, and execute the full seven-phase SMB attack workflow. Along the way, you discovered why CrackMapExec is preferred over Hydra for modern SMB environments.

## The Progression You Followed

Each lab added one new layer to your credential attack capability:

```mermaid
graph LR
    A["3.1 Manual Test"] --> B["3.2 Bash Loops"]
    B --> C["3.3 CrackMapExec"]
    C --> D["3.4 Enum + Brute"]
    D --> E["3.5 Full Attack"]

    style A fill:#4a90d9,color:#fff
    style E fill:#6aaa64,color:#fff
```

| Exercise | What You Added | Why It Matters |
|-----|---------------|----------------|
| 3.1 | Manual credential test | Learned SMB authentication syntax and NT_STATUS codes |
| 3.2 | Bash loop testing | Automated testing multiple passwords against one user |
| 3.3 | CrackMapExec brute force | Professional tool with SMBv2/v3 support |
| 3.4 | Enumeration + brute force | Two-phase attack chain; discover users, then attack |
| 3.5 | Full credential attack | Complete seven-phase workflow from recon to exploitation |

## Self-Assessment

Answer the following questions without looking back at the walkthroughs. If you get stuck, that topic is worth revisiting.

**1.** What smbclient flag provides the password inline with the username?

> &nbsp;
>
> &nbsp;

**2.** What does `NT_STATUS_LOGON_FAILURE` tell you, and what does it NOT tell you?

> &nbsp;
>
> &nbsp;

**3.** What is the difference between password spraying and brute forcing?

> &nbsp;
>
> &nbsp;

**4.** Why is CrackMapExec preferred over Hydra for modern SMB targets?

> &nbsp;
>
> &nbsp;

**5.** What does the `--continue-on-success` flag do in CrackMapExec?

> &nbsp;
>
> &nbsp;

**6.** Why should you enumerate usernames before attempting credential attacks?

> &nbsp;
>
> &nbsp;

**7.** List the seven phases of the complete SMB attack chain.

> &nbsp;
>
> &nbsp;

## Command Cheat Sheet

Keep the following reference handy throughout the rest of the workbook. These commands cover every technique from the chapter.

| Command | What It Does |
|---------|-------------|
| `smbclient //<target>/share -U user%pass` | Authenticate to SMB share with inline credentials |
| `smbclient //<target>/IPC$ -U user%pass -c 'exit'` | Test credentials against IPC$ (credential validation) |
| `for pass in ...; do smbclient ...; done` | Bash loop for multi-password testing |
| `while read pass; do ...; done < passwords.txt` | Test passwords from a file |
| `crackmapexec smb <target> -u user -p wordlist.txt` | Brute force single user with CrackMapExec |
| `crackmapexec smb <target> -u users.txt -p wordlist.txt` | Brute force multiple users |
| `crackmapexec smb <target> -u user -p pass --shares` | List accessible shares after authentication |
| `crackmapexec smb <target> ... --continue-on-success` | Keep testing after finding valid credentials |
| `rpcclient -U "" -N <target> -c 'enumdomusers' \| grep -oP 'user:\[\K[^\]]+' > users.txt` | Extract usernames to a file |

## Connect the Dots: What Comes Next

You can now discover credentials for SMB; the Windows file-sharing protocol. But SMB is just one service on a Windows machine. Your Nmap scans from Chapter 1 also found RDP (port 3389). Chapter 4 applies the same reconnaissance and credential-testing methodology to Remote Desktop Protocol. The tools change; you will use `xfreerdp` instead of `smbclient`: but the workflow remains the same: discover the service, enumerate what you can, and test credentials to gain access.

---

## Self-Assessment Answer Key

**1.** The `%` separator: `-U user%password` passes the password inline. Example: `smbclient //target/share -U admin%password`.

**2.** It tells you the credentials are invalid. It does NOT tell you whether the username or the password (or both) are wrong; this is intentional to prevent username enumeration through the login process.

**3.** Password spraying tests one password against many users (safer, avoids lockout). Brute forcing tests many passwords against one user (faster for single targets, higher lockout risk).

**4.** Hydra's SMB module only supports SMBv1, which is disabled on modern systems. CrackMapExec supports SMBv2/v3 natively and provides additional post-authentication capabilities.

**5.** By default, CrackMapExec stops after finding the first valid credential pair. `--continue-on-success` keeps testing all remaining combinations, which is essential when multiple users may have weak passwords.

**6.** Enumeration eliminates guesswork. Testing known usernames with a password list is far more efficient than guessing both. It also ensures you do not miss accounts like service accounts (svc_*) that may have elevated privileges.

**7.** (1) Service discovery, (2) Share enumeration, (3) Anonymous access testing, (4) Null session enumeration, (5) Username extraction, (6) Credential attack, (7) Authenticated access and data retrieval.
