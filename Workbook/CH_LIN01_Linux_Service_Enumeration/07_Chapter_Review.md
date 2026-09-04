# Chapter L1: Review

## What You Learned

Across six labs, you built a complete Linux service enumeration methodology; from a single targeted port scan to version-based vulnerability identification. Each lab added a layer of depth to your approach. Effective enumeration is a process, not a single command.

You started by detecting SSH on port 22 with a targeted version scan. You expanded to multi-service discovery, learning that a single host can expose multiple attack surfaces. Direct service interaction proved that automated scanners miss details that manual connections reveal. Full port scans showed why security through obscurity fails. NSE scripts gave you deep configuration insight beyond version strings. Vulnerability research connected detected versions to known exploits, completing the path from "what is running" to "what can be exploited."

The TechStart Inc engagement demonstrated a realistic workflow. Real penetration tests follow the same progression: scan, enumerate, interact, research, report. The tools change as targets change, but the methodology stays consistent.

Along the way, you learned that default scans miss non-standard ports, that automated tools truncate service banners, and that a version string is all you need to search vulnerability databases. These are not abstract lessons; they are mistakes that real assessments make when the tester stops too early.

## The Progression You Followed

```mermaid
graph LR
    A[L1.1 Single Port]
    B[L1.2 Multi-Service]
    C[L1.3 Interaction]
    D[L1.4 Full Range]
    E[L1.5 NSE Scripts]
    F[L1.6 Vuln Research]
    A --> B --> C --> D --> E --> F
```

| Lab  | Skill Learned                  | Key Command                | Flag                      |
|------|--------------------------------|----------------------------|---------------------------|
| L1.1 | Targeted version scan          | `nmap -p 22 -sV`          | `OCR{<ssh_detected>}`     |
| L1.2 | Multi-port service discovery   | `nmap -sV`                | `OCR{<multi_service>}`    |
| L1.3 | Direct service interaction     | `ftp`, `nc`               | `OCR{<ftp_interact>}`     |
| L1.4 | Full range port scanning       | `nmap -p- -sV`            | `OCR{<non_standard>}`     |
| L1.5 | Script-based enumeration       | `nmap --script`           | `OCR{<nse_script>}`       |
| L1.6 | Version-to-vulnerability match | `searchsploit`            | `OCR{<vuln_research>}`    |

## Key Concepts Revisited

- **Port states**: Open means the service is accepting connections. Closed means the port responds but no service is listening. Filtered means a firewall is blocking the probe.
- **Version detection**: The `-sV` flag reads service banners to identify software names and version numbers.
- **Banner grabbing**: Connecting directly (via `ftp`, `nc`, or `curl`) reveals information that automated version detection discards.
- **Full range scanning**: The `-p-` flag checks all 65,535 TCP ports, defeating security-through-obscurity configurations.
- **NSE scripts**: Extend Nmap with targeted queries for authentication methods, host keys, and algorithm support.
- **Vulnerability research**: Matching a version string to a CVE using searchsploit completes the enumeration-to-exploitation pipeline.

## Self-Assessment

Answer each question from memory before checking the answer key at the bottom of the page.

**1. What Nmap flag performs version detection on discovered services?**

> &nbsp;

**2. How many ports does Nmap scan by default when no `-p` flag is specified?**

> &nbsp;

**3. What flag scans all 65,535 TCP ports?**

> &nbsp;

**4. Name two tools for connecting directly to an FTP service to read its banner.**

> &nbsp;

**5. What NSE script lists the authentication methods an SSH server accepts?**

> &nbsp;

**6. What is the CVE identifier for the vsftpd 2.3.4 backdoor?**

> &nbsp;

**7. Why does Nmap not capture the full multi-line FTP banner during a version scan?**

> &nbsp;

**8. What command-line tool searches a local copy of the Exploit Database?**

> &nbsp;

## Command Cheat Sheet

| Command                                        | Purpose                                  |
|------------------------------------------------|------------------------------------------|
| `nmap -p 22 -sV <ip>`                         | Version scan on a single port            |
| `nmap -sV <ip>`                               | Version scan on top 1,000 ports          |
| `nmap -p- -sV --open -T4 <ip>`               | Full range scan with version detection   |
| `nmap -p- --open -T4 <ip>`                    | Fast port discovery without versions     |
| `nmap --script ssh-hostkey <ip>`              | Retrieve SSH host key fingerprints       |
| `nmap --script ssh-auth-methods <ip>`         | List SSH authentication methods          |
| `nmap --script ssh2-enum-algos <ip>`          | Enumerate SSH encryption algorithms      |
| `nmap --script <s1>,<s2>,<s3> <ip>`           | Run multiple NSE scripts at once         |
| `ftp <ip>`                                     | Connect to FTP service                   |
| `nc <ip> <port>`                               | Raw TCP connection for banner grabbing   |
| `curl http://<ip>:<port>`                      | Fetch HTTP page content                  |
| `ssh -p <port> <user>@<ip>`                   | SSH to a non-standard port               |
| `searchsploit <software> <version>`           | Search for known exploits locally        |
| `searchsploit -w <software> <version>`        | Get ExploitDB URL for an exploit         |

## Connect the Dots: What Comes Next

You now know how to find services, identify their versions, and research vulnerabilities. The next chapter; **CH_LIN02: SSH Authentication**: shifts from enumeration to access. You will use the SSH service you have been scanning throughout this chapter and attempt to authenticate through various methods: password guessing, credential lists, and key-based authentication.

Enumeration tells you the door exists and what lock it uses. Authentication testing tries the keys.

The skills from this chapter carry forward directly. You will still run Nmap scans, read banners, and check versions; but now you will pair that reconnaissance with active authentication attempts. Every finding from Chapter L1 becomes input for Chapter L2.

Consider reviewing the commands in the cheat sheet above until you can recall each one without looking. Fluency with enumeration tools frees your attention for the harder decisions that come during exploitation.

---

## Self-Assessment Answer Key

**1.** The `-sV` flag enables version detection.

**2.** Nmap scans the top 1,000 most common ports by default.

**3.** The `-p-` flag (shorthand for `-p 1-65535`) scans all TCP ports.

**4.** The `ftp` client and `nc` (netcat) both connect directly to FTP and display the banner.

**5.** The `ssh-auth-methods` NSE script lists accepted authentication types.

**6.** CVE-2011-2523 is the identifier for the vsftpd 2.3.4 backdoor vulnerability.

**7.** Nmap reads only enough of the banner to match a service signature, then disconnects. Multi-line custom messages and administrative notes are discarded during version matching.

**8.** searchsploit searches a local copy of the Exploit Database (ExploitDB) from the command line.
