# Chapter 1: Review

## What You Learned

Over five labs, you built a complete enumeration toolkit; starting from a single command that checks common ports and ending with a unified scan that combines port discovery, version detection, OS fingerprinting, and automated vulnerability scripts into one pass. Every future chapter in this workbook starts with an Nmap scan, so the skills from Chapter 1 are not just foundational; they are something you will use every single time you sit down to work on a lab.

## The Progression You Followed

Each lab added one new layer to your scanning capability:

```mermaid
graph LR
    A["1.1 Basic Scan"] --> B["1.2 Full Range"]
    B --> C["1.3 Version Detection"]
    C --> D["1.4 OS Detection"]
    D --> E["1.5 Aggressive Scan"]

    style A fill:#4a90d9,color:#fff
    style E fill:#6aaa64,color:#fff
```

| Exercise | What You Added | Why It Matters |
|-----|---------------|----------------|
| 1.1 | Basic port scan | Discovered which ports are open; the starting point for everything |
| 1.2 | Full-range scan | Found services hiding on non-standard ports |
| 1.3 | Version detection | Identified the exact software and version on each port; critical for finding known vulnerabilities |
| 1.4 | OS fingerprinting | Determined the operating system, which narrows down which exploits and tools apply |
| 1.5 | Comprehensive scan | Combined everything into a single command for efficiency |

## Self-Assessment

Answer the following questions without looking back at the walkthroughs. If you get stuck, that topic is worth revisiting.

**1.** What is the difference between an "open" port and a "filtered" port?

> &nbsp;
>
> &nbsp;

**2.** You run `nmap 10.100.5.10` and see 3 open ports. You then run `nmap -p- 10.100.5.10` and see 5 open ports. Why?

> &nbsp;
>
> &nbsp;

**3.** What does the `-sV` flag do, and why is it more useful than the SERVICE column in a basic scan?

> &nbsp;
>
> &nbsp;

**4.** Why does `-O` (OS detection) require `sudo` (root privileges)?

> &nbsp;
>
> &nbsp;

**5.** What does `nmap -A` do, and when would you choose it over running individual flags?

> &nbsp;
>
> &nbsp;

**6.** You found that a target is running "Microsoft IIS httpd 10.0" on port 80. What can you do with that version information?

> &nbsp;
>
> &nbsp;

## Command Cheat Sheet

Keep the following reference handy throughout the rest of the workbook. Every chapter starts with at least one of these commands.

| Command | What It Does |
|---------|-------------|
| `nmap <target>` | Scan the top 1,000 ports |
| `nmap -p- <target>` | Scan all 65,535 ports |
| `nmap -p 80,445,3389 <target>` | Scan specific ports only |
| `nmap -sV <target>` | Detect service versions on open ports |
| `sudo nmap -O <target>` | Detect the operating system |
| `nmap -sC <target>` | Run default NSE scripts against open ports |
| `nmap -A <target>` | Aggressive scan (version + OS + scripts + traceroute) |
| `nmap -T4 <target>` | Speed up the scan (good for labs, noisy on real networks) |
| `nmap -oN scan.txt <target>` | Save output to a text file |
| `nmap -oX scan.xml <target>` | Save output as XML (useful for importing into other tools) |

**Combining flags**: Nmap flags can be chained together. A common combination for labs:

```bash
nmap -sV -sC -O -T4 -p- <target>
```

Translates to: scan all ports, detect versions, run default scripts, fingerprint the OS, and do it fast.

## Connect the Dots: What Comes Next

You now know what services are running on the target and what software versions they use. The next step is to pick one of those services and dig deeper.

**Chapter 2 (SMB Reconnaissance)** focuses on port 445; the SMB file-sharing service you discovered in your scans. You will learn how to connect to SMB shares, list available files, and extract data without needing a password. The enumeration skills from Chapter 1 told you the door exists. Chapter 2 teaches you to open it.

---

## Self-Assessment Answer Key

**1.** An open port has a service actively listening and accepting connections. A filtered port has a firewall silently dropping packets; you cannot tell whether a service is behind it or not.

**2.** The default scan only checks the 1,000 most common ports. The full-range scan checks all 65,535. The 2 additional ports were on non-standard numbers outside the top 1,000.

**3.** `-sV` actively probes each open port to identify the running software and its version. The SERVICE column in a basic scan is just a guess based on the port number; it does not actually interrogate the service.

**4.** OS fingerprinting sends raw network packets that require low-level access to the network interface. Regular user accounts are not allowed to craft raw packets, so root privileges are needed.

**5.** `-A` enables OS detection, version detection, script scanning, and traceroute in a single pass. Use it when you want a thorough scan of a single target and do not mind the extra time. For large networks, running individual flags selectively is more efficient.

**6.** Search for known vulnerabilities specific to IIS 10.0, check whether the version is out of date (missing patches), and use that information to choose targeted exploitation techniques in later chapters.
