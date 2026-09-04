# Exercise 1.4: Failed Login Analysis

## Before You Begin

Exercise 1.4 is the final lab in Chapter N1. In Exercise 1.1 you analyzed firewall logs to detect a port scan, in Exercise 1.2 you examined HTTP traffic in a packet capture using Wireshark, and in Exercise 1.3 you investigated DNS query logs for signs of data exfiltration. Exercise 1.4 focuses on SSH authentication logs; the standard format used by every Linux system to record login attempts. The command-line skills you have practiced throughout this chapter (`grep`, `awk`, `sort`, `uniq`) apply directly here.

## Scenario

MediCare's CISO received automated alerts about an excessive number of failed SSH login attempts on a critical server. A small number of failed logins is normal; users occasionally mistype passwords or forget credentials after a vacation. However, the volume flagged by the alerting system suggests something far more deliberate. Your task is to analyze the authentication logs, determine whether this activity constitutes a brute-force attack, and document the evidence.

## Your Objectives

- Download SSH authentication logs from the target machine.
- Count failed login attempts and identify the source IP addresses responsible.
- Determine whether the traffic pattern matches a brute-force attack.
- Check whether any unauthorized login succeeded.
- Find and submit the flag.

## Background: SSH Brute-Force Attacks

SSH (Secure Shell) is the standard protocol for encrypted remote access to Linux and Unix servers. System administrators use SSH to manage servers from the command line, transfer files, and run maintenance scripts. Because SSH provides full shell access to a system, it is a high-value target for attackers.

A brute-force attack against SSH works by trying many username and password combinations in rapid succession. Pure brute force attempts every possible combination, but this is slow and impractical. A more common variant is a **dictionary attack**, which uses pre-compiled lists of common usernames (admin, root, test, guest, backup, oracle, postgres) and commonly leaked passwords. Dictionary attacks are far faster because they target the credentials that real users and administrators actually choose.

SSH servers log every authentication attempt; both successes and failures; in the system's auth log. Each log entry records the result, the username tried, the source IP address, and the timestamp. The key fields to look for are:

- **`Accepted password`**: the login succeeded with the correct credentials.
- **`Failed password`**: the login failed due to wrong credentials.
- **`invalid user`**: the username does not exist on the system at all.

A normal user's log signature is zero to two failures from an internal IP address, followed by a successful login within a few minutes. An attacker's log signature is dozens or hundreds of failures from an external IP address, across many different usernames, with no successful login at all.

## Walkthrough

### Step 1: Launch the Exercise

Start the lab environment and note the target IP address displayed on the launch page. You will use this IP to download the authentication log file. The target machine is hosting the auth log from MediCare's SSH server on a web server so you can retrieve it for analysis.

### Step 2: Download the Auth Log

!!! kali "Download the auth log from the target"
    Open a terminal on your analyst Kali workstation and download the SSH authentication log from the target machine.

    ```bash
    curl http://<target_ip>/auth.log -o auth.log
    ```

    The `curl -o` flag saves the log file to your current directory.

!!! kali "Preview the auth log structure"
    View the first several lines to understand its structure.

    ```bash
    head -20 auth.log
    ```

Each line follows the standard sshd log format:

```
Jan 15 08:15:23 medicare-ssh sshd[12345]: Accepted password for jthompson from 10.50.1.15 port 54321 ssh2
Jan 15 11:23:45 medicare-ssh sshd[23456]: Failed password for admin from 185.220.101.77 port 49152 ssh2
Jan 15 11:23:52 medicare-ssh sshd[23457]: Failed password for invalid user root from 185.220.101.77 port 49153 ssh2
```

The important fields in each line are:

| Field | Example | Description |
|---|---|---|
| Timestamp | `Jan 15 11:23:45` | Date and time of the attempt. |
| Hostname | `medicare-ssh` | The server that recorded the event. |
| Result | `Failed password` | Whether the login succeeded or failed. |
| Username | `admin` | The account name the user or attacker tried. |
| Source IP | `185.220.101.77` | The IP address the attempt came from. |

Note that lines containing `invalid user` indicate the username does not exist on the system at all.

### Step 3: Count Total Failed Attempts

!!! kali "Count total failed login attempts"
    Search the log for every failed login attempt and count the total.

    ```bash
    grep "Failed password" auth.log | wc -l
    ```

    The total count tells you the overall scale of the problem. A handful of failures across an entire day is normal; users forget passwords, mistype them, or try old credentials after a password change. Dozens or more concentrated in a short time window is a strong indicator of automated activity.

### Step 4: Count Failures per Source IP

