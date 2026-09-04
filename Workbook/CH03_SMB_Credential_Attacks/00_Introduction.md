# Chapter 3: SMB Credential Attacks

## From Reconnaissance to Attack

Chapter 2 gave you the map: you know what shares exist, what users are on the system, and what the password policy allows. But you could not access the protected shares because they require credentials. Chapter 3 crosses the line from reconnaissance into exploitation. You will test passwords against the SMB service, starting with a single manual guess and building up to a fully automated attack chain that discovers valid credentials across multiple user accounts.

Skipping the manual steps and jumping straight to automated tools is tempting, but it leaves you without the intuition to troubleshoot when tools break or behave unexpectedly. You will start with a single manual login attempt so you understand exactly what happens during SMB authentication; what a success looks like, what a failure looks like, and what the status codes mean. From there, you will build up to scripted testing, then fully automated brute force, and finally a complete pipeline that combines enumeration and credential attacks into one workflow.

## What You Will Learn

The five labs in this chapter take you from a single manual login attempt to a fully automated credential attack pipeline. Each lab adds a layer of automation and scope, mirroring the way a real penetration tester escalates their approach when initial manual attempts reveal that more thorough testing is needed.

By the end of this chapter, you will be able to:

- Authenticate to SMB shares using discovered credentials
- Interpret SMB authentication success and failure messages (NT_STATUS codes)
- Write bash scripts to test multiple password combinations
- Use CrackMapExec to automate brute force attacks against SMB
- Combine user enumeration (from Chapter 2) with credential attacks into a complete attack chain
- Execute a full SMB credential attack from enumeration to authenticated access

## What Is a Credential Attack?

Authentication requires two pieces of information: a username and a password. Chapter 2 gave you the first piece through user enumeration; you already have a list of valid usernames on the target system. A credential attack systematically tests passwords against those usernames to find the second piece. The methods range from manual guessing (trying "password" and "admin") to automated brute force (testing thousands of combinations per minute). In a penetration test, credential attacks are often the fastest path from "I know this service exists" to "I have access to this service."

Where do password guesses come from? There are several common sources:

- **Default credentials**: admin/admin, admin/password, guest with no password
- **Keyboard patterns**: qwerty, 123456, password1
- **Company-specific patterns**: CompanyName2024, Summer2025, Welcome1
- **Leaked password databases**: rockyou.txt, which contains millions of real passwords from data breaches

The strength of your wordlist determines the success of your attack. A well-targeted list of 100 likely passwords will often outperform a generic list of 10,000 random strings, because most users choose predictable passwords that follow common patterns.

One important technical note: these exercises use **SMBv2/v3**, the modern protocol. The classic tool Hydra; which you may have seen in other tutorials; only supports SMBv1, and SMBv1 is disabled on these targets. You will use **CrackMapExec** instead, which handles modern SMB authentication natively. The setup mirrors real-world conditions where SMBv1 is increasingly disabled for security reasons, and it ensures the skills you learn here transfer directly to current engagements.

## How SMB Authentication Works

When you connect to an SMB share without credentials, the server may allow anonymous access to some shares but block access to others. To reach the protected shares, you need to supply a valid username and password.

When you attempt authentication, the server responds with an **NT_STATUS** code that tells you exactly what happened. Understanding these codes is critical for interpreting your results:

| NT_STATUS Code | Meaning |
|----------------|---------|
| NT_STATUS_OK | Authentication succeeded; valid credentials |
| NT_STATUS_LOGON_FAILURE | Wrong username or wrong password |
| NT_STATUS_ACCOUNT_LOCKED_OUT | Too many failed attempts; account is locked |
| NT_STATUS_ACCOUNT_DISABLED | Valid credentials, but the account is disabled |
| NT_STATUS_PASSWORD_MUST_CHANGE | Valid credentials, but a password reset is required |

A successful login returns `NT_STATUS_OK` and grants you access to the share. Every other code tells you something useful; even failures reveal information. For example, `NT_STATUS_ACCOUNT_LOCKED_OUT` confirms the account exists, and `NT_STATUS_PASSWORD_MUST_CHANGE` tells you the credentials are valid even though you cannot log in yet. Learning to read these codes turns every failed attempt into useful intelligence.

You will encounter these status codes throughout every lab in this chapter. By the end, parsing them will be second nature.

## The Credential Attack Spectrum

The five labs in this chapter follow a deliberate progression from simple to complex. Each lab introduces one new capability, and each builds on the skills from the previous exercise:

```mermaid
graph LR
    A["3.1 Manual Test"] --> B["3.2 Scripted Testing"]
    B --> C["3.3 Automated Brute Force"]
    C --> D["3.4 Enum + Brute Force"]
    D --> E["3.5 Full Attack Chain"]

    style A fill:#4a90d9,color:#fff
    style E fill:#6aaa64,color:#fff
```

| Exercise | Command | What It Adds |
|-----|---------|-------------|
| 3.1 | `smbclient -U admin%password //<target>/share` | Manual authentication with inline credentials |
| 3.2 | `for pass in ...; do smbclient ...; done` | Bash loop testing multiple passwords |
| 3.3 | `crackmapexec smb <target> -u admin -p wordlist.txt` | Automated single-user brute force |
| 3.4 | `crackmapexec smb <target> -u users.txt -p wordlist.txt` | Enumeration + multi-user brute force |
| 3.5 | Full pipeline: enum4linux -> extract users -> CrackMapExec -> access shares | Complete attack chain from recon to exploitation |

Notice how the progression moves left to right: from a single command with hardcoded values, to loops, to dedicated tools, and finally to a pipeline that chains everything together. Do not worry about memorizing every flag and option right now. Each lab walkthrough explains the specific command you will use before you run it.

## Before You Start

Chapter 3 builds directly on the skills and output from Chapter 2. Make sure the following are in place before beginning Exercise 3.1:

- [ ] You have completed Chapter 2 (SMB Reconnaissance)
- [ ] You know how to list shares with `smbclient -L`
- [ ] You know how to enumerate users with `rpcclient` or `enum4linux`
- [ ] You understand the target's password policy (discovered in Chapter 2)
- [ ] Your VPN is connected and your terminal is open
- [ ] You have a Kali Linux terminal with CrackMapExec installed (pre-installed on most Kali builds)
- [ ] You have verified connectivity to the target by pinging it or running a quick Nmap scan

If any of the Chapter 2 concepts feel unclear, review those labs before proceeding. The techniques in this chapter assume you are comfortable with share enumeration and user discovery.