!!! kali "Count failures per source IP"
    Now determine which IP addresses are responsible for the failures. The total count is useful, but you need to know whether the failures come from one source or many. The pipeline below extracts the source IP from each failed attempt, counts the occurrences, and sorts by frequency in descending order.

    ```bash
    grep "Failed password" auth.log | grep -oE "from [0-9]+\.[0-9]+\.[0-9]+\.[0-9]+" | awk '{print $2}' | sort | uniq -c | sort -rn
    ```

    The output shows a dramatic imbalance. One external IP address has roughly 60 failures, while internal IP addresses have only one or two each; consistent with normal typos by legitimate users.

---

**Record Your Findings**

Fill in the table with the top results from your output:

| Source IP | Failed Attempts |
|---|---|
| | |
| | |
| | |
| | |

Which IP address accounts for the overwhelming majority of failures? _______________

Is this IP address internal (10.x.x.x, 172.16-31.x.x, 192.168.x.x) or external? _______________

---

### Step 5: Analyze the Attacker's Attempts

!!! kali "Filter failed attempts from the suspicious IP"
    Filter the log for only the failed attempts from the suspicious IP address.

    ```bash
    grep "185.220.101.77" auth.log | grep "Failed password"
    ```

Examine the output and look for three characteristics of a brute-force attack:

**Timing.** Compare the timestamps of consecutive attempts. The attacker sends a new attempt every 8 to 15 seconds. A legitimate user would pause, think, and retry after 30 seconds to a minute.

**Username variety.** Scan the usernames being tried. You will see admin, root, user, test, guest, backup, oracle, postgres, and dozens of other common account names. The attacker is cycling through a dictionary list rather than targeting a single known account.

**Volume.** Count how many unique usernames the attacker tried.

!!! kali "Count unique usernames attempted"
    The pipeline below pulls the username from each failed line, deduplicates, and counts the distinct values.

    ```bash
    grep "185.220.101.77" auth.log | grep "Failed password" | grep -oP "for (invalid user )?\K\S+" | sort -u | wc -l
    ```

    The attacker tried approximately 57 unique usernames across a window of roughly 10 to 15 minutes.

### Step 6: Verify No Successful Login

!!! kali "Check for any successful login from the attacker"
    The most critical question in any brute-force investigation is whether the attacker succeeded. Search for any accepted login from the attacker's IP address.

    ```bash
    grep "185.220.101.77" auth.log | grep "Accepted"
    ```

    The `grep Accepted` command should return no output, confirming that none of the attacker's attempts succeeded. In this case the brute-force attack failed entirely.

If this command had returned a result, it would mean the attacker guessed a valid credential and gained shell access to the server. That scenario requires immediate containment: disabling the compromised account, isolating the server from the network, and beginning a full incident response investigation.

---

**Record Your Findings**

Approximate duration of the attack (first to last attempt): _______________

Number of unique usernames tried: _______________

Did the attacker successfully log in? _______________

What type of attack does this evidence describe? _______________

---

### Step 7: Find the Flag

!!! kali "Search the log for the flag"
    Search the log file for the flag.

    ```bash
    grep "OCR{" auth.log
    ```

    Record the flag you find in `OCR{<flag_here>}` format.

## Analysis Questions

**1. The attacker tried 57 different usernames. What type of brute-force attack is this?**

??? note "Reveal Answer"

    This is a dictionary attack; the attacker uses a pre-compiled list of common usernames rather than trying every possible combination. Dictionary attacks are faster than pure brute force and often include admin, root, test, guest, backup, and service account names found on typical systems.

**2. None of the attacker's attempts succeeded. Does that mean the server is secure?**

??? note "Reveal Answer"

    The server defended against this specific attack, but it is not necessarily secure. The attack revealed that SSH is exposed directly to the internet, which it should not be. A more sophisticated attacker with a better wordlist or credential stuffing data from breached databases might succeed on a future attempt. The correct response is to block the attacker's IP immediately, deploy fail2ban to automatically block IPs after a threshold of failures, and restrict SSH access so that it is reachable only through a VPN.

**3. How would you distinguish a brute-force attack from a legitimate user who forgot their password?**

??? note "Reveal Answer"

    A legitimate user typically has one to three failures from an internal IP address, followed by a successful login, with attempts spread across several minutes. A brute-force attack produces dozens or hundreds of failures from an external IP address with no successes, occurring every few seconds, and cycling through many different usernames. The volume, speed, source location, and variety of usernames are the distinguishing factors.

## Key Takeaways

- SSH authentication logs record every login attempt with the result, username, source IP, and timestamp.
- Brute-force attacks produce a distinctive pattern: dozens of failures, many different usernames, rapid succession, an external source IP, and no successful logins.
- The same `grep`, `awk`, `sort`, and `uniq` pipeline you have used throughout this chapter applies to any text-based log format.
- Checking for both `Failed password` and `Accepted password` entries from a suspicious IP is critical; a successful login means the attacker gained access to the system.
- Real-world defenses against SSH brute force include fail2ban (automatic IP blocking after repeated failures), SSH key-based authentication (which eliminates password guessing entirely), and restricting SSH access to VPN-connected users only.
